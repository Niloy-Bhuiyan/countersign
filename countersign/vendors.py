"""Vendor name normalisation.

Duplicate detection compares vendors, and the same supplier arrives spelled four
different ways across four documents: ``Meghna Steel Ltd``, ``MEGHNA STEEL
LIMITED``, ``Meghna  Steel``, ``Meghna Steel Ltd.``. Normalisation collapses those
onto one key.

The rules are a committed table, not a similarity model. A controller asked why
two invoices were treated as the same vendor must be able to read the rule that
made them equal, and get the same answer by hand. Nothing here is probabilistic.

Only *legal form* is stripped. Trade words are part of the name and stay: stripping
``Industries`` would merge ``Padma Industries`` into ``Padma``, which are different
suppliers.
"""

from __future__ import annotations

import re

#: Legal-form suffixes, longest first so that "private limited" is removed as a
#: unit before "limited" can match part of it.
LEGAL_SUFFIXES: tuple[str, ...] = (
    "private limited",
    "pvt limited",
    "pvt ltd",
    "public limited company",
    "limited",
    "ltd",
    "plc",
    "incorporated",
    "inc",
    "corporation",
    "corp",
    "company",
    "and sons",
    "& sons",
    "and co",
    "& co",
    "co",
)

_PUNCTUATION = re.compile(r"[.,'\"()\-/\\]+")
_WHITESPACE = re.compile(r"\s+")
_LEADING_THE = re.compile(r"^the\s+")


def normalise_vendor_name(name: str) -> str:
    """Return the comparison key for a vendor name.

    >>> normalise_vendor_name("MEGHNA STEEL LIMITED")
    'meghna steel'
    >>> normalise_vendor_name("Meghna Steel Ltd.")
    'meghna steel'
    >>> normalise_vendor_name("Padma Industries Ltd")
    'padma industries'
    """
    text = _PUNCTUATION.sub(" ", name.casefold())
    text = _WHITESPACE.sub(" ", text).strip()
    text = _LEADING_THE.sub("", text)

    # Suffixes can stack: "Rupsha Trading Co Ltd". Strip repeatedly until nothing
    # matches, so order of appearance does not change the result.
    changed = True
    while changed:
        changed = False
        for suffix in LEGAL_SUFFIXES:
            if text.endswith(" " + suffix):
                text = text[: -len(suffix) - 1].strip()
                changed = True
                break

    return _WHITESPACE.sub(" ", text).strip()
