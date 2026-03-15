# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

import hashlib
import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from coreason_etl_purple_book.source import FdaPurpleBookSource


def test_download_and_hash_csv_success() -> None:
    source = FdaPurpleBookSource()
    test_url = "http://fake.url/data.csv"
    test_data = b"col1,col2\nval1,val2\n"

    expected_hash = hashlib.md5(test_data).hexdigest()  # noqa: S324

    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.raise_for_status.return_value = None
    mock_response.iter_content.return_value = [test_data[:5], test_data[5:]]

    with patch("dlt.sources.helpers.requests.get", return_value=mock_response):
        file_path, md5_digest = source.download_and_hash_csv(test_url)

    assert md5_digest == expected_hash
    assert os.path.exists(file_path)

    with open(file_path, "rb") as f:
        file_content = f.read()
    assert file_content == test_data

    # Cleanup
    os.remove(file_path)


def test_download_and_hash_csv_failure() -> None:
    source = FdaPurpleBookSource()
    test_url = "http://fake.url/data.csv"

    with (
        patch("dlt.sources.helpers.requests.get", side_effect=requests.exceptions.RequestException("Failed to fetch")),
        pytest.raises(requests.exceptions.RequestException),
    ):
        source.download_and_hash_csv(test_url)

    # In case of failure, no temporary file should be leaked
    # However, since mkstemp runs before the exception, we mock it to verify the exception doesn't leak it.
    mock_fd = MagicMock()
    mock_path = "some_fake_path.csv"
    with (
        patch("tempfile.mkstemp", return_value=(mock_fd, mock_path)),
        patch("os.fdopen", MagicMock()),
        patch("dlt.sources.helpers.requests.get", side_effect=requests.exceptions.RequestException("Failed")),
        patch("os.path.exists", return_value=True),
        patch("os.remove") as mock_remove,
        pytest.raises(requests.exceptions.RequestException),
    ):
        source.download_and_hash_csv(test_url)

    mock_remove.assert_called_once_with(mock_path)
