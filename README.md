# OAuth2 script for Mutt

[![QA](https://github.com/Tatsh/mutt-oauth2/actions/workflows/qa.yml/badge.svg)](https://github.com/Tatsh/mutt-oauth2/actions/workflows/qa.yml)
[![Tests](https://github.com/Tatsh/mutt-oauth2/actions/workflows/tests.yml/badge.svg)](https://github.com/Tatsh/mutt-oauth2/actions/workflows/tests.yml)
[![Coverage Status](https://coveralls.io/repos/github/Tatsh/mutt-oauth2/badge.svg?branch=master)](https://coveralls.io/github/Tatsh/mutt-oauth2?branch=master)
[![Documentation Status](https://readthedocs.org/projects/mutt-oauth2/badge/?version=latest)](https://mutt-oauth2.readthedocs.io/en/latest/?badge=latest)
![PyPI - Version](https://img.shields.io/pypi/v/mutt-oauth2)
![GitHub tag (with filter)](https://img.shields.io/github/v/tag/Tatsh/mutt-oauth2)
![GitHub](https://img.shields.io/github/license/Tatsh/mutt-oauth2)
![GitHub commits since latest release (by SemVer including pre-releases)](https://img.shields.io/github/commits-since/Tatsh/mutt-oauth2/v0.0.3/master)

This is an update of [Alexander Perlis' script](https://github.com/muttmua/mutt/blob/master/contrib/mutt_oauth2.py)
and conversion to a package. Instead of using GPG for token storage, this package uses Keyring.

## Installation

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
