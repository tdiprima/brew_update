#!/usr/bin/env python3
"""Homebrew maintenance: update, upgrade, cleanup, doctor.

The sudo password that cask upgrades need is read from the macOS login
keychain, so nothing is typed at the prompt and no password lives in this
file.
"""

from __future__ import annotations

import argparse
import getpass
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager

SERVICE = os.environ.get("BREW_KEYCHAIN_SERVICE", "brew-sudo")
ACCOUNT = os.environ.get("BREW_KEYCHAIN_ACCOUNT", os.environ.get("USER", ""))


class KeychainError(RuntimeError):
    """Raised when the sudo password cannot be read from the keychain."""


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


def get_password(service: str = SERVICE, account: str = ACCOUNT) -> str:
    """Read the sudo password out of the login keychain."""
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise KeychainError(
            f"No keychain item for service={service!r} account={account!r}.\n"
            f"Run: python3 brew_maint.py set-password"
        )
    return result.stdout.rstrip("\n")


@contextmanager
def askpass_env(password: str):
    """Yield an env dict with SUDO_ASKPASS pointing at a throwaway helper.

    Homebrew runs `sudo -A` when SUDO_ASKPASS is set, so cask upgrades that
    need root never prompt on the tty.
    """
    pw_fd, pw_path = tempfile.mkstemp(prefix="brew-askpass-pw-")
    try:
        with os.fdopen(pw_fd, "w") as handle:
            handle.write(password + "\n")
        os.chmod(pw_path, stat.S_IRUSR | stat.S_IWUSR)

        fd, path = tempfile.mkstemp(prefix="brew-askpass-", suffix=".sh")
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(f"#!/bin/sh\nexec cat {shlex.quote(pw_path)}\n")
            os.chmod(path, stat.S_IRWXU)

            env = os.environ.copy()
            env["SUDO_ASKPASS"] = path
            yield env
        finally:
            os.remove(path)
    finally:
        os.remove(pw_path)


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


def set_password() -> int:
    """Store (or replace) the sudo password used by the upgrade step."""
    password = getpass.getpass(f"sudo password for {ACCOUNT}: ")
    if not password:
        sys.exit("empty password, nothing stored")

    result = subprocess.run(
        ["security", "add-generic-password", "-U",
         "-s", SERVICE, "-a", ACCOUNT, "-w", password,
         "-D", "application password",
         "-j", "sudo password for brew cask upgrades"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.exit(result.stderr.strip())

    print(f"stored: service={SERVICE} account={ACCOUNT}")
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
        choices=["all", "update", "upgrade", "cleanup", "doctor", "set-password"],
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
    if args.command == "doctor":
        return doctor()
    return set_password()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
