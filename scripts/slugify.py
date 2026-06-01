#!/usr/bin/env python3
"""Slugify a string into a URL-safe, lowercase, hyphen-separated token.

ASCII-only: non-ASCII characters (e.g. accented letters) are lossy — they are
treated as separators and dropped, not transliterated. "Café" -> "caf".
"""

import argparse
import re
import sys


def slugify(text: str) -> str:
    """Lowercase TEXT, collapse runs of non-[a-z0-9] into single hyphens, strip edges.

    Pure function: no side effects, no module-level state.
    """
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main() -> None:
    """Parse one positional argument, print its slug, exit 0."""
    parser = argparse.ArgumentParser(description="Slugify a string.")
    parser.add_argument("text", help="text to slugify")
    args = parser.parse_args()
    print(slugify(args.text))
    sys.exit(0)


if __name__ == "__main__":
    main()
