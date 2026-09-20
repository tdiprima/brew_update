#!/usr/bin/env python3
"""Report on the health of the installation. Never fatal."""

from brewlib import brew


def main() -> int:
    brew("doctor")
    brew("missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
