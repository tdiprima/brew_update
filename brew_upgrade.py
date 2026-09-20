#!/usr/bin/env python3
"""Upgrade formulae and casks, feeding sudo from the keychain.

Casks with pkg installers or privileged payloads ask for root. Homebrew uses
`sudo -A` when SUDO_ASKPASS is set, so the password never touches the tty.
"""

import sys

from brewlib import askpass_env, brew, get_password


def main(argv: list[str]) -> int:
    greedy = "--no-greedy" not in argv
    password = get_password()

    with askpass_env(password) as env:
        status = brew("upgrade", "--formula", env=env)

        cask_args = ["upgrade", "--cask"]
        if greedy:
            cask_args.append("--greedy")
        status |= brew(*cask_args, env=env)

    return 1 if status else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
