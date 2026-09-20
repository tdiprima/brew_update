#!/usr/bin/env python3
"""Homebrew maintenance: update, upgrade, cleanup, doctor.

The sudo password that cask upgrades need comes from keychain.py, so nothing
is typed at the prompt.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

from keychain import KeychainError, askpass_env, get_password


def brew_path() -> str:
    for candidate in (os.environ.get("HOMEBREW_PREFIX", "") + "/bin/brew",
                      "/opt/homebrew/bin/brew", "/usr/local/bin/brew"):
        if candidate and os.path.isfile(candidate):
            return candidate
    found = shutil.which("brew")
    if not found:
        sys.exit("brew not found in PATH")
    return found


BREW = brew_path()


def run(args: list[str], env: dict | None = None, check: bool = False) -> int:
    """Run a command, streaming its output; return the exit code."""
    print(f"\n==> {' '.join(args)}", flush=True)
    code = subprocess.run(args, env=env).returncode
    if code != 0:
        print(f"!!! exited {code}: {' '.join(args)}", file=sys.stderr, flush=True)
        if check:
            sys.exit(code)
    return code


def brew(*args: str, env: dict | None = None, check: bool = False) -> int:
    return run([BREW, *args], env=env, check=check)


def update() -> int:
    """Refresh Homebrew itself and the formula/cask metadata."""
    return brew("update", "--force")


def upgrade(greedy: bool = True) -> int:
    """Upgrade formulae and casks, feeding sudo from the keychain."""
    try:
        password = get_password()
    except KeychainError as exc:
        print(f"!!! {exc}", file=sys.stderr, flush=True)
        return 1

    with askpass_env(password) as env:
        status = brew("upgrade", "--formula", env=env)

        cask_args = ["upgrade", "--cask"]
        if greedy:
            cask_args.append("--greedy")
        status |= brew(*cask_args, env=env)

    return 1 if status else 0


def cleanup() -> int:
    """Remove unused dependencies, stale downloads and old versions."""
    status = brew("autoremove")
    status |= brew("cleanup", "--prune=all", "-s")
    return 1 if status else 0


def doctor() -> int:
    """Report on the health of the installation. Never fatal."""
    brew("doctor")
    brew("missing")
    return 0


def run_all(greedy: bool = True, with_doctor: bool = True) -> int:
    """Run the whole maintenance pass: update, upgrade, cleanup, doctor."""
    steps = [
        ("update", update, ()),
        ("upgrade", upgrade, (greedy,)),
        ("cleanup", cleanup, ()),
    ]
    if with_doctor:
        steps.append(("doctor", doctor, ()))

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


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "command", nargs="?", default="all",
        choices=["all", "update", "upgrade", "cleanup", "doctor"],
        help="which step to run (default: all)",
    )
    parser.add_argument("--no-greedy", action="store_true",
                        help="skip casks that update themselves")
    parser.add_argument("--no-doctor", action="store_true",
                        help="with 'all': stop after cleanup")
    args = parser.parse_args(argv)

    greedy = not args.no_greedy
    if args.command == "all":
        return run_all(greedy=greedy, with_doctor=not args.no_doctor)
    if args.command == "update":
        return update()
    if args.command == "upgrade":
        return upgrade(greedy=greedy)
    if args.command == "cleanup":
        return cleanup()
    return doctor()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
