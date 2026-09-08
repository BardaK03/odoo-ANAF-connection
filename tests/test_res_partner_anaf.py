# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Integration tests for the three ANAF sync triggers on res.partner."""

from odoo.tests import Form, TransactionCase, tagged

from .anaf_bilant_data import ANAF_BILANT_DATA

EMAG_VAT = "RO14399840"
EMAG_CUI = "14399840"
ROMGAZ_VAT = "RO14056826"
# Valid check digit, but ANAF has no balance sheet for it in the fixtures.
NO_DATA_VAT = "RO13548146"


@tagged("post_install", "-at_install")
class TestResPartnerAnaf(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Pin the fiscal year so the suite does not drift as the calendar
        # moves past the captured fixtures.
        cls.env["ir.config_parameter"].sudo().set_param(
            "anaf_partner_bilant.year", "2025"
        )
        cls.germany = cls.env.ref("base.de")

    def _partner_env(self):
        return self.env["res.partner"].with_context(
            anaf_bilant_data=ANAF_BILANT_DATA
        )

    def _drain_queue(self):
        """Run the sync cron the way a real scheduler would.

        ``create``/``write`` deliberately never call ANAF synchronously - they
        apply a cache hit or queue the record - so tests that assert final
        values have to let the cron do its job.
        """
        self.env["ir.config_parameter"].sudo().set_param(
            "anaf_partner_bilant.throttle", "0"
        )
        self._partner_env()._cron_anaf_bilant_sync()
        self.env["res.partner"].invalidate_model()

    # ------------------------------------------------------------------
    # Fiscal code resolution
    # ------------------------------------------------------------------
    def test_cui_resolution(self):
        partner = self.env["res.partner"].create(
            {"name": "Test", "is_company": True}
        )
        for vat, expected in [
            ("RO14399840", EMAG_CUI),
            ("14399840", EMAG_CUI),
            (" ro 14.399.840 ", EMAG_CUI),
            ("14399841", False),  # broken check digit
            ("DE811907980", False),
            (False, False),
        ]:
            partner.with_context(skip_anaf_bilant=True).write({"vat": vat})
            self.assertEqual(partner._anaf_cui(), expected, vat)

    def test_bare_digits_ignored_for_non_romanian_country(self):
        partner = self.env["res.partner"].create(
            {"name": "Foreign", "is_company": True, "country_id": self.germany.id}
        )
        partner.with_context(skip_anaf_bilant=True).write({"vat": "14399840"})
        self.assertFalse(partner._anaf_cui())
        # An explicit RO prefix still wins over the country.
        partner.with_context(skip_anaf_bilant=True).write({"vat": "RO14399840"})
        self.assertEqual(partner._anaf_cui(), EMAG_CUI)

    def test_child_contacts_and_individuals_are_skipped(self):
        company = self._partner_env().create(
            {"name": "Parent", "is_company": True, "vat": EMAG_VAT}
        )
        child = self._partner_env().create(
            {"name": "Child", "parent_id": company.id, "vat": EMAG_VAT}
        )
        person = self._partner_env().create(
            {"name": "Person", "is_company": False, "vat": EMAG_VAT}
        )
        self.assertFalse(child._anaf_is_eligible())
        self.assertFalse(person._anaf_is_eligible())
        self.assertEqual(child.anaf_bilant_state, "none")
        self.assertEqual(person.anaf_bilant_state, "none")

    # ------------------------------------------------------------------
    # Value casting - covers the char Studio fields actually in use
    # ------------------------------------------------------------------
    def test_cast_char_field_keeps_digits_parseable(self):
        partner = self.env["res.partner"]
        char_field = partner._fields["ref"]
        self.assertEqual(
            partner._anaf_cast(char_field, "turnover", 8706154345.0), "8706154345"
        )
        self.assertEqual(partner._anaf_cast(char_field, "employees", 2889), "2889")
        self.assertEqual(partner._anaf_cast(char_field, "margin", -3.34), "-3.34")

    def test_cast_numeric_fields_after_a_studio_conversion(self):
        partner = self.env["res.partner"]
        integer_field = partner._fields["color"]
        float_field = self.env["res.currency"]._fields["rounding"]
        self.assertEqual(partner._anaf_cast(integer_field, "employees", 2889), 2889)
        self.assertEqual(partner._anaf_cast(float_field, "margin", -3.34), -3.34)
        self.assertIsInstance(
            partner._anaf_cast(float_field, "turnover", 8706154345.0), float
        )

    def test_studio_fields_exist_on_this_database(self):
        """Smoke test: flags a renamed or deleted Studio field early."""
        from ..models.res_partner import STUDIO_FIELD_MAP

        available = self.env["res.partner"]._fields
        missing = [name for name in STUDIO_FIELD_MAP if name not in available]
        self.assertFalse(
            missing,
            "Studio fields missing on res.partner: %s. Recreate them or "
            "update STUDIO_FIELD_MAP." % missing,
        )

    # ------------------------------------------------------------------
    # Trigger: create
    # ------------------------------------------------------------------
    def test_create_with_vat_is_queued_then_synced(self):
        partner = self._partner_env().create(
            {"name": "eMAG", "is_company": True, "vat": EMAG_VAT}
        )
        # A create must never block on HTTP - importing 5000 contacts cannot
        # mean 5000 synchronous requests inside one transaction.
        self.assertEqual(partner.anaf_bilant_state, "to_sync")

        self._drain_queue()
        self.assertEqual(partner.anaf_bilant_state, "done")
        self.assertEqual(partner.anaf_bilant_year, 2025)
        self.assertEqual(partner.anaf_bilant_cui, EMAG_CUI)
        self.assertTrue(partner.anaf_bilant_sync_date)

    def test_create_without_vat_stays_untouched(self):
        partner = self._partner_env().create({"name": "No VAT", "is_company": True})
        self.assertEqual(partner.anaf_bilant_state, "none")

    def test_unknown_cui_is_reported_not_zeroed(self):
        partner = self._partner_env().create(
            {"name": "Ghost", "is_company": True, "vat": NO_DATA_VAT}
        )
        self._drain_queue()
        self.assertEqual(partner.anaf_bilant_state, "no_data")
        self.assertFalse(partner.anaf_bilant_year)
        self.assertTrue(partner.anaf_bilant_message)

    # ------------------------------------------------------------------
    # Trigger: write (the requirement this module was extended for)
    # ------------------------------------------------------------------
    def test_updating_vat_resyncs(self):
        partner = self._partner_env().create(
            {"name": "Company", "is_company": True, "vat": EMAG_VAT}
        )
        self._drain_queue()
        self.assertEqual(partner.anaf_bilant_cui, EMAG_CUI)

        partner.write({"vat": ROMGAZ_VAT})
        self.assertEqual(partner.anaf_bilant_state, "to_sync")
        self._drain_queue()
        self.assertEqual(partner.anaf_bilant_cui, "14056826")
        self.assertEqual(partner.anaf_bilant_state, "done")

    def test_reformatting_the_same_vat_does_not_resync(self):
        partner = self._partner_env().create(
            {"name": "Company", "is_company": True, "vat": EMAG_VAT}
        )
        self._drain_queue()
        first_sync = partner.anaf_bilant_sync_date
        # Same fiscal code, different spelling - must be a no-op.
        partner.write({"vat": "14399840"})
        self.assertEqual(partner.anaf_bilant_sync_date, first_sync)
        self.assertEqual(partner.anaf_bilant_state, "done")

    def test_writing_unrelated_fields_does_not_resync(self):
        partner = self._partner_env().create(
            {"name": "Company", "is_company": True, "vat": EMAG_VAT}
        )
        self._drain_queue()
        first_sync = partner.anaf_bilant_sync_date
        partner.write({"phone": "0722000000"})
        self.assertEqual(partner.anaf_bilant_sync_date, first_sync)

    def test_write_without_cache_queues_for_the_cron(self):
        partner = self._partner_env().create({"name": "Later", "is_company": True})
        # An empty mapping means "ANAF knows nothing", so nothing lands in the
        # cache and the record has to be queued for the cron instead.
        partner.with_context(anaf_bilant_data={}).write({"vat": EMAG_VAT})
        self.assertEqual(partner.anaf_bilant_state, "to_sync")

    # ------------------------------------------------------------------
    # Trigger: onchange
    # ------------------------------------------------------------------
    def test_onchange_fills_metadata_in_the_form(self):
        with Form(self._partner_env()) as form:
            form.company_type = "company"
            form.name = "eMAG"
            form.vat = EMAG_VAT
            self.assertEqual(form.anaf_bilant_year, 2025)
            self.assertEqual(form.anaf_bilant_state, "done")
        self.assertEqual(form.record.anaf_bilant_cui, EMAG_CUI)

    # ------------------------------------------------------------------
    # Cache and cron
    # ------------------------------------------------------------------
    def test_cache_is_populated_and_reused(self):
        partner = self._partner_env().create(
            {"name": "eMAG", "is_company": True, "vat": EMAG_VAT}
        )
        self._drain_queue()
        cached = self.env["anaf.bilant"].search(
            [("cui", "=", EMAG_CUI), ("year", "=", 2025)]
        )
        self.assertEqual(len(cached), 1)
        self.assertEqual(cached.employees, 2889)
        self.assertEqual(cached.margin, -3.34)
        self.assertEqual(cached.partner_id, partner)

        # A second partner with the same fiscal code must not hit the service.
        twin = (
            self.env["res.partner"]
            .with_context(anaf_bilant_data={})
            .create({"name": "Twin", "is_company": True, "vat": EMAG_VAT})
        )
        self.assertEqual(twin.anaf_bilant_state, "done")
        self.assertEqual(twin.anaf_bilant_year, 2025)

    def test_cron_retries_a_previous_failure(self):
        partner = self._partner_env().create(
            {"name": "Flaky", "is_company": True, "vat": EMAG_VAT}
        )
        partner._anaf_set_status("error", "ANAF web service unreachable")
        self.assertEqual(partner.anaf_bilant_state, "error")

        # Freshly attempted errors are left alone until the back-off elapses.
        self._drain_queue()
        self.assertEqual(partner.anaf_bilant_state, "error")

        self.env["ir.config_parameter"].sudo().set_param(
            "anaf_partner_bilant.retry_hours", "-1"
        )
        self._drain_queue()
        self.assertEqual(partner.anaf_bilant_state, "done")
        self.assertEqual(partner.anaf_bilant_year, 2025)

    def test_manual_button_forces_a_refresh(self):
        partner = self._partner_env().create(
            {"name": "eMAG", "is_company": True, "vat": EMAG_VAT}
        )
        self._drain_queue()
        first_sync = partner.anaf_bilant_sync_date
        partner.with_context(
            anaf_bilant_data=ANAF_BILANT_DATA
        ).action_anaf_bilant_fetch()
        self.assertGreaterEqual(partner.anaf_bilant_sync_date, first_sync)
        self.assertEqual(partner.anaf_bilant_state, "done")
