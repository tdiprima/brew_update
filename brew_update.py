#!/usr/bin/env python3
"""Refresh Homebrew itself and the formula/cask metadata."""

from brewlib import brew


def main() -> int:
    return brew("update", "--force")


if __name__ == "__main__":
    raise SystemExit(main())
