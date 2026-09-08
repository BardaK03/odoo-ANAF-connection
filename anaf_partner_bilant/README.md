# ANAF Partner Bilant Enrichment (Odoo 19)

Fills the existing Studio fields on **Contacts** from the public ANAF
`/bilant` web service as soon as a Romanian VAT number is entered or changed.

## Field mapping

| ANAF indicator | Meaning (label returned by ANAF) | Odoo field |
|---|---|---|
| `I13` | Cifra de afaceri neta | `x_studio_ca_2024` |
| `I20` | Numar mediu de salariati | `x_studio_nr_angajati_2024` |
| `(I16 - I17) / I13 * 100` | Gross margin, % | `x_studio_profitabilitate_gross_profit` |

`I16` is *Profit brut* and `I17` is *Pierdere bruta*; ANAF fills exactly one of
them, so the difference is the signed gross result. `I18`/`I19` are the **net**
figures and are stored in the history model only.

Reference values verified against the live service for fiscal year 2025:

| Company | Turnover | Employees | Gross margin |
|---|---|---|---|
| Romgaz SA (14056826) | 7,579,634,046 | 5,227 | +47.52 % |
| Antibiotice SA (1973096) | 645,275,929 | 1,370 | +9.32 % |
| Dante International / eMAG (14399840) | 8,706,154,345 | 2,889 | -3.34 % |

## Triggers

| Trigger | Fires on | Covers |
|---|---|---|
| `_onchange_vat_anaf_bilant` | VAT edited in the form, on create **and** on update | Interactive use; values appear before saving |
| `create` / `write` hooks | Any ORM write where the canonical fiscal code changed | CSV import, XML-RPC, mass edit - onchange does not run there |
| `_cron_anaf_bilant_sync` (5 min) | Records in `to_sync`, plus `error` records that backed off | Retries after an ANAF outage |
| `_cron_anaf_bilant_refresh` (daily) | Records whose fiscal year is older than the newest published one | Yearly data rollover |
| "Fetch from ANAF" button | Manual, bypasses the cache | On-demand refresh |

Reformatting a VAT (`14399840` to `RO14399840`) is **not** treated as a change:
the canonical fiscal code is compared, not the raw string.

## Guards

* Only `is_company` records without a `parent_id` are queried.
* A bare numeric VAT counts as Romanian only when the country is RO or unset;
  an explicit `RO` prefix always wins.
* The CUI check digit is validated locally, so typos never reach ANAF.
* ANAF answers **HTTP 200 with an empty body** for unknown fiscal codes and for
  years not yet filed. The module treats an empty indicator list - not the
  status code - as "no data", and leaves existing values untouched rather than
  overwriting them with zeros.
* An undefined margin (zero turnover) leaves the field alone instead of
  writing `0`.

## Configuration

`Settings > Technical > System Parameters`:

| Key | Default | Purpose |
|---|---|---|
| `anaf_partner_bilant.url` | `https://webservicesp.anaf.ro/bilant` | Endpoint |
| `anaf_partner_bilant.timeout` | `10` | HTTP timeout, seconds |
| `anaf_partner_bilant.year` | *(unset)* | Pin a fiscal year; unset means last year, falling back one more |
| `anaf_partner_bilant.cache_days` | `30` | Cache TTL; `0` disables the cache |
| `anaf_partner_bilant.sync_mode` | `cron` | `immediate` makes `write` fetch synchronously |
| `anaf_partner_bilant.cron_batch` | `50` | Records per cron run |
| `anaf_partner_bilant.throttle` | `1.0` | Seconds between requests |
| `anaf_partner_bilant.retry_hours` | `6` | Back-off before retrying an error |
| `anaf_partner_bilant.stale_days` | `30` | Staleness window for the daily refresh |

Disable everything by deactivating the two crons and setting
`anaf_partner_bilant.sync_mode` aside; the onchange can be short-circuited per
call with the `skip_anaf_bilant` context key.

## Install

```bash
# copy the folder into your addons path, then
odoo-bin -c odoo.conf -d <database> -i anaf_partner_bilant --stop-after-init
```

## Test

```bash
odoo-bin -c odoo.conf -d <database> \
    -u anaf_partner_bilant --test-enable \
    --test-tags /anaf_partner_bilant --stop-after-init --log-level=test
```

The suite runs entirely offline: `tests/anaf_bilant_data.py` holds real ANAF
payloads, injected through the `anaf_bilant_data` context key that
`anaf.bilant.client.fetch` honours. No HTTP call is made.

## Known limitations

* `x_studio_ca_2024` and `x_studio_nr_angajati_2024` are `char` fields, so the
  module writes plain digit strings (`"8706154345"`). Converting them to
  `Float`/`Integer` in Studio enables numeric sorting, `>` filters and list
  aggregation; the module casts at runtime and needs no change afterwards.
* The field names say `2024` while the data comes from the newest published
  year. `anaf_bilant_year` on the ANAF tab shows the real year; relabelling the
  Studio fields is safe (labels carry no data).
