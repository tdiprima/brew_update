# brew_update

Homebrew maintenance in one Python script. The sudo password that cask
upgrades need is read from the macOS login keychain via
`security find-generic-password`, so nothing is typed at the prompt and no
password is stored in the file.

## Setup

Store the password once:

```sh
python3 brew_maint.py set-password
```

It prompts (hidden input) and writes a generic-password item to the login
keychain under service `brew-sudo`, account `$USER`. Re-running it replaces
the stored value.

Override the item's name with environment variables if you already keep the
password somewhere else:

```sh
export BREW_KEYCHAIN_SERVICE=my-sudo
export BREW_KEYCHAIN_ACCOUNT=username
```

The first read may pop a keychain access dialog. Choose **Always Allow** to
stop it asking again.

## Usage

Everything, in order — update, upgrade, cleanup, doctor:

```sh
python3 brew_maint.py
```

Or one step at a time:

| Command | What it runs |
| --- | --- |
| `brew_maint.py update` | `brew update --force` |
| `brew_maint.py upgrade` | `brew upgrade --formula`, then `brew upgrade --cask --greedy` |
| `brew_maint.py cleanup` | `brew autoremove`, `brew cleanup --prune=all -s` |
| `brew_maint.py doctor` | `brew doctor`, `brew missing` (advisory, never fails) |
| `brew_maint.py set-password` | store the sudo password in the keychain |

### Flags

- `--no-greedy` — skip casks that update themselves.
- `--no-doctor` — with `all` (the default): stop after cleanup.

## How the password gets to sudo

`askpass_env()` writes the password to a temporary file readable only by you,
plus a one-line helper script that `cat`s it, then points `SUDO_ASKPASS` at
that helper. Homebrew switches to `sudo -A` when it sees `SUDO_ASKPASS`, so
privileged cask steps ask the helper instead of the terminal. Both temp files
are deleted when the upgrade finishes, including on error.

## Exit codes

`0` when every step succeeded. `1` when any step failed; the full pass keeps
going through the remaining steps and lists the failures at the end. A
missing or unreadable keychain item fails the upgrade step only — cleanup and
doctor still run.

## Requirements

macOS with Homebrew and Python 3.13+ (the system `python3` is fine). No
third-party packages.

<br>
