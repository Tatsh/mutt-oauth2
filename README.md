# mutt-oauth2

[![Python versions](https://img.shields.io/pypi/pyversions/mutt-oauth2.svg?color=blue&logo=python&logoColor=white)](https://www.python.org/)
[![PyPI - Version](https://img.shields.io/pypi/v/mutt-oauth2)](https://pypi.org/project/mutt-oauth2/)
[![GitHub tag (with filter)](https://img.shields.io/github/v/tag/Tatsh/mutt-oauth2)](https://github.com/Tatsh/mutt-oauth2/tags)
[![License](https://img.shields.io/github/license/Tatsh/mutt-oauth2)](https://github.com/Tatsh/mutt-oauth2/blob/master/LICENSE.txt)
[![GitHub commits since latest release (by SemVer including pre-releases)](https://img.shields.io/github/commits-since/Tatsh/mutt-oauth2/v0.1.0/master)](https://github.com/Tatsh/mutt-oauth2/compare/v0.1.0...master)
[![QA](https://github.com/Tatsh/mutt-oauth2/actions/workflows/qa.yml/badge.svg)](https://github.com/Tatsh/mutt-oauth2/actions/workflows/qa.yml)
[![Tests](https://github.com/Tatsh/mutt-oauth2/actions/workflows/tests.yml/badge.svg)](https://github.com/Tatsh/mutt-oauth2/actions/workflows/tests.yml)
[![Coverage Status](https://coveralls.io/repos/github/Tatsh/mutt-oauth2/badge.svg?branch=master)](https://coveralls.io/github/Tatsh/mutt-oauth2?branch=master)
[![Documentation Status](https://readthedocs.org/projects/mutt-oauth2/badge/?version=latest)](https://mutt-oauth2.readthedocs.org/?badge=latest)
[![mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![pydocstyle](https://img.shields.io/badge/pydocstyle-enabled-AD4CD3)](http://www.pydocstyle.org/en/stable/)
[![pytest](https://img.shields.io/badge/pytest-zz?logo=Pytest&labelColor=black&color=black)](https://docs.pytest.org/en/stable/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Downloads](https://static.pepy.tech/badge/mutt-oauth2/month)](https://pepy.tech/project/mutt-oauth2)
[![Stargazers](https://img.shields.io/github/stars/Tatsh/mutt-oauth2?logo=github&style=flat)](https://github.com/Tatsh/mutt-oauth2/stargazers)

[![@Tatsh](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpublic.api.bsky.app%2Fxrpc%2Fapp.bsky.actor.getProfile%2F%3Factor%3Ddid%3Aplc%3Auq42idtvuccnmtl57nsucz72%26query%3D%24.followersCount%26style%3Dsocial%26logo%3Dbluesky%26label%3DFollow%2520%40Tatsh&query=%24.followersCount&style=social&logo=bluesky&label=Follow%20%40Tatsh)](https://bsky.app/profile/Tatsh.bsky.social)
[![Mastodon Follow](https://img.shields.io/mastodon/follow/109370961877277568?domain=hostux.social&style=social)](https://hostux.social/@Tatsh)

This is an update of [Alexander Perlis' script](https://github.com/muttmua/mutt/blob/master/contrib/mutt_oauth2.py)
and conversion to a package. Instead of using GPG for token storage, this package uses Keyring.

## Installation

### Pip

```shell
pip install mutt-oauth2
```

## Usage

```plain
Usage: mutt-oauth2 [OPTIONS]

  Obtain and print a valid OAuth2 access token.

Options:
  -a, --authorize      Manually authorise new tokens.
  -d, --debug          Enable debug logging.
  -t, --test           Test authentication.
  -u, --username TEXT  Keyring username.
  -v, --verbose        Enable verbose logging.
  -h, --help           Show this message and exit.
```

Start by calling `mutt-oauth2 -a`. Be sure to have your client ID and and client secret available.

### Scopes required

| Provider  | Scopes                                                              |
| --------- | ------------------------------------------------------------------- |
| Gmail     | Gmail API                                                           |
| Microsoft | offline_access IMAP.AccessAsUser.All POP.AccessAsUser.All SMTP.Send |

To support other accounts, use the `--username` argument with a unique string such as the account
email address.

Test the script with the `--test` argument.

### mutt configuration

Add the following to `muttrc`:

```plain
set imap_authenticators="oauthbearer:xoauth2"
set imap_oauth_refresh_command="/path/to/mutt-oauth2"
set smtp_authenticators=${imap_authenticators}
set smtp_oauth_refresh_command=${imap_oauth_refresh_command}
```
