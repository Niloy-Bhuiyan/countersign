"""Document emission, tested on a slice rather than the whole corpus.

Rendering five hundred files takes seconds; these assertions do not need them all.
The one property worth checking against the full corpus is which invoices get an
unreadable file, and that is a pure function.
"""

import random

from data.documents import N_CORRUPT, N_ENCRYPTED, N_IMAGE_ONLY, _unreadable_assignments, emit


def test_unreadable_files_are_never_given_to_a_defective_invoice(corpus):
    """Otherwise recall would be depressed by defects nothing could have caught."""
    assignments = _unreadable_assignments(random.Random(3), corpus["invoices"])
    defective = {inv.id for inv in corpus["invoices"] if inv.defect}
    assert assignments
    assert not (set(assignments) & defective)


def test_the_unreadable_mix_is_what_was_configured(corpus):
    assignments = _unreadable_assignments(random.Random(3), corpus["invoices"])
    counts = {value: list(assignments.values()).count(value) for value in set(assignments.values())}
    assert counts["quarantined_image_only"] == N_IMAGE_ONLY
    assert counts["quarantined_unreadable"] == N_CORRUPT
    assert counts["quarantined_encrypted"] == N_ENCRYPTED


def test_emit_writes_one_file_per_invoice(corpus, tmp_path):
    subset = corpus["invoices"][:12]
    manifest = emit(random.Random(5), corpus["vendors"], subset, directory=tmp_path)

    assert len(manifest) == len(subset)
    assert {row["invoice_id"] for row in manifest} == {inv.id for inv in subset}
    for row in manifest:
        assert (tmp_path / row["filename"]).exists()
        assert row["bytes"] > 0


def test_the_name_written_on_a_document_still_identifies_the_vendor(corpus, tmp_path):
    from countersign.vendors import normalise_vendor_name

    by_vendor = {vendor.id: vendor for vendor in corpus["vendors"]}
    manifest = emit(
        random.Random(5), corpus["vendors"], corpus["invoices"][:30], directory=tmp_path
    )

    for row in manifest:
        expected = normalise_vendor_name(by_vendor[row["vendor_id"]].legal_name)
        assert normalise_vendor_name(row["vendor_name_as_written"]) == expected
