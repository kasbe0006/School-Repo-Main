"""
Shared schema pieces: the strict base model, reusable field types, and money helpers.

MONEY RULE
    The database stores money as INTEGER paise (1500.50 rupees -> 150050).
    - Requests send rupees as a decimal number, e.g. {"amount": 1500.50}.
      rupees_to_paise() turns it into an integer before it touches the database.
    - Responses return BOTH: the raw integer (e.g. "amount": 150050), which the
      frontend formats with formatMoney(paise), and a decimal text
      "amount_rupees": "1500.50" made here in the API layer.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Base model
# ---------------------------------------------------------------------------
class StrictModel(BaseModel):
    """
    Base for all request bodies.
    extra="forbid" -> unknown fields are rejected (a typo like "capcity" gives 422).
    str_strip_whitespace -> "  CSE " becomes "CSE".
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---------------------------------------------------------------------------
# Reusable field types. The Literal lists match the CHECK constraints in
# sql/01_tables.sql, so bad values are stopped here BEFORE reaching the database.
# ---------------------------------------------------------------------------
Role = Literal["admin", "teacher", "student", "accountant"]
TimeText = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$", examples=["09:30"])]
Name = Annotated[str, Field(min_length=1, max_length=80)]
Phone = Annotated[str, Field(pattern=r"^\+?[0-9]{7,15}$", examples=["01712345678"])]
Password = Annotated[str, Field(min_length=8, max_length=128)]

# Rupees amounts: at most 2 decimal places, as in real money
Rupees = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2, examples=[1500.50])]
PositiveRupees = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2, examples=[1500.50])]


# ---------------------------------------------------------------------------
# Money helpers
# ---------------------------------------------------------------------------
def rupees_to_paise(rupees: Decimal | int | float | str) -> int:
    """1500.50 rupees -> 150050 paise. Decimal avoids float surprises like 0.1 + 0.2."""
    amount = Decimal(str(rupees)) * 100
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def paise_to_rupees(paise: int | None) -> str | None:
    """150050 paise -> "1500.50" (text, so no float rounding can creep in)."""
    if paise is None:
        return None
    return f"{Decimal(paise) / 100:.2f}"


def add_rupees_fields(row: dict, *money_fields: str) -> dict:
    """For each money field X in the row, add X_rupees with the decimal text. Returns the same dict."""
    for field in money_fields:
        if field in row:
            row[f"{field}_rupees"] = paise_to_rupees(row[field])
    return row
