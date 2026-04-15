import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_db_session():
    """Mock async database session for unit tests."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_vnstock():
    """Mock vnstock Vnstock class for unit tests."""
    mock = MagicMock()
    mock_stock = MagicMock()
    mock.stock.return_value = mock_stock
    return mock, mock_stock
