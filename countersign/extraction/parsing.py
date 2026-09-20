"""Turn the strings a document prints into typed values.

The extraction model's job is to find a field and copy what it says. Interpreting
that text is done here, in deterministic code, for three reasons: the same string
always parses the same way, a parsing bug has one place to fix, and the parsers
can be tested exhaustively against every notation the corpus contains without
calling a model at all.

So the model returns ``"BDT 1,234.56"`` and this module returns
``Decimal("1234.56")``. It never returns a float: see
:mod:`countersign.money`.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

#: Currency words and symbols that appear before or after an amount.
_CURRENCY_NOISE = re.compile(
    r"^(?:bdt|usd|eur|gbp|tk\.?|taka|৳|\$|€|£)\s*|\s*(?:bdt|usd|eur|gbp|tk\.?|taka)$",
    re.IGNORECASE,
)
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}\b)")
_SPACES = re.compile(r"[\s  ]+")

#: Date formats the four layouts and the spreadsheets use, most specific first.
DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%Y/%m/%d",
)


class ParseError(ValueError):
    """Raised when a field cannot be read. Never guessed around."""


def parse_amount(text: str | Decimal | int) -> Decimal:
    """Read an amount as it was printed.

    Handles ``BDT 1,234.56``, ``1,234.56 BDT``, ``Tk. 1,234.56``, ``1234.56``,
    parenthesised negatives and a trailing minus.

    >>> parse_amount("Tk. 1,234.56")
    Decimal('1234.56')
    >>> parse_amount("(1,200.00)")
    Decimal('-1200.00')
    """
    if isinstance(text, Decimal):
        return text
    if isinstance(text, int):
        return Decimal(text)
    if not isinstance(text, str):
        raise ParseError(f"cannot read {text!r} as an amount")

    cleaned = _SPACES.sub(" ", text).strip()
    if not cleaned:
        raise ParseError("empty amount")

    negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        negative, cleaned = True, cleaned[1:-1].strip()
    if cleaned.endswith("-"):
        negative, cleaned = True, cleaned[:-1].strip()

    # One pass removes a currency at either end, or at both.
    cleaned = _CURRENCY_NOISE.sub("", cleaned).strip()
    cleaned = _THOUSANDS.sub("", cleaned)

    if cleaned.startswith("-"):
        negative, cleaned = True, cleaned[1:].strip()

    if not re.fullmatch(r"\d+(?:\.\d+)?", cleaned):
        raise ParseError(f"cannot read {text!r} as an amount")

    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:  # pragma: no cover - guarded by the regex above
        raise ParseError(f"cannot read {text!r} as an amount") from exc

    return -value if negative else value


def parse_quantity(text: str | Decimal | int) -> Decimal:
    """Quantities print like amounts but never carry a currency."""
    return parse_amount(text)


def parse_date(text: str | date) -> date:
    """Read a date in any format the corpus prints.

    Ambiguous day/month pairs are read as day-first, because every layout here is
    day-first and the ISO layout is unambiguous anyway. A format that cannot be
    matched raises rather than falling back to a guess.

    >>> parse_date("15 Mar 2026")
    datetime.date(2026, 3, 15)
    >>> parse_date("15/03/2026")
    datetime.date(2026, 3, 15)
    """
    if isinstance(text, date):
        return text
    if not isinstance(text, str):
        raise ParseError(f"cannot read {text!r} as a date")

    cleaned = _SPACES.sub(" ", text).strip().rstrip(".")
    if not cleaned:
        raise ParseError("empty date")

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    raise ParseError(f"cannot read {text!r} as a date")


def parse_rate(text: str | Decimal | int) -> Decimal:
    """Read a tax rate, with or without a percent sign.

    >>> parse_rate("7.5%")
    Decimal('7.5')
    """
    if isinstance(text, str):
        text = text.replace("%", "").strip()
    return parse_amount(text)


def parse_currency(text: str) -> str:
    """Normalise a currency to a three-letter code.

    ``Tk.`` and ``Taka`` are how BDT is written on these documents; they are the
    only aliases accepted, because inventing more would mean guessing.
    """
    cleaned = _SPACES.sub("", text or "").strip().upper().rstrip(".")
    aliases = {"TK": "BDT", "TAKA": "BDT", "৳": "BDT", "$": "USD", "US$": "USD"}
    cleaned = aliases.get(cleaned, cleaned)
    if not re.fullmatch(r"[A-Z]{3}", cleaned):
        raise ParseError(f"cannot read {text!r} as a currency code")
    return cleaned
