"""Utilities."""
from __future__ import annotations

from base64 import standard_b64encode
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Protocol, cast
import asyncio
import contextlib
import json
import logging
import poplib
import socket

from anyio.to_thread import run_sync
from typing_extensions import override
import aioimaplib  # type: ignore[import-untyped]
import aiosmtplib
import keyring

from .constants import KEYRING_SERVICE_NAME
from .registrations import Registration

if TYPE_CHECKING:
    from niquests import AsyncSession

log = logging.getLogger(__name__)


class _Pop3Shortcmd(Protocol):
    def _shortcmd(self, line: str) -> bytes:
        ...


__all__ = ('OAuth2Error', 'SavedToken', 'get_localhost_redirect_uri', 'log_oauth2_error',
           'try_auth')


class OAuth2Error(Exception):
    """Generic OAuth2 error."""


def log_oauth2_error(data: dict[str, Any]) -> None:
    """
    Log OAuth2 error information.

    Parameters
    ----------
    data : dict[str, Any]
        Token response containing potential error fields.
    """
    if 'error' in data:
        log.error('Error type: %s', data['error'])
        if 'error_description' in data:
            log.error('Description: %s', data['error_description'])


def build_sasl_string(registration: Registration, user: str, host: str, port: int,
                      bearer_token: str) -> str:
    """
    Build a SASL authentication string for the given registration.

    Parameters
    ----------
    registration : ~mutt_oauth2.registrations.Registration
        Provider registration containing the SASL method.
    user : str
        Account username or email address.
    host : str
        Hostname of the mail server.
    port : int
        Port number of the mail server.
    bearer_token : str
        OAuth2 bearer token.

    Returns
    -------
    str
        The encoded SASL string.

    Raises
    ------
    ValueError
        If the SASL method is not supported.
    """
    match registration.sasl_method:
        case 'OAUTHBEARER':
            return f'n,a={user},\1host={host}\1port={port}\1auth=Bearer {bearer_token}\1\1'
        case 'XOAUTH2':
            return f'user={user}\1auth=Bearer {bearer_token}\1\1'
        case _:
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
        """
        Create an instance using the Keyring.

        Parameters
        ----------
        username : str
            Keyring username.

        Returns
        -------
        SavedToken | None
            The saved token if present, otherwise ``None``.
        """
        if token_data := keyring.get_password(KEYRING_SERVICE_NAME, username):
            return SavedToken(**json.loads(token_data, object_hook=object_hook))
        return None

    def update(self, data: dict[str, Any]) -> None:
        """
        Update the token.

        Parameters
        ----------
        data : dict[str, Any]
            Token response data from the authorisation server.
        """
        self.access_token = data['access_token']
        self.access_token_expiration = (datetime.now(tz=timezone.utc) +
                                        timedelta(seconds=int(data['expires_in'])))
        if 'refresh_token' in data:
            self.refresh_token = data['refresh_token']

    def persist(self, username: str) -> None:
        """
        Persist the token to the Keyring.

        Parameters
        ----------
        username : str
            Keyring username.
        """
        keyring.set_password(KEYRING_SERVICE_NAME, username, self.as_json())

    def is_access_token_valid(self) -> bool:
        """
        Check if the access token is valid.

        Returns
        -------
        bool
            True if the access token is still valid.
        """
        if self.access_token_expiration:
            return datetime.now(tz=timezone.utc) < self.access_token_expiration
        return False

    def as_json(self, indent: int | None = None) -> str:
        """
        Convert the token to JSON.

        Parameters
        ----------
        indent : int | None
            Indentation width for pretty-printing, or ``None`` for compact output.

        Returns
        -------
        str
            JSON representation of the token.
        """
        return json.dumps(asdict(self),
                          allow_nan=False,
                          cls=SavedTokenEncoder,
                          indent=indent,
                          sort_keys=True)

    async def refresh(self, username: str, session: AsyncSession) -> None:
        """
        Refresh the access token using the refresh token.

        Parameters
        ----------
        username : str
            Keyring username.
        session : niquests.AsyncSession
            HTTP session.

        Raises
        ------
        OAuth2Error
            If the token refresh fails.
        """
        if self.is_access_token_valid():  # pragma: no cover
            return
        r = await session.post(self.registration.token_endpoint,
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

    async def exchange_auth_for_access(self, auth_code: str, verifier: str, redirect_uri: str,
                                       session: AsyncSession) -> Any:
        """
        Exchange the authorisation code for an access token.

        Parameters
        ----------
        auth_code : str
            Authorisation code from the redirect.
        verifier : str
            PKCE code verifier.
        redirect_uri : str
            Redirect URI used in the authorisation request.
        session : niquests.AsyncSession
            HTTP session.

        Returns
        -------
        Any
            Token response data from the authorisation server.

        Raises
        ------
        OAuth2Error
            If the token exchange fails.
        """
        log.debug('Exchanging the authorisation code for an access token.')
        r = await session.post(self.registration.token_endpoint,
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

    async def get_device_code(self, session: AsyncSession) -> Any:
        """
        Get the device code.

        Parameters
        ----------
        session : niquests.AsyncSession
            HTTP session.

        Returns
        -------
        Any
            Device authorisation response from the server.

        Raises
        ------
        OAuth2Error
            If the device code request fails.
        """
        r = await session.post(self.registration.device_code_endpoint,
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

    async def device_poll(self, device_code: str, session: AsyncSession) -> Any:
        """
        Poll the device code endpoint for the access token.

        Parameters
        ----------
        device_code : str
            Device code from :py:meth:`get_device_code`.
        session : niquests.AsyncSession
            HTTP session.

        Returns
        -------
        Any
            Token response, or an error payload while authorisation is pending.

        Raises
        ------
        OAuth2Error
            If polling fails with a terminal error.
        """
        r = await session.post(self.registration.token_endpoint,
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


async def try_auth(token: SavedToken, *, debug: bool = False) -> None:
    """
    Try to authenticate using the passed-in token.

    Parameters
    ----------
    token : SavedToken
        Token to test.
    debug : bool
        Enable debug output on protocol connections.

    Raises
    ------
    RuntimeError
        If any authentication test fails.
    """
    async def _test_imap() -> bool:
        try:
            imap_conn = aioimaplib.IMAP4_SSL(token.registration.imap_endpoint)
            await imap_conn.wait_hello_from_server()
            sasl_string = build_sasl_string(token.registration, token.email,
                                            token.registration.imap_endpoint, 993,
                                            token.access_token)
            encoded = standard_b64encode(sasl_string.encode()).decode()
            protocol = imap_conn.protocol
            response = await asyncio.wait_for(
                protocol.execute(  # ty: ignore[unresolved-attribute]
                    aioimaplib.Command(
                        'AUTHENTICATE',
                        protocol.new_tag(),  # ty: ignore[unresolved-attribute]
                        token.registration.sasl_method,
                        encoded,
                        loop=protocol.loop  # ty: ignore[invalid-argument-type,unresolved-attribute]
                    )),
                imap_conn.timeout)
            if response.result != 'OK':
                msg = str(response.lines)
                raise aioimaplib.AioImapException(msg)  # noqa: TRY301
            await imap_conn.list('""', '*')  # ty: ignore[invalid-argument-type]
        except (aioimaplib.AioImapException, aioimaplib.Error):
            log.exception('IMAP authentication failed. Does your account allow IMAP?')
            return True
        else:
            log.info('IMAP authentication succeeded.')
            return False

    async def _test_pop() -> bool:
        def _sync() -> None:
            pop_conn = poplib.POP3_SSL(token.registration.pop_endpoint)
            sasl_string = build_sasl_string(token.registration, token.email,
                                            token.registration.pop_endpoint, 995,
                                            token.access_token)
            if debug:  # pragma: no cover
                pop_conn.set_debuglevel(2)
            pop_via_shortcmd = cast('_Pop3Shortcmd', pop_conn)
            pop_via_shortcmd._shortcmd(  # noqa: SLF001
                f'AUTH {token.registration.sasl_method}')
            pop_via_shortcmd._shortcmd(  # noqa: SLF001
                standard_b64encode(sasl_string.encode()).decode())

        try:
            await run_sync(_sync)
        except poplib.error_proto:
            log.exception('POP authentication failed. Does your account allow POP?')
            return True
        else:
            log.info('POP authentication succeeded.')
            return False

    async def _test_smtp() -> bool:
        try:
            smtp_conn = aiosmtplib.SMTP(hostname=token.registration.smtp_endpoint, port=587)
            await smtp_conn.connect()
            await smtp_conn.ehlo(hostname='test')
            await smtp_conn.starttls()
            await smtp_conn.ehlo(hostname='test')
            sasl_string = build_sasl_string(token.registration, token.email,
                                            token.registration.smtp_endpoint, 587,
                                            token.access_token)
            encoded = standard_b64encode(sasl_string.encode())
            response = await smtp_conn.execute_command(b'AUTH',
                                                       token.registration.sasl_method.encode(),
                                                       encoded)
            if response.code != aiosmtplib.SMTPStatus.auth_successful:
                raise aiosmtplib.SMTPAuthenticationError(  # noqa: TRY301
                    response.code, response.message)
        except aiosmtplib.SMTPAuthenticationError:
            log.exception('SMTP authentication failed.')
            return True
        else:
            log.info('SMTP authentication succeeded.')
            return False

    results = await asyncio.gather(_test_imap(), _test_pop(), _test_smtp())
    if any(results):
        raise RuntimeError


def get_localhost_redirect_uri() -> tuple[int, str]:
    """
    Find an available port and return a localhost URI.

    Returns
    -------
    tuple[int, str]
        The listening port and matching ``http://localhost:{port}/`` URI.
    """
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    listen_port = s.getsockname()[1]
    s.close()
    return listen_port, f'http://localhost:{listen_port}/'
