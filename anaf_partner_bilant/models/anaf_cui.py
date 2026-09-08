# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Pure helpers for Romanian fiscal code (CUI/CIF) handling.

Deliberately free of any Odoo import so the logic can be unit tested in
isolation and reused from anywhere in the module.
"""

import re

# Accepts "RO14399840", "14399840", "ro 14 399 840", "RO-14399840".
_CUI_RE = re.compile(r"^(RO)?(\d{2,10})$")

# Official ANAF control key for the CUI check digit.
_CONTROL_KEY = (7, 5, 3, 2, 1, 7, 5, 3, 2)
_CONTROL_KEY_LENGTH = len(_CONTROL_KEY)


def normalize_vat(vat: str | bool | None) -> tuple[bool, str | bool]:
    """Return ``(has_ro_prefix, cui_digits)`` extracted from a raw VAT string.

    ``cui_digits`` is a canonical digit-only string without leading zeros, or
    ``False`` when the input cannot be read as a Romanian fiscal code.
    """
    if not vat:
        return False, False
    cleaned = re.sub(r"[\s.\-/]", "", vat).upper()
    match = _CUI_RE.match(cleaned)
    if not match:
        return False, False
    digits = str(int(match.group(2)))
    return bool(match.group(1)), digits


def is_valid_cui(cui: str | bool | None) -> bool:
    """Validate the ANAF check digit of a digit-only CUI string."""
    if not cui or not cui.isdigit() or len(cui) < 2:
        return False
    body, control_digit = cui[:-1], int(cui[-1])
    padded = body.rjust(_CONTROL_KEY_LENGTH, "0")
    if len(padded) > _CONTROL_KEY_LENGTH:
        return False
    weighted = sum(int(d) * k for d, k in zip(padded, _CONTROL_KEY))
    control = weighted * 10 % 11
    if control == 10:
        control = 0
    return control == control_digit
