from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
import json
import poplib

from mutt_oauth2.registrations import Registration
from mutt_oauth2.utils import (
    OAuth2Error,
    SavedToken,
    build_sasl_string,
    get_localhost_redirect_uri,
    log_oauth2_error,
    object_hook,
    try_auth,
)
import aiosmtplib
import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_log_oauth2_error(mocker: MockerFixture) -> None:
    mock_logger = mocker.patch('mutt_oauth2.utils.log')
    error_data = {'error': 'invalid_request', 'error_description': 'Invalid request parameters'}
    log_oauth2_error(error_data)
    mock_logger.error.assert_any_call('Error type: %s', 'invalid_request')
    mock_logger.error.assert_any_call('Description: %s', 'Invalid request parameters')


def test_log_oauth2_error_nothing(mocker: MockerFixture) -> None:
    mock_logger = mocker.patch('mutt_oauth2.utils.log')
    log_oauth2_error({})
    assert not mock_logger.error.called

    log_oauth2_error({'error': 'invalid_request'})
    assert mock_logger.error.call_count == 1


def test_build_sasl_string_oauthbearer() -> None:
    registration = Registration(sasl_method='OAUTHBEARER',
                                authorize_endpoint='http://example.com/authorize',
                                device_code_endpoint='http://example.com/device',
                                token_endpoint='http://example.com/token',
                                redirect_uri='http://localhost',
                                imap_endpoint='imap.example.com',
                                pop_endpoint='pop.example.com',
                                smtp_endpoint='smtp.example.com',
                                scope='email')
    result = build_sasl_string(registration, 'user', 'host', 993, 'token')
    assert result == 'n,a=user,\1host=host\1port=993\1auth=Bearer token\1\1'


def test_build_sasl_string_xoauth2() -> None:
    registration = Registration(sasl_method='XOAUTH2',
                                authorize_endpoint='http://example.com/authorize',
                                device_code_endpoint='http://example.com/device',
                                token_endpoint='http://example.com/token',
                                redirect_uri='http://localhost',
                                imap_endpoint='imap.example.com',
                                pop_endpoint='pop.example.com',
                                smtp_endpoint='smtp.example.com',
                                scope='email')
    result = build_sasl_string(registration, 'user', 'host', 993, 'token')
    assert result == 'user=user\1auth=Bearer token\1\1'


def test_build_sasl_string_invalid_method() -> None:
    registration = Registration(sasl_method='INVALID',
                                authorize_endpoint='http://example.com/authorize',
                                device_code_endpoint='http://example.com/device',
                                token_endpoint='http://example.com/token',
                                redirect_uri='http://localhost',
                                imap_endpoint='imap.example.com',
                                pop_endpoint='pop.example.com',
                                smtp_endpoint='smtp.example.com',
                                scope='email')
    with pytest.raises(ValueError, match='INVALID'):
        build_sasl_string(registration, 'user', 'host', 993, 'token')


def test_object_hook_with_access_token_expiration() -> None:
    data = {'access_token_expiration': '1699999999'}
    result = object_hook(data)
    assert isinstance(result['access_token_expiration'], datetime)


def test_object_hook_with_registration(mocker: MockerFixture) -> None:
    mock_registration = mocker.patch('mutt_oauth2.utils.Registration')
    data = {'registration': {'key': 'value'}}
    result = object_hook(data)
    mock_registration.assert_called_once_with(key='value')
    assert 'registration' in result


def test_saved_token_from_keyring(mocker: MockerFixture) -> None:
    mock_keyring = mocker.patch('mutt_oauth2.utils.keyring.get_password',
                                return_value=json.dumps({
                                    'access_token': 'token',
                                    'access_token_expiration': '1699999999',
                                    'registration': {
                                        'key': 'value'
                                    },
                                    'client_id': 'client_id',
                                    'client_secret': 'client_secret',
                                    'email': 'fake@email.com'
                                }))
    mocker.patch('mutt_oauth2.utils.object_hook', side_effect=lambda x: x)
    token = SavedToken.from_keyring('username')
    mock_keyring.assert_called_once_with('tatsh-mutt-oauth2', 'username')
    assert token is not None
    assert token.access_token == 'token'


def test_saved_token_from_keyring_none(mocker: MockerFixture) -> None:
    mock_keyring = mocker.patch('mutt_oauth2.utils.keyring.get_password', return_value=None)
    token = SavedToken.from_keyring('username')
    mock_keyring.assert_called_once_with('tatsh-mutt-oauth2', 'username')
    assert token is None


def test_saved_token_update() -> None:
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=MagicMock())
    data = {'access_token': 'new_token', 'expires_in': 3600, 'refresh_token': 'refresh_token'}
    token.update(data)
    assert token.access_token == 'new_token'
    assert token.access_token_expiration is not None
    assert token.access_token_expiration > datetime.now(tz=timezone.utc)


def test_saved_token_persist(mocker: MockerFixture) -> None:
    mock_keyring = mocker.patch('mutt_oauth2.utils.keyring.set_password')
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    token.persist('username')
    mock_keyring.assert_called_once()


def test_saved_token_is_access_token_valid() -> None:
    token = SavedToken(
        access_token_expiration=datetime.now(tz=timezone.utc) + timedelta(seconds=3600),
        client_id='client_id',
        client_secret='client_secret',
        email='email',
        registration=Registration(sasl_method='XOAUTH2',
                                  authorize_endpoint='http://example.com/authorize',
                                  device_code_endpoint='http://example.com/device',
                                  token_endpoint='http://example.com/token',
                                  redirect_uri='http://localhost',
                                  imap_endpoint='imap.example.com',
                                  pop_endpoint='pop.example.com',
                                  smtp_endpoint='smtp.example.com',
                                  scope='email'))
    assert token.is_access_token_valid()


async def test_saved_token_refresh(mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.utils.keyring.set_password')
    mock_response = MagicMock(json=lambda: {'access_token': 'new_token', 'expires_in': 3600})
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    await token.refresh('username', mock_session)
    mock_session.post.assert_called_once()


async def test_saved_token_refresh_raises_oauth2error_when_response_has_error_key(
        mocker: MockerFixture) -> None:
    mock_response = MagicMock(json=lambda: {'error': 'invalid_grant'})
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    with pytest.raises(OAuth2Error):
        await token.refresh('username', mock_session)


async def test_saved_token_exchange_auth_for_access(mocker: MockerFixture) -> None:
    mock_response = MagicMock(json=lambda: {'access_token': 'new_token', 'expires_in': 3600})
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    await token.exchange_auth_for_access('auth_code', 'verifier', 'redirect_uri', mock_session)
    mock_session.post.assert_called_once()


async def test_saved_token_exchange_auth_for_access_raises_oauth2error_when_response_has_error_key(
        mocker: MockerFixture) -> None:
    mock_response = MagicMock(json=lambda: {'error': 'invalid_grant'})
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    with pytest.raises(OAuth2Error):
        await token.exchange_auth_for_access('auth_code', 'verifier', 'redirect_uri', mock_session)


async def test_saved_token_get_device_code(mocker: MockerFixture) -> None:
    mock_response = MagicMock(
        json=lambda: {
            'device_code': 'device_code',
            'user_code': 'user_code',
            'verification_uri': 'http://example.com/verify'
        })
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    await token.get_device_code(mock_session)
    mock_session.post.assert_called_once()


async def test_saved_token_get_device_code_raises_oauth2error_when_response_has_error_key(
        mocker: MockerFixture) -> None:
    mock_response = MagicMock(json=lambda: {'error': 'invalid_grant'})
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    with pytest.raises(OAuth2Error):
        await token.get_device_code(mock_session)


async def test_saved_token_device_poll(mocker: MockerFixture) -> None:
    mock_response = MagicMock(json=lambda: {'access_token': 'new_token', 'expires_in': 3600})
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    await token.device_poll('device_code', mock_session)
    mock_session.post.assert_called_once()


async def test_saved_token_device_poll_raises_oauth2error_when_response_has_error_key(
        mocker: MockerFixture) -> None:
    mock_response = MagicMock(json=lambda: {'error': 'invalid_grant'})
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    with pytest.raises(OAuth2Error):
        await token.device_poll('device_code', mock_session)


async def test_try_auth(mocker: MockerFixture) -> None:
    mock_imap = mocker.patch('mutt_oauth2.utils.aioimaplib.IMAP4_SSL')
    mock_imap_instance = MagicMock()
    mock_imap_instance.wait_hello_from_server = AsyncMock()
    mock_imap_instance.protocol = MagicMock()
    mock_imap_instance.protocol.execute = AsyncMock(return_value=MagicMock(result='OK'))
    mock_imap_instance.protocol.new_tag.return_value = 'A001'
    mock_imap_instance.timeout = 10.0
    mock_imap_instance.list = AsyncMock()
    mock_imap.return_value = mock_imap_instance
    mock_pop = mocker.patch('mutt_oauth2.utils.poplib.POP3_SSL')
    mock_smtp = mocker.patch('mutt_oauth2.utils.aiosmtplib.SMTP')
    mock_smtp_instance = AsyncMock()
    mock_smtp_instance.execute_command = AsyncMock(return_value=MagicMock(code=235))
    mock_smtp.return_value = mock_smtp_instance
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    await try_auth(token)
    mock_imap.assert_called_once_with('imap.example.com')
    mock_pop.assert_called_once_with('pop.example.com')
    mock_smtp.assert_called_once_with(hostname='smtp.example.com', port=587)


async def test_try_auth_raises_runtime_error_on_imap_auth(mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.utils.poplib.POP3_SSL')
    mock_smtp = mocker.patch('mutt_oauth2.utils.aiosmtplib.SMTP')
    mock_smtp_instance = AsyncMock()
    mock_smtp_instance.execute_command = AsyncMock(return_value=MagicMock(code=235))
    mock_smtp.return_value = mock_smtp_instance
    mock_imap = mocker.patch('mutt_oauth2.utils.aioimaplib.IMAP4_SSL')
    mock_imap_instance = MagicMock()
    mock_imap_instance.wait_hello_from_server = AsyncMock()
    mock_imap_instance.protocol = MagicMock()
    mock_imap_instance.protocol.execute = AsyncMock(
        return_value=MagicMock(result='NO', lines=['Authentication failed']))
    mock_imap_instance.protocol.new_tag.return_value = 'A001'
    mock_imap_instance.timeout = 10.0
    mock_imap.return_value = mock_imap_instance
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    with pytest.raises(RuntimeError, match=r'.*'):
        await try_auth(token)


async def test_try_auth_raises_runtime_error_on_pop_auth(mocker: MockerFixture) -> None:
    mock_imap = mocker.patch('mutt_oauth2.utils.aioimaplib.IMAP4_SSL')
    mock_imap_instance = MagicMock()
    mock_imap_instance.wait_hello_from_server = AsyncMock()
    mock_imap_instance.protocol = MagicMock()
    mock_imap_instance.protocol.execute = AsyncMock(return_value=MagicMock(result='OK'))
    mock_imap_instance.protocol.new_tag.return_value = 'A001'
    mock_imap_instance.timeout = 10.0
    mock_imap_instance.list = AsyncMock()
    mock_imap.return_value = mock_imap_instance
    mock_smtp = mocker.patch('mutt_oauth2.utils.aiosmtplib.SMTP')
    mock_smtp_instance = AsyncMock()
    mock_smtp_instance.execute_command = AsyncMock(return_value=MagicMock(code=235))
    mock_smtp.return_value = mock_smtp_instance
    mock_pop = mocker.patch('mutt_oauth2.utils.poplib.POP3_SSL')
    mock_pop.return_value._shortcmd.side_effect = poplib.error_proto(  # noqa: SLF001
        'Authentication failed')
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    with pytest.raises(RuntimeError, match=r'.*'):
        await try_auth(token)


async def test_try_auth_raises_runtime_error_on_smtp_auth(mocker: MockerFixture) -> None:
    mock_imap = mocker.patch('mutt_oauth2.utils.aioimaplib.IMAP4_SSL')
    mock_imap_instance = MagicMock()
    mock_imap_instance.wait_hello_from_server = AsyncMock()
    mock_imap_instance.protocol = MagicMock()
    mock_imap_instance.protocol.execute = AsyncMock(return_value=MagicMock(result='OK'))
    mock_imap_instance.protocol.new_tag.return_value = 'A001'
    mock_imap_instance.timeout = 10.0
    mock_imap_instance.list = AsyncMock()
    mock_imap.return_value = mock_imap_instance
    mocker.patch('mutt_oauth2.utils.poplib.POP3_SSL')
    mock_smtp = mocker.patch('mutt_oauth2.utils.aiosmtplib.SMTP')
    mock_smtp_instance = AsyncMock()
    mock_smtp_instance.execute_command = AsyncMock(
        side_effect=aiosmtplib.SMTPAuthenticationError(535, 'Authentication failed'))
    mock_smtp.return_value = mock_smtp_instance
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    with pytest.raises(RuntimeError, match=r'.*'):
        await try_auth(token)


async def test_try_auth_raises_runtime_error_on_smtp_bad_response_code(
        mocker: MockerFixture) -> None:
    mock_imap = mocker.patch('mutt_oauth2.utils.aioimaplib.IMAP4_SSL')
    mock_imap_instance = MagicMock()
    mock_imap_instance.wait_hello_from_server = AsyncMock()
    mock_imap_instance.protocol = MagicMock()
    mock_imap_instance.protocol.execute = AsyncMock(return_value=MagicMock(result='OK'))
    mock_imap_instance.protocol.new_tag.return_value = 'A001'
    mock_imap_instance.timeout = 10.0
    mock_imap_instance.list = AsyncMock()
    mock_imap.return_value = mock_imap_instance
    mocker.patch('mutt_oauth2.utils.poplib.POP3_SSL')
    mock_smtp = mocker.patch('mutt_oauth2.utils.aiosmtplib.SMTP')
    mock_smtp_instance = AsyncMock()
    mock_smtp_instance.execute_command = AsyncMock(
        return_value=MagicMock(code=535, message='Authentication failed'))
    mock_smtp.return_value = mock_smtp_instance
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 redirect_uri='http://localhost',
                                                 scope='email',
                                                 smtp_endpoint='smtp.example.com',
                                                 token_endpoint='http://example.com/token'))
    with pytest.raises(RuntimeError, match=r'.*'):
        await try_auth(token)


def test_object_hook_with_invalid_access_token_expiration() -> None:
    data = {'access_token_expiration': 'not-a-number'}
    result = object_hook(data)
    assert result['access_token_expiration'] == 'not-a-number'


def test_saved_token_update_without_refresh_token() -> None:
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=MagicMock())
    data = {'access_token': 'new_token', 'expires_in': 3600}
    token.update(data)
    assert token.access_token == 'new_token'
    assert not token.refresh_token


def test_saved_token_is_access_token_valid_none_expiration() -> None:
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=MagicMock())
    assert not token.is_access_token_valid()


def test_saved_token_is_access_token_expired() -> None:
    token = SavedToken(
        access_token_expiration=datetime.now(tz=timezone.utc) - timedelta(seconds=3600),
        client_id='client_id',
        client_secret='client_secret',
        email='email',
        registration=MagicMock())
    assert not token.is_access_token_valid()


def test_saved_token_as_json() -> None:
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    result = json.loads(token.as_json(indent=2))
    assert result['client_id'] == 'client_id'
    assert result['email'] == 'email'


async def test_saved_token_refresh_without_client_secret(mocker: MockerFixture) -> None:
    mocker.patch('mutt_oauth2.utils.keyring.set_password')
    mock_response = MagicMock(json=lambda: {'access_token': 'new_token', 'expires_in': 3600})
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret=None,
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    await token.refresh('username', mock_session)
    call_kwargs = mock_session.post.call_args
    assert 'client_secret' not in call_kwargs.kwargs['data']


async def test_saved_token_exchange_auth_without_client_secret(mocker: MockerFixture) -> None:
    mock_response = MagicMock(json=lambda: {'access_token': 'new_token', 'expires_in': 3600})
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret=None,
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    await token.exchange_auth_for_access('auth_code', 'verifier', 'redirect_uri', mock_session)
    call_kwargs = mock_session.post.call_args
    assert 'client_secret' not in call_kwargs.kwargs['data']


async def test_saved_token_get_device_code_with_tenant(mocker: MockerFixture) -> None:
    mock_response = MagicMock(
        json=lambda: {
            'device_code': 'device_code',
            'user_code': 'user_code',
            'verification_uri': 'http://example.com/verify'
        })
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'),
                       tenant='common')
    await token.get_device_code(mock_session)
    call_kwargs = mock_session.post.call_args
    assert call_kwargs.kwargs['data']['tenant'] == 'common'


async def test_saved_token_device_poll_with_tenant(mocker: MockerFixture) -> None:
    mock_response = MagicMock(json=lambda: {'access_token': 'new_token', 'expires_in': 3600})
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret='client_secret',
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'),
                       tenant='common')
    await token.device_poll('device_code', mock_session)
    call_kwargs = mock_session.post.call_args
    assert call_kwargs.kwargs['data']['tenant'] == 'common'


async def test_saved_token_device_poll_without_client_secret(mocker: MockerFixture) -> None:
    mock_response = MagicMock(json=lambda: {'access_token': 'new_token', 'expires_in': 3600})
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_response)
    token = SavedToken(access_token_expiration=None,
                       client_id='client_id',
                       client_secret=None,
                       email='email',
                       registration=Registration(sasl_method='XOAUTH2',
                                                 authorize_endpoint='http://example.com/authorize',
                                                 device_code_endpoint='http://example.com/device',
                                                 token_endpoint='http://example.com/token',
                                                 redirect_uri='http://localhost',
                                                 imap_endpoint='imap.example.com',
                                                 pop_endpoint='pop.example.com',
                                                 smtp_endpoint='smtp.example.com',
                                                 scope='email'))
    await token.device_poll('device_code', mock_session)
    call_kwargs = mock_session.post.call_args
    assert 'client_secret' not in call_kwargs.kwargs['data']


def test_get_localhost_redirect_uri() -> None:
    port, uri = get_localhost_redirect_uri()
    assert isinstance(port, int)
    assert uri.startswith('http://localhost:')
