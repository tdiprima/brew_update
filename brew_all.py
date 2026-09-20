#!/usr/bin/env python3
"""Run the whole maintenance pass: update, upgrade, cleanup, doctor."""

import sys

import brew_cleanup
import brew_doctor
import brew_update
import brew_upgrade


def main(argv: list[str]) -> int:
    steps = [
        ("update", brew_update.main, ()),
        ("upgrade", brew_upgrade.main, (argv,)),
        ("cleanup", brew_cleanup.main, ()),
    ]
    if "--no-doctor" not in argv:
        steps.append(("doctor", brew_doctor.main, ()))

    failed = []
    for name, fn, args in steps:
        print(f"\n########## {name} ##########", flush=True)
        if fn(*args):
            failed.append(name)

    if failed:
        print(f"\nfailed steps: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\nall steps finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
