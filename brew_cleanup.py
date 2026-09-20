#!/usr/bin/env python3
"""Remove unused dependencies, stale downloads and old versions."""

from brewlib import brew


def main() -> int:
    status = brew("autoremove")
    status |= brew("cleanup", "--prune=all", "-s")
    return 1 if status else 0


if __name__ == "__main__":
    raise SystemExit(main())
