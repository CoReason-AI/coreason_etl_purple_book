# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

from datetime import date

import pytest
from pydantic import ValidationError

from coreason_etl_purple_book.exceptions import DataIntegrityError
from coreason_etl_purple_book.schemas import SilverFdaPurpleBookManifest


def test_silver_manifest_valid() -> None:
    data = {
        "bla_number": "1234",
        "trade_name": "Test Brand",
        "ingredient": "Test Ingredient",
        "applicant_short": "Test Sponsor",
        "license_type": "351(a)",
        "approval_date": "2023-01-01",
        "exclusivity_end_date": "2030-01-01",
        "marketing_status": "Rx",
    }
    manifest = SilverFdaPurpleBookManifest(**data)
    assert manifest.bla_number == "001234"
    assert manifest.approval_date == date(2023, 1, 1)
    assert manifest.exclusivity_end_date == date(2030, 1, 1)


def test_silver_manifest_valid_no_exclusivity() -> None:
    data = {
        "bla_number": " 123 ",
        "trade_name": "Test Brand",
        "ingredient": "Test Ingredient",
        "applicant_short": "Test Sponsor",
        "license_type": "351(k)",
        "approval_date": "2023-01-01",
        "exclusivity_end_date": None,
        "marketing_status": "OTC",
    }
    manifest = SilverFdaPurpleBookManifest(**data)
    assert manifest.bla_number == "000123"
    assert manifest.exclusivity_end_date is None


def test_bla_number_sanitization() -> None:
    data = {
        "bla_number": "  12-34_a. ",
        "trade_name": "Test",
        "ingredient": "Test",
        "applicant_short": "Test",
        "license_type": "351(a)",
        "approval_date": "2023-01-01",
        "marketing_status": "Rx",
    }
    manifest = SilverFdaPurpleBookManifest(**data)
    # The regex re.sub(r"[^a-zA-Z0-9]", "", v) strips all non-alphanumeric, including underscore
    # 12-34_a. -> 1234a
    assert manifest.bla_number == "01234a"


def test_bla_number_sanitization_alphanumeric_only() -> None:
    data = {
        "bla_number": "BLA 123",
        "trade_name": "Test",
        "ingredient": "Test",
        "applicant_short": "Test",
        "license_type": "351(a)",
        "approval_date": "2023-01-01",
        "marketing_status": "Rx",
    }
    manifest = SilverFdaPurpleBookManifest(**data)
    assert manifest.bla_number == "BLA123"


def test_bla_number_length_validation_fails() -> None:
    data = {
        "bla_number": "1234567",
        "trade_name": "Test",
        "ingredient": "Test",
        "applicant_short": "Test",
        "license_type": "351(a)",
        "approval_date": "2023-01-01",
        "marketing_status": "Rx",
    }
    # Because DataIntegrityError is not derived from ValueError, pydantic doesn't wrap it.
    with pytest.raises(DataIntegrityError) as exc_info:
        SilverFdaPurpleBookManifest(**data)
    assert "BLA Number exceeds 6 characters after sanitization" in str(exc_info.value)


def test_bla_number_integer_input() -> None:
    data = {
        "bla_number": 123,
        "trade_name": "Test",
        "ingredient": "Test",
        "applicant_short": "Test",
        "license_type": "351(a)",
        "approval_date": "2023-01-01",
        "marketing_status": "Rx",
    }
    with pytest.raises(ValidationError) as exc_info:
        SilverFdaPurpleBookManifest(**data)
    assert "BLA Number must be a string" in str(exc_info.value)


def test_invalid_date_format() -> None:
    data = {
        "bla_number": "123",
        "trade_name": "Test",
        "ingredient": "Test",
        "applicant_short": "Test",
        "license_type": "351(a)",
        "approval_date": "not-a-date",
        "marketing_status": "Rx",
    }
    with pytest.raises(ValidationError) as exc_info:
        SilverFdaPurpleBookManifest(**data)
    assert "approval_date" in str(exc_info.value)
