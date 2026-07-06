# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

import re
from datetime import date, datetime
from typing import Any
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from coreason_etl_purple_book.schemas import SilverFdaPurpleBookManifest


def test_silver_manifest_valid() -> None:
    data: dict[str, Any] = {
        "bla_number": "1234",
        "proprietary_name": "Test Brand",
        "proper_name": "Test Ingredient",
        "applicant": "Test Sponsor",
        "license_type": "351(a)",
        "approval_date": "2023-01-01",
        "exclusivity_expiration": "2030-01-01",
        "marketing_status": "Rx",
    }
    manifest = SilverFdaPurpleBookManifest(**data)
    assert manifest.bla_number == "001234"
    assert manifest.approval_date == date(2023, 1, 1)
    assert manifest.exclusivity_expiration == date(2030, 1, 1)


def test_date_parsing_formats() -> None:
    base_data: dict[str, Any] = {
        "bla_number": "1234",
        "proprietary_name": "Test",
        "proper_name": "Test",
        "applicant": "Test",
        "license_type": "351(a)",
        "marketing_status": "Rx",
    }

    # MM/DD/YYYY
    manifest1 = SilverFdaPurpleBookManifest(**{**base_data, "approval_date": "02/28/2024"})
    assert manifest1.approval_date == date(2024, 2, 28)

    # Month DD, YYYY
    manifest2 = SilverFdaPurpleBookManifest(**{**base_data, "approval_date": "February 28, 2024"})
    assert manifest2.approval_date == date(2024, 2, 28)

    # Mon DD, YYYY
    manifest3 = SilverFdaPurpleBookManifest(**{**base_data, "approval_date": "Feb 28, 2024"})
    assert manifest3.approval_date == date(2024, 2, 28)

    # Datetime object
    manifest4 = SilverFdaPurpleBookManifest(**{**base_data, "approval_date": datetime(2024, 2, 28)})
    assert manifest4.approval_date == date(2024, 2, 28)

    # Date object
    manifest5 = SilverFdaPurpleBookManifest(**{**base_data, "approval_date": date(2024, 2, 28)})
    assert manifest5.approval_date == date(2024, 2, 28)

    # Empty string tests
    manifest6 = SilverFdaPurpleBookManifest(
        **{**base_data, "approval_date": "2024-02-28", "exclusivity_expiration": "   "}
    )
    assert manifest6.exclusivity_expiration is None

    # Integer instead of string/date/datetime
    with pytest.raises(ValidationError) as exc_info:
        SilverFdaPurpleBookManifest(**{**base_data, "approval_date": 20240228})
    assert "Expected a string, date, or datetime" in str(exc_info.value)

    # Invalid string format
    with pytest.raises(ValidationError) as exc_info:
        SilverFdaPurpleBookManifest(**{**base_data, "approval_date": "invalid-random-string"})
    assert "Unrecognized date format" in str(exc_info.value)

    # empty string exclusivity_expiration
    manifest7 = SilverFdaPurpleBookManifest(
        **{**base_data, "approval_date": "2024-02-28", "exclusivity_expiration": ""}
    )
    assert manifest7.exclusivity_expiration is None

    # Note: dateutil.parser parses "28/02/2024" as year 2024, day 2, month 28 (ValueError: month must be in 1..12).
    with pytest.raises(ValidationError) as exc_info:
        SilverFdaPurpleBookManifest(
            **{**base_data, "approval_date": "2024-02-28", "exclusivity_expiration": "invalid-random-string"}
        )
    assert "Unrecognized date format" in str(exc_info.value)

    # integer exclusivity_expiration
    with pytest.raises(ValidationError) as exc_info:
        SilverFdaPurpleBookManifest(**{**base_data, "approval_date": "2024-02-28", "exclusivity_expiration": 20240228})
    assert "Expected a string, date, or datetime" in str(exc_info.value)

    # valid datetime object exclusivity_expiration
    manifest8 = SilverFdaPurpleBookManifest(
        **{**base_data, "approval_date": "2024-02-28", "exclusivity_expiration": datetime(2024, 2, 28)}
    )
    assert manifest8.exclusivity_expiration == date(2024, 2, 28)

    # valid date object exclusivity_expiration
    manifest10 = SilverFdaPurpleBookManifest(
        **{**base_data, "approval_date": "2024-02-28", "exclusivity_expiration": date(2024, 2, 28)}
    )
    assert manifest10.exclusivity_expiration == date(2024, 2, 28)

    # None exclusivity_expiration
    manifest9 = SilverFdaPurpleBookManifest(
        **{**base_data, "approval_date": "2024-02-28", "exclusivity_expiration": None}
    )
    assert manifest9.exclusivity_expiration is None

    # None approval_date
    manifest_none_approval = SilverFdaPurpleBookManifest(**{**base_data, "approval_date": None})
    assert manifest_none_approval.approval_date is None

    # empty space approval_date
    manifest_space_approval = SilverFdaPurpleBookManifest(**{**base_data, "approval_date": "   "})
    assert manifest_space_approval.approval_date is None


def test_silver_manifest_valid_no_exclusivity() -> None:
    data: dict[str, Any] = {
        "bla_number": " 123 ",
        "proprietary_name": "Test Brand",
        "proper_name": "Test Ingredient",
        "applicant": "Test Sponsor",
        "license_type": "351(k)",
        "approval_date": "2023-01-01",
        "exclusivity_expiration": None,
        "marketing_status": "OTC",
    }
    manifest = SilverFdaPurpleBookManifest(**data)
    assert manifest.bla_number == "000123"
    assert manifest.exclusivity_expiration is None


def test_bla_number_sanitization() -> None:
    data: dict[str, Any] = {
        "bla_number": "  12-34_a. ",
        "proprietary_name": "Test",
        "proper_name": "Test",
        "applicant": "Test",
        "license_type": "351(a)",
        "approval_date": "2023-01-01",
        "marketing_status": "Rx",
    }
    manifest = SilverFdaPurpleBookManifest(**data)
    # The regex re.sub(r"[^a-zA-Z0-9]", "", v) strips all non-alphanumeric, including underscore
    # 12-34_a. -> 1234a
    assert manifest.bla_number == "01234a"


def test_bla_number_sanitization_alphanumeric_only() -> None:
    data: dict[str, Any] = {
        "bla_number": "BLA 123",
        "proprietary_name": "Test",
        "proper_name": "Test",
        "applicant": "Test",
        "license_type": "351(a)",
        "approval_date": "2023-01-01",
        "marketing_status": "Rx",
    }
    manifest = SilverFdaPurpleBookManifest(**data)
    assert manifest.bla_number == "BLA123"


def test_bla_number_length_validation_logs_warning() -> None:
    data: dict[str, Any] = {
        "bla_number": "1234567",
        "proprietary_name": "Test",
        "proper_name": "Test",
        "applicant": "Test",
        "license_type": "351(a)",
        "approval_date": "2023-01-01",
        "marketing_status": "Rx",
    }
    with patch("coreason_etl_purple_book.schemas.logger.warning") as mock_warning:
        manifest = SilverFdaPurpleBookManifest(**data)

    mock_warning.assert_called_once_with("BLA Number exceeds 6 characters after sanitization: '1234567'")
    assert manifest.bla_number == "1234567"


def test_bla_number_integer_input() -> None:
    data: dict[str, Any] = {
        "bla_number": 123,
        "proprietary_name": "Test",
        "proper_name": "Test",
        "applicant": "Test",
        "license_type": "351(a)",
        "approval_date": "2023-01-01",
        "marketing_status": "Rx",
    }
    with pytest.raises(ValidationError) as exc_info:
        SilverFdaPurpleBookManifest(**data)
    assert "BLA Number must be a string" in str(exc_info.value)


def test_invalid_date_format() -> None:
    data: dict[str, Any] = {
        "bla_number": "123",
        "proprietary_name": "Test",
        "proper_name": "Test",
        "applicant": "Test",
        "license_type": "351(a)",
        "approval_date": "not-a-date",
        "marketing_status": "Rx",
    }
    with pytest.raises(ValidationError) as exc_info:
        SilverFdaPurpleBookManifest(**data)
    assert "approval_date" in str(exc_info.value)


@given(bla_number=st.text(alphabet=st.characters(categories=["Lu", "Ll", "N" + "d"]), min_size=1, max_size=100))  # type: ignore[untyped-decorator, unused-ignore, list-item]
def test_silver_manifest_hypothesis_valid_strings(bla_number: str) -> None:
    data: dict[str, Any] = {
        "bla_number": bla_number,
        "proprietary_name": "Test Brand",
        "proper_name": "Test Ingredient",
        "applicant": "Test Sponsor",
        "license_type": "351(a)",
        "approval_date": "2023-01-01",
        "marketing_status": "Rx",
    }

    sanitized = re.sub(r"[^a-zA-Z0-9]", "", bla_number).strip()

    with patch("coreason_etl_purple_book.schemas.logger.warning") as mock_warning:
        manifest = SilverFdaPurpleBookManifest(**data)

    if len(sanitized) > 6:
        mock_warning.assert_called_once_with(f"BLA Number exceeds 6 characters after sanitization: '{sanitized}'")
        assert manifest.bla_number == sanitized
    else:
        assert len(manifest.bla_number) == 6
        assert manifest.bla_number == sanitized.zfill(6)
