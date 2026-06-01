#!/usr/bin/env python3
"""Co-located test for slugify.

Run from the repo root:

    python3 scripts/slugify_test.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from slugify import slugify


def main() -> None:
    """Assert slugify behaviour across the specified cases, then report pass."""
    assert slugify("") == ""
    assert slugify("  Hello,  World!! ") == "hello-world"
    assert slugify("RUS-44: Add a thing") == "rus-44-add-a-thing"
    assert slugify("Café") == "caf"
    assert slugify("!!!") == ""
    print("PASS: slugify_test")
    sys.exit(0)


if __name__ == "__main__":
    main()
