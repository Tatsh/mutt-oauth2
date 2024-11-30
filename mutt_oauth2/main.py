from base64 import urlsafe_b64encode
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
from .utils import OAuth2Error, SavedToken, get_localhost_redirect_uri, test_auth

__all__ = ('main',)

log = logging.getLogger(__name__)


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
        auth_flow = click.prompt('Preferred OAuth2 flow',
                                 default='auth_code',
                                 type=click.Choice(
                                     ['auth_code', 'localhostauth_code', 'devicecode']))
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
        if token.registration.tenant is not None:
            token.tenant = click.prompt('Tenant', default=token.registration.tenant)
        if auth_flow in {'auth_code', 'localhostauth_code'}:
            verifier = secrets.token_urlsafe(90)
            challenge = urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())[:-1]
            redirect_uri = token.registration.redirect_uri
            listen_port = None
            if auth_flow == 'localhostauth_code':
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
            if token.tenant:
                base_params['tenant'] = token.tenant
            click.echo(token.registration.authorize_endpoint +
                       f'?{urlencode(base_params, quote_via=urllib.parse.quote)}')
            auth_code = ''
            if auth_flow == 'auth_code':
                auth_code = click.prompt(
                    'Visit displayed URL to retrieve authorization code. Enter '
                    'code from server (might be in browser address bar)')
            else:
                click.echo('Visit displayed URL to authorize this application. Waiting...')

                class MyHandler(http.server.BaseHTTPRequestHandler):
                    def do_HEAD(self) -> None:  # noqa: N802
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()

                    def do_GET(self) -> None:  # noqa: N802
                        nonlocal auth_code
                        querydict = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                        if 'code' in querydict:
                            auth_code = querydict['code'][0]
                        self.do_HEAD()
                        self.wfile.write(b'<html><head><title>Authorisation result</title></head>'
                                         b'<body><p>Authorization redirect completed. You may '
                                         b'close this window.</p></body></html>')

                assert listen_port is not None
                with (http.server.HTTPServer(('127.0.0.1', listen_port), MyHandler) as
                      httpd, contextlib.suppress(KeyboardInterrupt)):
                    httpd.handle_request()
            if not auth_code:
                click.echo('Did not obtain an authorisation code.', err=True)
                raise click.exceptions.Exit(1)
            try:
                data = token.exchange_auth_for_access(auth_code, verifier, redirect_uri)
            except (requests.HTTPError, OAuth2Error) as e:
                raise click.Abort from e
        elif auth_flow == 'devicecode':
            try:
                data = token.get_device_code()
            except (requests.HTTPError, OAuth2Error) as e:
                raise click.Abort from e
            click.echo(data['message'])
            click.echo('Polling ...')
            code = data['device_code']
            while True:
                time.sleep(data['interval'])
                data = token.device_poll(code)
                if 'error' not in data:
                    match data['error']:
                        case 'authorization_declined':
                            click.echo('User declined authorisation.', err=True)
                        case 'expired_token':
                            click.echo('Too much time has elapsed.', err=True)
                        case 'authorization_pending':
                            click.echo(data['message'], err=True)
                            if 'error_condition' in data:
                                click.echo(data['error_condition'], err=True)
                    raise click.exceptions.Exit(1)
        else:
            raise ValueError(auth_flow)
        token.update(data)
        token.persist(username)
    try:
        token.refresh(username)
    except requests.HTTPError as e:
        click.echo('Caught error attempting refresh.', err=True)
        raise click.exceptions.Exit(1) from e
    log.debug('Token: %s', token.as_json(indent=2))
    if test:
        test_auth(token, debug=debug)
    else:
        click.echo(token.access_token)
