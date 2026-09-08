# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests import TransactionCase, tagged

from .anaf_bilant_data import ANAF_BILANT_DATA

EMAG = ("14399840", 2025)
ROMGAZ = ("14056826", 2025)
ANTIBIOTICE = ("1973096", 2025)


@tagged("post_install", "-at_install")
class TestAnafBilantClient(TransactionCase):
    def setUp(self):
        super().setUp()
        self.client = self.env["anaf.bilant.client"].with_context(
            anaf_bilant_data=ANAF_BILANT_DATA
        )

    def test_parse_loss_making_company(self):
        data = self.client.parse(ANAF_BILANT_DATA[EMAG])
        self.assertEqual(data["company_name"], "DANTE INTERNATIONALSA")
        self.assertEqual(data["year"], 2025)
        self.assertEqual(data["turnover"], 8706154345.0)
        self.assertEqual(data["employees"], 2889)
        self.assertEqual(data["gross_result"], -290554064.0)
        self.assertEqual(data["margin"], -3.34)

    def test_parse_profitable_companies(self):
        romgaz = self.client.parse(ANAF_BILANT_DATA[ROMGAZ])
        self.assertEqual(romgaz["employees"], 5227)
        self.assertEqual(romgaz["margin"], 47.52)
        antibiotice = self.client.parse(ANAF_BILANT_DATA[ANTIBIOTICE])
        self.assertEqual(antibiotice["employees"], 1370)
        self.assertEqual(antibiotice["margin"], 9.32)

    def test_parse_is_independent_of_indicator_order(self):
        payload = dict(ANAF_BILANT_DATA[EMAG])
        payload["i"] = list(reversed(payload["i"]))
        self.assertEqual(
            self.client.parse(payload), self.client.parse(ANAF_BILANT_DATA[EMAG])
        )

    def test_parse_empty_payload_yields_nothing(self):
        self.assertEqual(self.client.parse({}), {})
        self.assertEqual(self.client.parse({"an": 2026, "i": []}), {})

    def test_parse_zero_turnover_leaves_margin_undefined(self):
        payload = {
            "an": 2025,
            "cui": 1,
            "deni": "Zero Co",
            "i": [
                {"indicator": "I13", "val_indicator": 0},
                {"indicator": "I16", "val_indicator": 1000},
                {"indicator": "I20", "val_indicator": 3},
            ],
        }
        data = self.client.parse(payload)
        self.assertIsNone(data["margin"])
        self.assertEqual(data["employees"], 3)

    def test_fetch_unknown_cui_is_not_an_error(self):
        error, payload = self.client.fetch("13548146", 2025)
        self.assertFalse(error)
        self.assertEqual(payload, {})
