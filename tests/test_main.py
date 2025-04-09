from unittest.mock import Mock

from click.testing import CliRunner
from mutt_oauth2.main import get_handler, main
from mutt_oauth2.utils import OAuth2Error, SavedToken
from pytest_mock import MockerFixture
import pytest


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
    handler = get_handler('auth_code')(mocker.MagicMock(), '', mocker.MagicMock())
    handler.path = '/'
    handler.request_version = 'HTTP/1.1'
    handler.do_GET()  # type: ignore[attr-defined]
    send_response.assert_called_once_with(200)
    send_header.assert_called_with('Content-type', 'text/html')
    end_headers.assert_called_once()


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


def test_main_authorize_new_token(runner: CliRunner, mock_saved_token: Mock,
                                  mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    mocker.patch('click.prompt',
                 side_effect=[
                     'auth_code', 'google', 'test@example.com', 'client_id', 'client_secret',
                     'auth_code'
                 ])
    mocker.patch('mutt_oauth2.main.get_localhost_redirect_uri',
                 return_value=(8080, 'http://localhost:8080/'))
    mocker.patch('mutt_oauth2.main.SavedToken.exchange_auth_for_access',
                 return_value={
                     'access_token': 'new_token',
                     'expires_in': 3600
                 })
    mocker.patch.object(SavedToken, 'persist')
    result = runner.invoke(main, ('--authorize',))
    assert result.exit_code == 0
    assert 'new_token' in result.output


def test_main_device_code_flow(runner: CliRunner, mock_saved_token: Mock,
                               mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    mocker.patch(
        'click.prompt',
        side_effect=['devicecode', 'google', 'test@example.com', 'client_id', 'client_secret'])
    mocker.patch('mutt_oauth2.main.time.sleep')
    mocker.patch('mutt_oauth2.main.SavedToken.get_device_code',
                 return_value={
                     'message': 'Visit this URL',
                     'device_code': 'device_code',
                     'interval': 1
                 })
    mocker.patch('mutt_oauth2.main.SavedToken.device_poll',
                 return_value={
                     'access_token': 'new_token',
                     'expires_in': 3600,
                     'interval': 1
                 })
    mocker.patch.object(SavedToken, 'persist')
    result = runner.invoke(main, ('--authorize',))
    assert result.exit_code == 0
    assert 'new_token' in result.output


def test_main_invalid_flow(runner: CliRunner, mock_saved_token: Mock,
                           mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    mocker.patch('click.prompt',
                 side_effect=['ffff', 'google', 'test@example.com', 'client_id', 'client_secret'])
    mocker.patch.object(SavedToken, 'persist')
    result = runner.invoke(main, ('--authorize',))
    assert result.exit_code != 0


def test_main_localhost_flow_empty(runner: CliRunner, mock_saved_token: Mock,
                                   mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    mocker.patch('click.prompt',
                 side_effect=[
                     'localhostauth_code', 'google', 'test@example.com', 'client_id',
                     'client_secret'
                 ])
    mocker.patch('mutt_oauth2.main.time.sleep')
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


def test_main_device_code_flow_error(runner: CliRunner, mock_saved_token: Mock,
                                     mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    mocker.patch('mutt_oauth2.main.time.sleep')
    mocker.patch(
        'click.prompt',
        side_effect=['devicecode', 'google', 'test@example.com', 'client_id', 'client_secret'])
    mocker.patch('mutt_oauth2.main.SavedToken.get_device_code',
                 return_value={
                     'message': 'Visit this URL',
                     'device_code': 'device_code',
                     'interval': 1
                 })
    mocker.patch('mutt_oauth2.main.SavedToken.device_poll',
                 return_value={'error': 'authorization_declined'})
    result = runner.invoke(main, ('--authorize',))
    assert result.exit_code == 1
    assert 'User declined authorisation.' in result.output


def test_main_device_code_flow_expired(runner: CliRunner, mock_saved_token: Mock,
                                       mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    mocker.patch('mutt_oauth2.main.time.sleep')
    mocker.patch(
        'click.prompt',
        side_effect=['devicecode', 'google', 'test@example.com', 'client_id', 'client_secret'])
    mocker.patch('mutt_oauth2.main.SavedToken.get_device_code',
                 return_value={
                     'message': 'Visit this URL',
                     'device_code': 'device_code',
                     'interval': 1
                 })
    mocker.patch('mutt_oauth2.main.SavedToken.device_poll', return_value={'error': 'expired_token'})
    result = runner.invoke(main, ('--authorize',))
    assert result.exit_code == 1
    assert 'Too much time has elapsed.' in result.output


def test_main_device_code_flow_authorization_pending(runner: CliRunner, mock_saved_token: Mock,
                                                     mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    mocker.patch('mutt_oauth2.main.time.sleep')
    mocker.patch(
        'click.prompt',
        side_effect=['devicecode', 'google', 'test@example.com', 'client_id', 'client_secret'])
    mocker.patch('mutt_oauth2.main.SavedToken.get_device_code',
                 return_value={
                     'message': 'Visit this URL',
                     'device_code': 'device_code',
                     'interval': 1
                 })
    mocker.patch('mutt_oauth2.main.SavedToken.device_poll',
                 return_value={
                     'error': 'authorization_pending',
                     'message': 'Authorisation pending.'
                 })
    result = runner.invoke(main, ('--authorize',))
    assert result.exit_code == 1
    assert 'Authorisation pending.' in result.output


def test_main_device_code_flow_other_error(runner: CliRunner, mock_saved_token: Mock,
                                           mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=None)
    mocker.patch('mutt_oauth2.main.time.sleep')
    mocker.patch(
        'click.prompt',
        side_effect=['devicecode', 'google', 'test@example.com', 'client_id', 'client_secret'])
    mocker.patch('mutt_oauth2.main.SavedToken.get_device_code',
                 return_value={
                     'message': 'Visit this URL',
                     'device_code': 'device_code',
                     'interval': 1
                 })
    mocker.patch('mutt_oauth2.main.SavedToken.device_poll', return_value={'error': 'other'})
    result = runner.invoke(main, ('--authorize',))
    assert result.exit_code == 1


def test_main_test_auth(runner: CliRunner, mock_saved_token: Mock, mocker: MockerFixture) -> None:
    try_auth = mocker.patch('mutt_oauth2.main.try_auth')
    result = runner.invoke(main, ('--test',))
    assert result.exit_code == 0
    try_auth.assert_called_once_with(mock_saved_token, debug=False)
