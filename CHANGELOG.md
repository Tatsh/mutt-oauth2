<!-- markdownlint-disable MD024 -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.1/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

## [0.2.1] - 2026-07-08

### Added

- `--logout` flag to clear the stored token from the keyring. An error is reported if no stored
  credential exists or deletion fails.

### Changed

- `--authorize` now re-authorises even when a token is already stored.

### Fixed

- `invalid_grant` errors raised during token refresh are now reported instead of being ignored.
- OAuth2 error payloads returned during the authorisation code token exchange are now reported
  instead of a generic HTTP status error.
- Exit with an error when no token is available instead of continuing.

## [0.2.0] - 2026-04-26

### Added

- `anyio` dependency for thread bridging (POP3 still uses synchronous `poplib` via
  `anyio.to_thread`).

### Changed

- Migrated HTTP calls from synchronous `requests` to async `niquests`.
- Migrated IMAP and SMTP auth testing from `imaplib`/`smtplib` to `aioimaplib`/`aiosmtplib`.
- Core token operations (refresh, exchange, device code, device poll) are now async internally.
- `--test` auth verification runs IMAP, POP, and SMTP checks concurrently.

### Removed

- `requests` dependency.

## [0.1.2]

### Added

- Attestation.

### Removed

- `--verbose`/`-v` parameter removed.

## [0.1.1]

### Added

- Support secretless tokens. Thanks to @tharvik.

## [0.1.0]

### Removed

- Copy and paste code authorisation
- Device code authorisation

## [0.0.3]

### Added

- Added documentation to library code
- Added content to `index.rst` based on README
- Man page

[unreleased]: https://github.com/Tatsh/mutt-oauth2/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/Tatsh/mutt-oauth2/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Tatsh/mutt-oauth2/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/Tatsh/mutt-oauth2/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/Tatsh/mutt-oauth2/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Tatsh/mutt-oauth2/compare/v0.0.3...v0.1.0
[0.0.3]: https://github.com/Tatsh/mutt-oauth2/compare/v0.0.2...v0.0.3
