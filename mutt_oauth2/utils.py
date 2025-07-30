"""Utilities."""
from __future__ import annotations

from base64 import standard_b64encode
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
import contextlib
import imaplib
import json
import logging
import poplib
import smtplib
import socket

from typing_extensions import override
import keyring
import requests

from .constants import KEYRING_SERVICE_NAME
from .registrations import Registration

log = logging.getLogger(__name__)

__all__ = ('OAuth2Error', 'SavedToken', 'get_localhost_redirect_uri', 'log_oauth2_error',
           'try_auth')


class OAuth2Error(Exception):
    """Generic OAuth2 error."""


def log_oauth2_error(data: dict[str, Any]) -> None:
    """Log OAuth2 error information."""
    if 'error' in data:
        log.error('Error type: %s', data['error'])
        if 'error_description' in data:
            log.error('Description: %s', data['error_description'])


def build_sasl_string(registration: Registration, user: str, host: str, port: int,
                      bearer_token: str) -> str:
    if registration.sasl_method == 'OAUTHBEARER':
        return f'n,a={user},\1host={host}\1port={port}\1auth=Bearer {bearer_token}\1\1'
    if registration.sasl_method == 'XOAUTH2':
        return f'user={user}\1auth=Bearer {bearer_token}\1\1'
    raise ValueError(registration.sasl_method)


def object_hook(d: dict[str, Any]) -> Any:
    if 'access_token_expiration' in d:
        with contextlib.suppress(ValueError):
            d['access_token_expiration'] = datetime.fromtimestamp(float(
                d['access_token_expiration']),
                                                                  tz=timezone.utc)
    if 'registration' in d:
        d['registration'] = Registration(**d['registration'])
    return d


class SavedTokenEncoder(json.JSONEncoder):
    @override
    def default(self, o: Any) -> Any:
        if isinstance(o, datetime):
            return o.timestamp()
        return super().default(o)  # pragma: no cover


@dataclass
class SavedToken:
    """Data class for OAuth2 token information."""
    access_token_expiration: datetime | None
    """Access token expiration."""
    client_id: str
    """Client ID."""
    client_secret: str | None
    """Client secret, if applicable."""
    email: str
    """Email address."""
    registration: Registration
    """Registration."""
    access_token: str = ''
    """
    Access token.

    :meta hide-value:
    """
    refresh_token: str = ''
    """
    Refresh token.

    :meta hide-value:
    """
    tenant: str | None = None
    """
    Tenant ID, if applicable.

    :meta hide-value:
    """
    @staticmethod
    def from_keyring(username: str) -> SavedToken | None:
        """Create an instance using the Keyring."""
        if token_data := keyring.get_password(KEYRING_SERVICE_NAME, username):
            return SavedToken(**json.loads(token_data, object_hook=object_hook))
        return None

    def update(self, data: dict[str, Any]) -> None:
        """Update the token."""
        self.access_token = data['access_token']
        self.access_token_expiration = (datetime.now(tz=timezone.utc) +
                                        timedelta(seconds=int(data['expires_in'])))
        if 'refresh_token' in data:
            self.refresh_token = data['refresh_token']

    def persist(self, username: str) -> None:
        """Persist the token to the Keyring."""
        keyring.set_password(KEYRING_SERVICE_NAME, username, self.as_json())

    def is_access_token_valid(self) -> bool:
        """Check if the access token is valid."""
        if self.access_token_expiration:
            return datetime.now(tz=timezone.utc) < self.access_token_expiration
        return False

    def as_json(self, indent: int | None = None) -> str:
        """Convert the token to JSON."""
        return json.dumps(asdict(self),
                          allow_nan=False,
                          cls=SavedTokenEncoder,
                          indent=indent,
                          sort_keys=True)

    def refresh(self, username: str) -> None:
        """
        Refresh the access token using the refresh token.

        Raises
        ------
        OAuth2Error
        """
        if self.is_access_token_valid():  # pragma: no cover
            return
        r = requests.post(self.registration.token_endpoint,
                          data={
                              'client_id': self.client_id,
                              'grant_type': 'refresh_token',
                              'refresh_token': self.refresh_token
                          } | ({
                              'client_secret': self.client_secret
                          } if self.client_secret is not None else {}),
                          timeout=15)
        r.raise_for_status()
        if (data := r.json()) and 'error' in data:
            log_oauth2_error(data)
            raise OAuth2Error
        self.update(data)
        self.persist(username)

    def exchange_auth_for_access(self, auth_code: str, verifier: str, redirect_uri: str) -> Any:
        """
        Exchange the authorisation code for an access token.

        Raises
        ------
        OAuth2Error
        """
        log.debug('Exchanging the authorisation code for an access token.')
        r = requests.post(self.registration.token_endpoint,
                          data={
                              'client_id': self.client_id,
                              'code': auth_code,
                              'code_verifier': verifier,
                              'grant_type': 'authorization_code',
                              'redirect_uri': redirect_uri,
                              'scope': self.registration.scope
                          } | ({
                              'client_secret': self.client_secret
                          } if self.client_secret is not None else {}),
                          timeout=15)
        r.raise_for_status()
        if (data := r.json()) and 'error' in data:
            log_oauth2_error(data)
            raise OAuth2Error
        return data

    def get_device_code(self) -> Any:
        """
        Get the device code.

        Raises
        ------
        OAuth2Error
        """
        r = requests.post(self.registration.device_code_endpoint,
                          data=({
                              'client_id': self.client_id,
                              'scope': self.registration.scope
                          } | ({
                              'tenant': self.tenant
                          } if self.tenant else {})),
                          timeout=15)
        r.raise_for_status()
        if (data := r.json()) and 'error' in data:
            log_oauth2_error(data)
            raise OAuth2Error
        return data

    def device_poll(self, device_code: str) -> Any:
        """
        Poll the device code endpoint for the access token.

        Raises
        ------
        OAuth2Error
        """
        r = requests.post(self.registration.token_endpoint,
                          data={
                              'client_id': self.client_id,
                              'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                              'device_code': device_code
                          } | ({
                              'tenant': self.tenant
                          } if self.tenant else {}) | ({
                              'client_secret': self.client_secret
                          } if self.client_secret is not None else {}),
                          timeout=15)
        r.raise_for_status()
        if (data := r.json()) and 'error' in data:
            log_oauth2_error(data)
            raise OAuth2Error
        return data


def try_auth(token: SavedToken, *, debug: bool = False) -> None:
    """
    Try to authenticate using passed in token.

    Raises
    ------
    RuntimeError
    """
    errors = False
    imap_conn = imaplib.IMAP4_SSL(token.registration.imap_endpoint)
    sasl_string = build_sasl_string(token.registration, token.email,
                                    token.registration.imap_endpoint, 993, token.access_token)
    if debug:  # pragma: no cover
        imap_conn.debug = 4
    try:
        imap_conn.authenticate(
            token.registration.sasl_method,
            lambda _: sasl_string.encode(),  # pragma: no cover
        )
        # Microsoft has a bug wherein a mismatch between username and token can still report a
        # successful login... (Try a consumer login with the token from a work/school account.)
        # Fortunately subsequent commands fail with an error. Thus we follow AUTH with another
        # IMAP command before reporting success.
        imap_conn.list()
        log.info('IMAP authentication succeeded.')
    except imaplib.IMAP4.error:
        log.exception('IMAP authentication failed. Does your account allow IMAP?')
        errors = True
    pop_conn = poplib.POP3_SSL(token.registration.pop_endpoint)
    sasl_string = build_sasl_string(token.registration, token.email,
                                    token.registration.pop_endpoint, 995, token.access_token)
    if debug:  # pragma: no cover
        pop_conn.set_debuglevel(2)
    try:
        # poplib doesn't have an auth command taking an authenticator object
        # Microsoft requires a two-line SASL for POP
        pop_conn._shortcmd(  # type: ignore[attr-defined] # noqa: SLF001
            f'AUTH {token.registration.sasl_method}')
        pop_conn._shortcmd(  # type: ignore[attr-defined] # noqa: SLF001
            standard_b64encode(sasl_string.encode()).decode())
        log.info('POP authentication succeeded.')
    except poplib.error_proto:
        log.exception('POP authentication failed. Does your account allow POP?')
        errors = True
    # SMTP_SSL would be simpler but Microsoft does not answer on port 465.
    smtp_conn = smtplib.SMTP(token.registration.smtp_endpoint, 587)
    sasl_string = build_sasl_string(token.registration, token.email,
                                    token.registration.smtp_endpoint, 587, token.access_token)
    smtp_conn.ehlo('test')
    smtp_conn.starttls()
    smtp_conn.ehlo('test')
    if debug:  # pragma: no cover
        smtp_conn.set_debuglevel(2)
    try:
        smtp_conn.auth(
            token.registration.sasl_method,
            lambda _=None: sasl_string,  # pragma: no cover
        )
        log.info('SMTP authentication succeeded.')
    except smtplib.SMTPAuthenticationError:
        log.exception('SMTP authentication failed.')
        errors = True
    if errors:
        raise RuntimeError


def get_localhost_redirect_uri() -> tuple[int, str]:
    """Find an available port and return a localhost URI."""
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    listen_port = s.getsockname()[1]
    s.close()
    return listen_port, f'http://localhost:{listen_port}/'
