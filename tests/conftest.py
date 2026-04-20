"""Configuration for Pytest."""
from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn
from unittest.mock import AsyncMock, Mock
import os

from click.testing import CliRunner
from mutt_oauth2.utils import SavedToken
import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

if os.getenv('_PYTEST_RAISE', '0') != '0':  # pragma no cover

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call: pytest.CallInfo[None]) -> NoReturn:
        assert call.excinfo is not None
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo: pytest.ExceptionInfo[BaseException]) -> NoReturn:
        raise excinfo.value


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_saved_token(mocker: MockerFixture) -> Mock:
    mock_token = Mock(spec=SavedToken)
    mock_token.registration = Mock()
    mock_token.refresh = AsyncMock()
    mock_token.exchange_auth_for_access = AsyncMock()
    mock_token.get_device_code = AsyncMock()
    mock_token.device_poll = AsyncMock()
    mocker.patch('mutt_oauth2.main.SavedToken.from_keyring', return_value=mock_token)
    return mock_token


@pytest.fixture
def mock_async_session(mocker: MockerFixture) -> AsyncMock:
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mocker.patch('mutt_oauth2.main.AsyncSession', return_value=mock_session)
    return mock_session
