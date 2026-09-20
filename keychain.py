#!/usr/bin/env python3
"""Keychain access for the brew maintenance scripts.

Stores and reads the sudo password that cask upgrades need, and hands it to
sudo through a throwaway SUDO_ASKPASS helper. Run this file directly to store
(or replace) the password.
"""

from __future__ import annotations

import getpass
import os
import shlex
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager

SERVICE = os.environ.get("BREW_KEYCHAIN_SERVICE", "brew-sudo")
ACCOUNT = os.environ.get("BREW_KEYCHAIN_ACCOUNT", os.environ.get("USER", ""))


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
            f"Run: python3 keychain.py"
        )
    return result.stdout.rstrip("\n")


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


if __name__ == "__main__":
    raise SystemExit(set_password())
