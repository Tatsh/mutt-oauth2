from base64 import urlsafe_b64encode
from collections.abc import Callable
from typing import Literal
from urllib.parse import urlencode
import contextlib
import getpass
import hashlib
import http
import http.server
import logging
import secrets
import time
import urllib
import urllib.parse

import click
import requests

from .registrations import registrations
from .utils import OAuth2Error, SavedToken, get_localhost_redirect_uri, try_auth

__all__ = ('main',)

log = logging.getLogger(__name__)


def get_handler(
        auth_code_callback: Callable[[str], None]) -> type[http.server.BaseHTTPRequestHandler]:
    class MyHandler(http.server.BaseHTTPRequestHandler):
        def do_HEAD(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            querydict = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if 'code' in querydict:  # pragma: no cover
                auth_code_callback(querydict['code'][0])
            self.do_HEAD()
            self.wfile.write(b'<html><head><title>Authorisation result</title></head>'
                             b'<body><p>Authorization redirect completed. You may '
                             b'close this window.</p></body></html>')

    return MyHandler


@click.command(context_settings={'help_option_names': ('-h', '--help')})
@click.option('-a', '--authorize', help='Manually authorise new tokens.', is_flag=True)
@click.option('-d', '--debug', help='Enable debug logging.', is_flag=True)
@click.option('-t', '--test', help='Test authentication.', is_flag=True)
@click.option('-u', '--username', help='Keyring username.', default=getpass.getuser())
@click.option('-v', '--verbose', help='Enable verbose logging.', is_flag=True)
def main(username: str,
         *,
         authorize: bool = False,
         debug: bool = False,
         test: bool = False,
         verbose: bool = False) -> None:
    """Obtain and print a valid OAuth2 access token."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO if verbose else logging.ERROR)
    token = SavedToken.from_keyring(username)
    if not token:
        if not authorize or test:
            click.echo('You must run this command with --authorize at least once.', err=True)
            raise click.exceptions.Exit(1)
        auth_flow: Literal['auth_code', 'localhostauth_code', 'devicecode'] = click.prompt(
            'Preferred OAuth2 flow',
            default='auth_code',
            show_choices=True,
            type=click.Choice(['auth_code', 'localhostauth_code', 'devicecode']))
        token = SavedToken(access_token_expiration=None,
                           registration=getattr(
                               registrations,
                               click.prompt('OAuth2 registration',
                                            default='google',
                                            type=click.Choice(['google', 'microsoft']))),
                           email=click.prompt('Account e-mail address'),
                           client_id=click.prompt('Client ID'),
                           client_secret=click.prompt('Client secret'))
        log.debug('Settings thus far: %s', token.as_json(indent=2))
        if token.registration.tenant is not None:  # pragma: no cover
            token.tenant = click.prompt('Tenant', default=token.registration.tenant)
        if auth_flow in {'auth_code', 'localhostauth_code'}:
            verifier = secrets.token_urlsafe(90)
            challenge = urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())[:-1]
            redirect_uri = token.registration.redirect_uri
            listen_port = None
            if auth_flow == 'localhostauth_code':  # pragma: no cover
                listen_port, redirect_uri = get_localhost_redirect_uri()
            base_params = {
                'client_id': token.client_id,
                'login_hint': token.email,
                'response_type': 'code',
                'redirect_uri': redirect_uri,
                'code_challenge': challenge,
                'code_challenge_method': 'S256',
                'scope': token.registration.scope
            }
            log.debug('Parameters: %s', base_params)
            if token.tenant:  # pragma: no cover
                base_params['tenant'] = token.tenant
            click.echo(token.registration.authorize_endpoint +
                       f'?{urlencode(base_params, quote_via=urllib.parse.quote)}')
            auth_code = ''
            if auth_flow == 'auth_code':
                auth_code = click.prompt(
                    'Visit displayed URL to retrieve authorization code. Enter '
                    'code from server (might be in browser address bar)')
            else:  # pragma: no cover
                click.echo('Visit displayed URL to authorize this application. Waiting...')
                assert listen_port is not None

                def set_auth_code(x: str) -> None:
                    nonlocal auth_code
                    auth_code = x

                with (http.server.HTTPServer(('127.0.0.1', listen_port), get_handler(set_auth_code))
                      as httpd, contextlib.suppress(KeyboardInterrupt)):
                    httpd.handle_request()
            if not auth_code:
                click.echo('Did not obtain an authorisation code.', err=True)
                raise click.exceptions.Exit(1)
            try:
                data = token.exchange_auth_for_access(auth_code, verifier, redirect_uri)
            except (OAuth2Error, requests.HTTPError) as e:  # pragma: no cover
                raise click.Abort from e
        elif auth_flow == 'devicecode':
            try:
                data = token.get_device_code()
            except (OAuth2Error, requests.HTTPError) as e:  # pragma: no cover
                raise click.Abort from e
            click.echo(data['message'])
            click.echo('Polling ...')
            code = data['device_code']
            while True:
                time.sleep(data['interval'])
                data = token.device_poll(code)
                if 'error' in data:
                    match data['error']:
                        case 'authorization_declined':
                            click.echo('User declined authorisation.', err=True)
                        case 'expired_token':
                            click.echo('Too much time has elapsed.', err=True)
                        case 'authorization_pending':
                            click.echo(data['message'], err=True)
                            if 'error_condition' in data:  # pragma: no cover
                                click.echo(data['error_condition'], err=True)
                    raise click.exceptions.Exit(1)
                break
        else:
            msg = 'Invalid auth flow.'
            raise click.BadParameter(msg, param_hint='auth_flow')
        token.update(data)
        token.persist(username)
    try:
        token.refresh(username)
    except (OAuth2Error, requests.HTTPError) as e:
        click.echo('Caught error attempting refresh.', err=True)
        raise click.exceptions.Exit(1) from e
    log.debug('Token: %s', token.as_json(indent=2))
    if test:
        try_auth(token, debug=debug)
    else:
        click.echo(token.access_token)
