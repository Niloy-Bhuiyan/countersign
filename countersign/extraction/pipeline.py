"""Document in, typed invoice or a reason for review out.

``validators=False`` exists for the evaluation only. It is the configuration the
evaluation calls v1: the reader's output accepted as it stands. Comparing it with
v2, the same reader with arithmetic validation, is how the validators' value is
measured rather than asserted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from countersign.extraction import offline
from countersign.extraction.schema import ExtractedInvoice, FieldFailure, parse_raw
from countersign.extraction.validators import validate
from countersign.intake import Intake, read


@dataclass
class ExtractionOutcome:
    intake: Intake
    invoice: ExtractedInvoice | None = None
    failures: list[FieldFailure] = field(default_factory=list)
    provider: str = offline.NAME
    version: str = offline.VERSION

    @property
    def ok(self) -> bool:
        return self.invoice is not None

    @property
    def review_reason(self) -> str | None:
        if not self.intake.readable:
            return self.intake.status
        if self.failures:
            return "extraction_failed"
        return None


def extract_document(path: Path, *, validators: bool = True) -> ExtractionOutcome:
    intake = read(path)
    if not intake.readable:
        return ExtractionOutcome(intake=intake)

    parsed = parse_raw(offline.extract(intake))
    if not parsed.ok:
        return ExtractionOutcome(intake=intake, failures=parsed.failures)

    if validators:
        failures = validate(parsed.invoice)
        if failures:
            return ExtractionOutcome(intake=intake, failures=failures)

    version = offline.VERSION + ("+validators" if validators else "")
    return ExtractionOutcome(intake=intake, invoice=parsed.invoice, version=version)
