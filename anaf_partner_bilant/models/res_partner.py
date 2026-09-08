# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Wire ANAF balance sheet data into the existing Studio partner fields.

Three complementary triggers cover every channel a VAT number can arrive
through:

* ``_onchange_vat_anaf_bilant`` - interactive form edit, on create AND on
  update, giving the user the values before saving.
* ``create``/``write`` hooks - imports, XML-RPC and mass edits, where onchange
  never runs. They apply a cache hit immediately, otherwise queue the record.
* ``_cron_anaf_bilant_sync`` - drains the queue, throttled, and retries what
  failed while ANAF was unreachable.
"""

import logging
import time

from odoo import api, fields, models

from .anaf_cui import is_valid_cui, normalize_vat

_logger = logging.getLogger(__name__)

# Existing Studio fields this module populates, mapped to parsed ANAF keys.
STUDIO_FIELD_MAP = {
    "x_studio_ca_2024": "turnover",
    "x_studio_nr_angajati_2024": "employees",
    "x_studio_profitabilitate_gross_profit": "margin",
}

DEFAULT_CRON_BATCH = 50
DEFAULT_REFRESH_BATCH = 500
DEFAULT_THROTTLE = 1.0
DEFAULT_RETRY_HOURS = 6
DEFAULT_STALE_DAYS = 30
MAX_YEAR_FALLBACK = 2


class ResPartner(models.Model):
    _inherit = "res.partner"

    anaf_bilant_cui = fields.Char(
        string="ANAF Synced CUI",
        readonly=True,
        copy=False,
        help="Fiscal code the stored figures were fetched for.",
    )
    anaf_bilant_year = fields.Integer(
        string="ANAF Fiscal Year",
        readonly=True,
        copy=False,
        help="Fiscal year the financial figures actually come from.",
    )
    anaf_bilant_sync_date = fields.Datetime(
        string="ANAF Last Sync",
        readonly=True,
        copy=False,
        help="When ANAF data was last applied successfully.",
    )
    anaf_bilant_attempt_date = fields.Datetime(
        string="ANAF Last Attempt",
        readonly=True,
        copy=False,
        index=True,
        help="When ANAF was last queried, successfully or not. Used to back "
        "off instead of retrying a broken fiscal code every few minutes.",
    )
    anaf_bilant_state = fields.Selection(
        [
            ("none", "Not synced"),
            ("to_sync", "Queued"),
            ("done", "Synced"),
            ("no_data", "No ANAF data"),
            ("error", "Error"),
        ],
        string="ANAF Status",
        default="none",
        readonly=True,
        copy=False,
        index=True,
    )
    anaf_bilant_message = fields.Char(
        string="ANAF Message", readonly=True, copy=False
    )
    anaf_bilant_ids = fields.One2many(
        "anaf.bilant", "partner_id", string="ANAF History", readonly=True
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _anaf_cui(self):
        """Canonical Romanian fiscal code for this partner, or ``False``."""
        self.ensure_one()
        has_ro_prefix, cui = normalize_vat(self.vat)
        if not cui:
            return False
        # A bare numeric VAT is only Romanian if the country says so (or is
        # not set yet); an explicit RO prefix always wins.
        if not has_ro_prefix and self.country_id and self.country_id.code != "RO":
            return False
        if not is_valid_cui(cui):
            return False
        return cui

    def _anaf_is_eligible(self):
        """Only company records without a parent are worth querying."""
        self.ensure_one()
        return bool(self.is_company and not self.parent_id)

    @api.model
    def _anaf_get_config(self, key, default):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("anaf_partner_bilant.%s" % key)
        )
        return value if value not in (None, False, "") else default

    @api.model
    def _anaf_target_years(self):
        """Candidate fiscal years, newest first.

        The balance sheet for year N is filed during N+1, so the newest
        possible year is last year; we fall back one more year for companies
        that file late or when queried early in the calendar year.
        """
        forced = self._anaf_get_config("year", False)
        if forced:
            try:
                return [int(forced)]
            except (TypeError, ValueError):
                _logger.warning(
                    "Ignoring invalid anaf_partner_bilant.year=%r", forced
                )
        current = fields.Date.context_today(self).year
        return [current - offset for offset in range(1, MAX_YEAR_FALLBACK + 1)]

    def _anaf_studio_values(self, data):
        """Cast parsed ANAF values to whatever type each Studio field has.

        The Studio fields are deliberately not redeclared by this module, so
        their type stays whatever the user configured. Casting at runtime keeps
        the module correct for ``char`` fields today and for ``float`` or
        ``integer`` fields after a Studio conversion, with no code change.
        """
        self.ensure_one()
        values = {}
        for field_name, data_key in STUDIO_FIELD_MAP.items():
            field = self._fields.get(field_name)
            if field is None:
                _logger.warning(
                    "Field %s is missing on res.partner; skipping it. "
                    "Recreate it in Studio or adjust STUDIO_FIELD_MAP.",
                    field_name,
                )
                continue
            value = data.get(data_key)
            # None means ANAF gave us nothing usable (a zero turnover makes
            # the margin undefined). Leave the previous value alone rather
            # than overwriting good data with a misleading zero.
            if value is None:
                continue
            values[field_name] = self._anaf_cast(field, data_key, value)
        return values

    @api.model
    def _anaf_cast(self, field, data_key, value):
        if field.type in ("char", "text"):
            if data_key == "margin":
                return "%.2f" % value
            return "%d" % round(value)
        if field.type == "integer":
            return int(round(value))
        if field.type in ("float", "monetary"):
            return float(value)
        _logger.warning(
            "Unsupported type %r on field %s; writing its text form.",
            field.type,
            field.name,
        )
        return str(value)

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------
    def _anaf_fetch(self, cui, force=False):
        """Resolve ANAF data for ``cui``, newest available year first.

        Returns ``(error, data, payload)``. ``data`` is empty when ANAF has no
        balance sheet for any candidate year. ``payload`` is None on a cache
        hit, since there is nothing new to store.
        """
        client = self.env["anaf.bilant.client"]
        cache = self.env["anaf.bilant"]
        last_error = ""
        for year in self._anaf_target_years():
            if not force:
                cached = cache._find_fresh(cui, year)
                if cached:
                    return "", cached._to_data(), None
            error, payload = client.fetch(cui, year)
            if error:
                last_error = error
                continue
            data = client.parse(payload)
            if data:
                return "", data, payload
        return last_error, {}, None

    def _anaf_fetch_cached_only(self, cui):
        """Cache-only lookup, so saving a record never blocks on HTTP."""
        self.ensure_one()
        if self._anaf_get_config("sync_mode", "cron") == "immediate":
            return self._anaf_fetch(cui)
        cache = self.env["anaf.bilant"]
        for year in self._anaf_target_years():
            cached = cache._find_fresh(cui, year)
            if cached:
                return "", cached._to_data(), None
        return "", {}, None

    # ------------------------------------------------------------------
    # Applying
    # ------------------------------------------------------------------
    def _anaf_sync(self, force=False):
        """Fetch and apply ANAF data for each eligible partner in ``self``."""
        for partner in self:
            if not partner._anaf_is_eligible():
                continue
            cui = partner._anaf_cui()
            if not cui:
                partner._anaf_set_status(
                    "none",
                    self.env._("No valid Romanian fiscal code."),
                    attempted=False,
                )
                continue
            error, data, payload = partner._anaf_fetch(cui, force=force)
            if error:
                _logger.info(
                    "ANAF sync failed for %s: %s", partner.display_name, error
                )
                partner._anaf_set_status("error", error)
                continue
            if not data:
                partner._anaf_set_status(
                    "no_data",
                    self.env._(
                        "ANAF has no balance sheet for CUI %(cui)s.", cui=cui
                    ),
                )
                continue
            partner._anaf_apply(cui, data, payload)
        return True

    def _anaf_apply(self, cui, data, payload=None):
        self.ensure_one()
        values = self._anaf_studio_values(data)
        values.update(self._anaf_status_values(cui, data))
        self.with_context(skip_anaf_bilant=True).write(values)
        self.env["anaf.bilant"]._store(data, payload=payload, partner=self)
        return values

    @api.model
    def _anaf_status_values(self, cui, data):
        return {
            "anaf_bilant_cui": cui,
            "anaf_bilant_year": data.get("year") or 0,
            "anaf_bilant_sync_date": fields.Datetime.now(),
            "anaf_bilant_attempt_date": fields.Datetime.now(),
            "anaf_bilant_state": "done",
            "anaf_bilant_message": False,
        }

    def _anaf_set_status(self, state, message=False, attempted=True):
        self.ensure_one()
        values = {"anaf_bilant_state": state, "anaf_bilant_message": message}
        if attempted:
            values["anaf_bilant_attempt_date"] = fields.Datetime.now()
        self.with_context(skip_anaf_bilant=True).write(values)

    def _anaf_mark_to_sync(self):
        """Queue records for the cron, applying a cache hit straight away."""
        for partner in self:
            if not partner._anaf_is_eligible():
                continue
            cui = partner._anaf_cui()
            if not cui:
                continue
            # Already up to date for this exact fiscal code - typically a save
            # right after the onchange already filled the figures in.
            if partner.anaf_bilant_state == "done" and (
                partner.anaf_bilant_cui == cui
            ):
                continue
            unused_error, data, payload = partner._anaf_fetch_cached_only(cui)
            if data:
                partner._anaf_apply(cui, data, payload)
            else:
                partner._anaf_set_status("to_sync", attempted=False)
        return True

    # ------------------------------------------------------------------
    # Triggers
    # ------------------------------------------------------------------
    @api.onchange("vat", "country_id")
    def _onchange_vat_anaf_bilant(self):
        """Fill the figures live in the form, on create and on VAT update."""
        if self.env.context.get("skip_anaf_bilant"):
            return None
        if not self._anaf_is_eligible():
            return None
        cui = self._anaf_cui()
        if not cui:
            return None
        error, data, payload = self._anaf_fetch(cui)
        if error:
            return {"warning": {"title": self.env._("ANAF"), "message": error}}
        if not data:
            return {
                "warning": {
                    "title": self.env._("ANAF"),
                    "message": self.env._(
                        "ANAF has no balance sheet for CUI %(cui)s. The "
                        "financial fields were left unchanged.",
                        cui=cui,
                    ),
                }
            }
        values = self._anaf_studio_values(data)
        values.update(self._anaf_status_values(cui, data))
        self.with_context(skip_anaf_bilant=True).update(values)
        # Seed the cache from the id-less form record too, so the following
        # save does not trigger a second identical request.
        if payload:
            self.env["anaf.bilant"]._store(data, payload=payload)
        return None

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        if not self.env.context.get("skip_anaf_bilant"):
            partners.filtered(lambda p: p.vat)._anaf_mark_to_sync()
        return partners

    def write(self, vals):
        track_vat = "vat" in vals or "country_id" in vals
        previous = (
            {partner.id: partner._anaf_cui() for partner in self}
            if track_vat
            else {}
        )
        result = super().write(vals)
        if previous and not self.env.context.get("skip_anaf_bilant"):
            # Compare canonical fiscal codes, not raw strings: retyping
            # "14399840" as "RO14399840" is not a real change and must not
            # cause a refetch.
            changed = self.filtered(
                lambda p: p._anaf_cui() and p._anaf_cui() != previous.get(p.id)
            )
            changed._anaf_mark_to_sync()
        return result

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_anaf_bilant_fetch(self):
        """Manual refresh from the partner form, bypassing the cache."""
        self._anaf_sync(force=True)
        return True

    @api.model
    def _cron_anaf_bilant_sync(self):
        """Drain the queue and retry failures that have backed off long enough."""
        batch = int(self._anaf_get_config("cron_batch", DEFAULT_CRON_BATCH))
        throttle = float(self._anaf_get_config("throttle", DEFAULT_THROTTLE))
        retry_hours = int(self._anaf_get_config("retry_hours", DEFAULT_RETRY_HOURS))
        retry_cutoff = fields.Datetime.subtract(
            fields.Datetime.now(), hours=retry_hours
        )
        partners = self.search(
            [
                "|",
                ("anaf_bilant_state", "=", "to_sync"),
                "&",
                ("anaf_bilant_state", "=", "error"),
                "|",
                ("anaf_bilant_attempt_date", "=", False),
                ("anaf_bilant_attempt_date", "<", retry_cutoff),
            ],
            limit=batch,
        )
        _logger.info("ANAF bilant cron: %s partner(s) to sync", len(partners))
        in_test = self.env.registry.in_test_mode()
        for index, partner in enumerate(partners):
            partner._anaf_sync()
            # Commit per record so one unreachable call cannot discard the
            # whole batch, and stay under the ANAF request rate.
            if not in_test:
                self.env.cr.commit()
                if throttle and index < len(partners) - 1:
                    time.sleep(throttle)
        return True

    @api.model
    def _cron_anaf_bilant_refresh(self):
        """Requeue partners whose figures predate the newest published year.

        ANAF publishes a new balance sheet once a year, so synced records go
        stale silently. Records ANAF knows nothing about carry year 0 and are
        retried only after the staleness window, to avoid a daily hammer.
        """
        batch = int(self._anaf_get_config("refresh_batch", DEFAULT_REFRESH_BATCH))
        stale_days = int(self._anaf_get_config("stale_days", DEFAULT_STALE_DAYS))
        stale_cutoff = fields.Datetime.subtract(
            fields.Datetime.now(), days=stale_days
        )
        newest_year = max(self._anaf_target_years())
        partners = self.search(
            [
                ("vat", "!=", False),
                ("anaf_bilant_state", "in", ("done", "no_data")),
                ("anaf_bilant_year", "<", newest_year),
                "|",
                ("anaf_bilant_attempt_date", "=", False),
                ("anaf_bilant_attempt_date", "<", stale_cutoff),
            ],
            limit=batch,
        )
        if partners:
            _logger.info(
                "ANAF bilant refresh: requeueing %s partner(s) older than %s",
                len(partners),
                newest_year,
            )
            partners.with_context(skip_anaf_bilant=True).write(
                {"anaf_bilant_state": "to_sync"}
            )
        return True
