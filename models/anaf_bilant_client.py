# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""HTTP client for the public ANAF ``/bilant`` web service.

Implemented as an ``AbstractModel`` so that it stays overridable by other
modules and mockable from tests through the ``anaf_bilant_data`` context key,
mirroring ``l10n_ro_partner_create_by_vat``'s ``anaf_data`` hook.
"""

import logging

import requests

from odoo import api, models

_logger = logging.getLogger(__name__)

DEFAULT_URL = "https://webservicesp.anaf.ro/bilant"
DEFAULT_TIMEOUT = 10.0

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Odoo-AnafPartnerBilant/1.0",
}

# ANAF returns a normalized set of 20 indicators (I1..I20) regardless of the
# balance sheet form used by the company. Only the ones we consume are named.
INDICATOR_TURNOVER = "I13"
INDICATOR_GROSS_PROFIT = "I16"
INDICATOR_GROSS_LOSS = "I17"
INDICATOR_NET_PROFIT = "I18"
INDICATOR_NET_LOSS = "I19"
INDICATOR_EMPLOYEES = "I20"


class AnafBilantClient(models.AbstractModel):
    _name = "anaf.bilant.client"
    _description = "ANAF Bilant Web Service Client"

    @api.model
    def _get_config(self, key, default):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "anaf_partner_bilant.%s" % key
        )
        return value or default

    @api.model
    def fetch(self, cui, year):
        """Query ANAF for one ``(cui, year)`` pair.

        Never raises: returns ``(error_message, raw_payload)`` so callers can
        decide what to do without wrapping every call in a try/except. An empty
        error with an empty payload means "ANAF answered, but has no data".
        """
        mocked = self.env.context.get("anaf_bilant_data")
        if mocked is not None:
            return "", mocked.get((str(cui), int(year)), {})

        url = self._get_config("url", DEFAULT_URL)
        timeout = float(self._get_config("timeout", DEFAULT_TIMEOUT))
        params = {"an": int(year), "cui": int(cui)}
        try:
            response = requests.get(
                url, params=params, headers=HEADERS, timeout=timeout
            )
        except requests.exceptions.RequestException as err:
            return (
                self.env._(
                    "ANAF web service unreachable: %(error)s", error=err
                ),
                {},
            )

        if response.status_code != 200:
            return (
                self.env._(
                    "ANAF request failed (HTTP %(code)s): %(reason)s",
                    code=response.status_code,
                    reason=response.reason,
                ),
                {},
            )
        try:
            payload = response.json()
        except ValueError:
            return self.env._("ANAF returned a non-JSON response."), {}

        # ANAF answers HTTP 200 with an empty indicator list both for unknown
        # fiscal codes and for years whose balance sheet is not filed yet, so
        # the payload shape - not the status code - is the real signal.
        if not isinstance(payload, dict) or not payload.get("i"):
            _logger.debug("ANAF has no bilant for CUI %s year %s", cui, year)
            return "", {}
        return "", payload

    @api.model
    def parse(self, payload):
        """Turn a raw ANAF payload into normalized business values.

        Returns ``{}`` when the payload carries no usable indicators.
        """
        if not payload or not payload.get("i"):
            return {}

        # The order of the "i" list is NOT stable across responses, so always
        # index by indicator code instead of relying on positions.
        indicators = {
            item.get("indicator"): item.get("val_indicator") or 0
            for item in payload.get("i", [])
        }

        turnover = indicators.get(INDICATOR_TURNOVER) or 0
        gross_profit = indicators.get(INDICATOR_GROSS_PROFIT) or 0
        gross_loss = indicators.get(INDICATOR_GROSS_LOSS) or 0
        gross_result = gross_profit - gross_loss

        # I16 and I17 are mutually exclusive: ANAF fills exactly one of them.
        margin = None
        if turnover:
            margin = round(gross_result / turnover * 100.0, 2)

        return {
            "cui": str(payload.get("cui") or ""),
            "year": int(payload.get("an") or 0),
            "company_name": (payload.get("deni") or "").strip(),
            "caen": str(payload.get("caen") or ""),
            "caen_name": (payload.get("den_caen") or "").strip(),
            "turnover": float(turnover),
            "employees": int(indicators.get(INDICATOR_EMPLOYEES) or 0),
            "gross_result": float(gross_result),
            "net_result": float(
                (indicators.get(INDICATOR_NET_PROFIT) or 0)
                - (indicators.get(INDICATOR_NET_LOSS) or 0)
            ),
            "margin": margin,
        }
