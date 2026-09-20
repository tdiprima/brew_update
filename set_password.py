#!/usr/bin/env python3
"""Store (or replace) the sudo password used by the upgrade script."""

import getpass
import subprocess
import sys

from brewlib import ACCOUNT, SERVICE


def main() -> int:
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


if __name__ == "__main__":
    raise SystemExit(main())
