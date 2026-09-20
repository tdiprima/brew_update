"""Shared helpers for the brew maintenance scripts."""

from __future__ import annotations

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


class KeychainError(RuntimeError):
    """Raised when the sudo password cannot be read from the keychain."""


def get_password(service: str = SERVICE, account: str = ACCOUNT) -> str:
    """Read the sudo password out of the login keychain."""
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise KeychainError(
            f"No keychain item for service={service!r} account={account!r}.\n"
            f"Run: python3 set_password.py"
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
