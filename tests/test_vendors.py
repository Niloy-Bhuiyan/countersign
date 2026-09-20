"""Vendor normalisation has to be boring and exact. These pin the table's behaviour."""

import pytest

from countersign.vendors import normalise_vendor_name


@pytest.mark.parametrize(
    "written",
    [
        "Meghna Steel Ltd",
        "MEGHNA STEEL LIMITED",
        "Meghna  Steel",
        "Meghna Steel Ltd.",
        "meghna steel ltd",
        "Meghna Steel, Ltd.",
        "The Meghna Steel Limited",
    ],
)
def test_one_supplier_spelled_seven_ways(written):
    assert normalise_vendor_name(written) == "meghna steel"


def test_stacked_legal_suffixes_are_all_removed():
    assert normalise_vendor_name("Rupsha Trading Co Ltd") == "rupsha trading"
    assert normalise_vendor_name("Titas Packaging Pvt Ltd") == "titas packaging"


def test_trade_words_are_not_stripped():
    # Two different suppliers. Stripping "Industries" as if it were a legal form
    # would merge them and let a duplicate check fire across unrelated vendors.
    assert normalise_vendor_name("Padma Industries Ltd") == "padma industries"
    assert normalise_vendor_name("Padma Ltd") == "padma"
    assert normalise_vendor_name("Padma Industries Ltd") != normalise_vendor_name("Padma Ltd")


def test_ampersand_and_written_forms_agree():
    assert normalise_vendor_name("Surma Jute & Sons") == normalise_vendor_name(
        "Surma Jute and Sons"
    )


def test_a_name_that_is_only_a_suffix_survives():
    # Guards the strip loop against eating the whole name and returning "".
    assert normalise_vendor_name("Limited") == "limited"
