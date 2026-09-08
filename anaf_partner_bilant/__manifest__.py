# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "ANAF Partner Bilant Enrichment",
    "summary": "Auto-fill partner financial data (turnover, employees, gross"
    " margin) from the ANAF /bilant public web service when the VAT is set",
    "category": "Localization",
    "countries": ["ro"],
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "author": "CG Hitech",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/anaf_bilant_views.xml",
        "views/res_partner_views.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "application": False,
}
