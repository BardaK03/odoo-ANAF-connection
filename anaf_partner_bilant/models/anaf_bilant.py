# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Per-(CUI, year) cache and multi-year history of ANAF balance sheet data."""

import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

DEFAULT_CACHE_DAYS = 30


class AnafBilant(models.Model):
    _name = "anaf.bilant"
    _description = "ANAF Balance Sheet Data"
    _order = "year desc, cui"

    partner_id = fields.Many2one(
        "res.partner", string="Partner", ondelete="set null", index=True
    )
    cui = fields.Char(required=True, index=True, help="Fiscal code, digits only.")
    year = fields.Integer(required=True, index=True)
    company_name = fields.Char()
    caen = fields.Char(string="CAEN")
    caen_name = fields.Char(string="CAEN Description")
    turnover = fields.Float(string="Net Turnover (I13)", digits=(16, 2))
    employees = fields.Integer(string="Average Employees (I20)")
    gross_result = fields.Float(string="Gross Result (I16-I17)", digits=(16, 2))
    net_result = fields.Float(string="Net Result (I18-I19)", digits=(16, 2))
    margin = fields.Float(string="Gross Margin %", digits=(16, 2))
    payload = fields.Text(
        help="Raw ANAF JSON response, kept so values can be re-derived "
        "without hitting the web service again."
    )
    fetch_date = fields.Datetime(required=True, default=fields.Datetime.now)

    _cui_year_uniq = models.Constraint(
        "unique (cui, year)",
        "ANAF balance sheet data is already stored for this fiscal code "
        "and year.",
    )

    @api.depends("company_name", "cui", "year")
    def _compute_display_name(self):
        for record in self:
            record.display_name = "%s (%s) - %s" % (
                record.company_name or record.cui,
                record.cui,
                record.year,
            )

    def _to_data(self):
        """Shape a cached record like ``anaf.bilant.client.parse`` output."""
        self.ensure_one()
        return {
            "cui": self.cui,
            "year": self.year,
            "company_name": self.company_name or "",
            "caen": self.caen or "",
            "caen_name": self.caen_name or "",
            "turnover": self.turnover,
            "employees": self.employees,
            "gross_result": self.gross_result,
            "net_result": self.net_result,
            "margin": self.margin if self.turnover else None,
        }

    @api.model
    def _cache_max_age_days(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "anaf_partner_bilant.cache_days", DEFAULT_CACHE_DAYS
        )
        try:
            return int(value)
        except (TypeError, ValueError):
            return DEFAULT_CACHE_DAYS

    @api.model
    def _find_fresh(self, cui, year):
        """Return a non-stale cached record for ``(cui, year)``, or an empty set."""
        max_age = self._cache_max_age_days()
        if max_age <= 0:
            return self.browse()
        limit_date = fields.Datetime.subtract(fields.Datetime.now(), days=max_age)
        return self.sudo().search(
            [
                ("cui", "=", str(cui)),
                ("year", "=", int(year)),
                ("fetch_date", ">=", limit_date),
            ],
            limit=1,
        )

    @api.model
    def _store(self, data, payload=None, partner=None):
        """Upsert cached ANAF data. Cache failures must never break a sync."""
        values = {
            key: data[key]
            for key in (
                "company_name",
                "caen",
                "caen_name",
                "turnover",
                "employees",
                "gross_result",
                "net_result",
            )
            if key in data
        }
        values.update(
            margin=data.get("margin") or 0.0,
            payload=json.dumps(payload) if payload else False,
            fetch_date=fields.Datetime.now(),
        )
        if partner:
            values["partner_id"] = partner.id
        try:
            existing = self.sudo().search(
                [("cui", "=", data["cui"]), ("year", "=", data["year"])], limit=1
            )
            if existing:
                existing.write(values)
                return existing
            values.update(cui=data["cui"], year=data["year"])
            return self.sudo().create(values)
        except Exception:  # pragma: no cover - cache must stay best-effort
            _logger.exception(
                "Could not cache ANAF bilant for CUI %s year %s",
                data.get("cui"),
                data.get("year"),
            )
            return self.browse()
