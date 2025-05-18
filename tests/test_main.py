from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

from mutt_oauth2.main import get_handler, main
from mutt_oauth2.utils import OAuth2Error, SavedToken
from typing_extensions import Self
import pytest
import requests

if TYPE_CHECKING:
    from collections.abc import Callable

    from click.testing import CliRunner
    from pytest_mock import MockerFixture


@pytest.fixture
def mock_saved_token(mocker: MockerFixture) -> Mock:
    mock_token = Mock(spec=SavedToken)
    mock_token.registration = Mock()
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=mock_token)
    return mock_token


def test_get_handler(mocker: MockerFixture) -> None:
    send_response = mocker.patch(
        'mutt_oauth2.main.http.server.BaseHTTPRequestHandler.send_response')
    send_header = mocker.patch('mutt_oauth2.main.http.server.BaseHTTPRequestHandler.send_header')
    end_headers = mocker.patch('mutt_oauth2.main.http.server.BaseHTTPRequestHandler.end_headers')
    mocker.patch('mutt_oauth2.main.http.server.BaseHTTPRequestHandler.parse_request')
    mocker.patch('mutt_oauth2.main.http.server.BaseHTTPRequestHandler.handle_one_request')
    auth_code = None

    def set_auth_code(x: str) -> None:
        nonlocal auth_code
        auth_code = x

    handler = get_handler(set_auth_code)(mocker.MagicMock(), '', mocker.MagicMock())
    handler.path = '/?code=blah'
    handler.request_version = 'HTTP/1.1'
    handler.do_GET()  # type: ignore[attr-defined]
    send_response.assert_called_once_with(200)
    send_header.assert_called_with('Content-type', 'text/html')
    end_headers.assert_called_once()
    assert auth_code == 'blah'


def test_main_no_token_no_authorize(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    result = runner.invoke(main, ('--test',))
    assert result.exit_code == 1
    assert 'You must run this command with --authorize at least once.' in result.output


def test_main_with_token_refresh_success(runner: CliRunner, mock_saved_token: Mock,
                                         mocker: MockerFixture) -> None:
    mock_saved_token.is_access_token_valid.return_value = False
    mocker.patch.object(mock_saved_token, 'refresh')
    result = runner.invoke(main)
    assert result.exit_code == 0
    mock_saved_token.refresh.assert_called_once()


def test_main_with_token_refresh_failure(runner: CliRunner, mock_saved_token: Mock,
                                         mocker: MockerFixture) -> None:
    mock_saved_token.is_access_token_valid.return_value = False
    mocker.patch.object(mock_saved_token, 'refresh', side_effect=OAuth2Error)
    result = runner.invoke(main)
    assert result.exit_code == 1
    assert 'Caught error attempting refresh.' in result.output


def test_main_authorize_new_token_no_auth_code(runner: CliRunner, mock_saved_token: Mock,
                                               mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    mocker.patch(
        'click.prompt',
        side_effect=['google', 'test@example.com', 'client_id', 'client_secret', 'auth_code'])
    mocker.patch('mutt_oauth2.main.http.server.HTTPServer')
    mocker.patch('mutt_oauth2.main.get_localhost_redirect_uri',
                 return_value=(8080, 'http://localhost:8080/'))
    mocker.patch('mutt_oauth2.main.SavedToken.exchange_auth_for_access',
                 return_value={
                     'access_token': 'new_token',
                     'expires_in': 3600
                 })
    mocker.patch.object(SavedToken, 'persist')
    result = runner.invoke(main, ('--authorize',))
    assert result.exit_code == 1


def test_main_localhost_flow_empty(runner: CliRunner, mock_saved_token: Mock,
                                   mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    mocker.patch(
        'click.prompt',
        side_effect=['microsoft', 'test@example.com', 'client_id', 'client_secret', 'tenant'])
    mocker.patch('mutt_oauth2.main.SavedToken.get_device_code',
                 return_value={
                     'message': 'Visit this URL',
                     'device_code': 'device_code',
                     'interval': 1
                 })
    mocker.patch('mutt_oauth2.main.http.server.HTTPServer')
    mocker.patch('mutt_oauth2.main.get_localhost_redirect_uri', return_value=(8080, ''))
    mocker.patch('mutt_oauth2.main.SavedToken.device_poll',
                 return_value={
                     'access_token': 'new_token',
                     'expires_in': 3600,
                     'interval': 1
                 })
    mocker.patch.object(SavedToken, 'persist')
    result = runner.invoke(main, ('--authorize',))
    assert result.exit_code == 1
    assert 'Did not obtain an authorisation code.' in result.output


def test_main_authorize_new_token(runner: CliRunner, mock_saved_token: Mock,
                                  mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    mocker.patch(
        'click.prompt',
        side_effect=['microsoft', 'test@example.com', 'client_id', 'client_secret', 'tenant'])
    mocker.patch('mutt_oauth2.main.SavedToken.get_device_code',
                 return_value={
                     'message': 'Visit this URL',
                     'device_code': 'device_code',
                     'interval': 1
                 })

    class MockHTTPServer:
        def __init__(self, _: Any, callback: Callable[..., Any]) -> None:
            self.callback = callback

        def handle_request(self) -> None:
            self.callback('code')

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            pass

    mocker.patch('mutt_oauth2.main.get_handler', lambda x: x)
    mocker.patch('mutt_oauth2.main.http.server.HTTPServer', MockHTTPServer)
    mocker.patch('mutt_oauth2.main.get_localhost_redirect_uri', return_value=(8080, ''))
    mocker.patch('mutt_oauth2.main.SavedToken.device_poll',
                 return_value={
                     'access_token': 'new_token',
                     'expires_in': 3600,
                     'interval': 1
                 })
    mocker.patch('mutt_oauth2.main.SavedToken.exchange_auth_for_access')
    mocker.patch('mutt_oauth2.main.SavedToken.persist')
    mocker.patch('mutt_oauth2.main.SavedToken.as_json')
    result = runner.invoke(main, ('--authorize',))
    assert result.exit_code == 0


def test_main_authorize_new_token_exchange_fail(runner: CliRunner, mock_saved_token: Mock,
                                                mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    mocker.patch(
        'click.prompt',
        side_effect=['microsoft', 'test@example.com', 'client_id', 'client_secret', 'tenant'])
    mocker.patch('mutt_oauth2.main.SavedToken.get_device_code',
                 return_value={
                     'message': 'Visit this URL',
                     'device_code': 'device_code',
                     'interval': 1
                 })

    class MockHTTPServer:
        def __init__(self, _: Any, callback: Callable[..., Any]) -> None:
            self.callback = callback

        def handle_request(self) -> None:
            self.callback('code')

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            pass

    mocker.patch('mutt_oauth2.main.get_handler', lambda x: x)
    mocker.patch('mutt_oauth2.main.http.server.HTTPServer', MockHTTPServer)
    mocker.patch('mutt_oauth2.main.get_localhost_redirect_uri', return_value=(8080, ''))
    mocker.patch('mutt_oauth2.main.SavedToken.device_poll',
                 return_value={
                     'access_token': 'new_token',
                     'expires_in': 3600,
                     'interval': 1
                 })
    mocker.patch('mutt_oauth2.main.SavedToken.exchange_auth_for_access',
                 side_effect=requests.HTTPError)
    result = runner.invoke(main, ('--authorize',))
    assert result.exit_code == 1


def test_main_test_auth(runner: CliRunner, mock_saved_token: Mock, mocker: MockerFixture) -> None:
    try_auth = mocker.patch('mutt_oauth2.main.try_auth')
    result = runner.invoke(main, ('--test',))
    assert result.exit_code == 0
    try_auth.assert_called_once_with(mock_saved_token, debug=False)
