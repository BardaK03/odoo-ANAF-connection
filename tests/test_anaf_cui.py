# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests import TransactionCase, tagged

from ..models.anaf_cui import is_valid_cui, normalize_vat


@tagged("post_install", "-at_install")
class TestAnafCui(TransactionCase):
    def test_normalize_accepts_ro_prefix(self):
        self.assertEqual(normalize_vat("RO14399840"), (True, "14399840"))

    def test_normalize_accepts_bare_digits(self):
        self.assertEqual(normalize_vat("14399840"), (False, "14399840"))

    def test_normalize_strips_separators_and_case(self):
        self.assertEqual(normalize_vat(" ro 14.399-840 "), (True, "14399840"))

    def test_normalize_drops_leading_zeros(self):
        self.assertEqual(normalize_vat("RO0014399840"), (True, "14399840"))

    def test_normalize_rejects_foreign_and_empty(self):
        for value in ("DE811907980", "ABC", "", False, None):
            self.assertEqual(normalize_vat(value), (False, False), value)

    def test_check_digit_accepts_real_fiscal_codes(self):
        for cui in ("14399840", "14056826", "1973096", "13548146"):
            self.assertTrue(is_valid_cui(cui), cui)

    def test_check_digit_rejects_typos(self):
        self.assertFalse(is_valid_cui("14399841"))
        self.assertFalse(is_valid_cui("8"))
        self.assertFalse(is_valid_cui("abc"))
