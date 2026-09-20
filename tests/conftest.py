import random

import pytest

from countersign.settings import settings
from data.generate import build


@pytest.fixture(scope="session")
def corpus():
    """The full synthetic corpus at the committed seed."""
    return build(settings.corpus_seed)


@pytest.fixture
def rng():
    return random.Random(1)
