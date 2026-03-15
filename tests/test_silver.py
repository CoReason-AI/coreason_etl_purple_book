# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

import uuid
from datetime import date
from unittest.mock import patch

import polars as pl

from coreason_etl_purple_book.identity import NAMESPACE_FDA_PURPLE_BOOK
from coreason_etl_purple_book.silver import process_silver_layer


def test_process_silver_layer_valid() -> None:
    mock_df = pl.DataFrame(
        {
            "source_bla_number": [" 123 ", "456"],
            "proprietary_name": ["Brand A", "Brand B"],
            "proper_name": ["Ingredient A", "Ingredient B"],
            "applicant": ["Sponsor A", "Sponsor B"],
            "license_type": ["351(a)", "351(k)"],
            "approval_date": ["2023-01-01", "2024-05-15"],
            "exclusivity_expiration": ["2030-01-01", None],
            "marketing_status": ["Rx", "OTC"],
        }
    )

    with patch("polars.read_database", return_value=mock_df) as mock_read_db:
        result_df = process_silver_layer("postgresql://user:pass@localhost:5432/db")

        mock_read_db.assert_called_once()
        assert "query" in mock_read_db.call_args.kwargs
        assert "connection" in mock_read_db.call_args.kwargs
        assert mock_read_db.call_args.kwargs["connection"] == "postgresql://user:pass@localhost:5432/db"

        assert len(result_df) == 2

        # Verify columns mapped and types converted
        assert "bla_number" in result_df.columns
        assert "source_id" in result_df.columns
        assert "coreason_id" in result_df.columns
        assert "exclusivity_end_date" in result_df.columns

        # Verify ID sanitization and generation
        assert result_df["bla_number"][0] == "000123"
        assert result_df["source_id"][0] == "000123"
        assert result_df["coreason_id"][0] == str(uuid.uuid5(NAMESPACE_FDA_PURPLE_BOOK, "000123"))

        assert result_df["bla_number"][1] == "000456"
        assert result_df["source_id"][1] == "000456"
        assert result_df["coreason_id"][1] == str(uuid.uuid5(NAMESPACE_FDA_PURPLE_BOOK, "000456"))

        # Verify date conversion
        assert result_df["approval_date"][0] == date(2023, 1, 1)
        assert result_df["approval_date"][1] == date(2024, 5, 15)
        assert result_df["exclusivity_end_date"][0] == date(2030, 1, 1)
        assert result_df["exclusivity_end_date"][1] is None


def test_process_silver_layer_mixed_valid_and_invalid() -> None:
    mock_df = pl.DataFrame(
        {
            "source_bla_number": ["123", "toolong123", "456"],
            "proprietary_name": ["Brand A", "Brand B", "Brand C"],
            "proper_name": ["Ingredient A", "Ingredient B", "Ingredient C"],
            "applicant": ["Sponsor A", "Sponsor B", "Sponsor C"],
            "license_type": ["351(a)", "351(k)", "351(a)"],
            "approval_date": ["2023-01-01", "2024-05-15", "invalid_date"],
            "exclusivity_expiration": [None, None, None],
            "marketing_status": ["Rx", "OTC", "Rx"],
        }
    )

    with patch("polars.read_database", return_value=mock_df):
        result_df = process_silver_layer("postgresql://user:pass@localhost:5432/db")

        # Only 1st row is valid
        # 2nd row has BLA too long -> DataIntegrityError
        # 3rd row has invalid date -> ValidationError
        assert len(result_df) == 1
        assert result_df["bla_number"][0] == "000123"


def test_process_silver_layer_empty() -> None:
    # Empty DB response
    mock_df = pl.DataFrame(
        {
            "source_bla_number": [],
            "proprietary_name": [],
            "proper_name": [],
            "applicant": [],
            "license_type": [],
            "approval_date": [],
            "exclusivity_expiration": [],
            "marketing_status": [],
        }
    )

    with patch("polars.read_database", return_value=mock_df):
        result_df = process_silver_layer("postgresql://user:pass@localhost:5432/db")

        assert len(result_df) == 0
        assert isinstance(result_df, pl.DataFrame)


def test_process_silver_layer_all_invalid() -> None:
    # DB response with all invalid data
    mock_df = pl.DataFrame(
        {
            "source_bla_number": ["toolongbla", "anotherlongbla"],
            "proprietary_name": ["A", "B"],
            "proper_name": ["A", "B"],
            "applicant": ["A", "B"],
            "license_type": ["A", "B"],
            "approval_date": ["2023-01-01", "2023-01-01"],
            "exclusivity_expiration": [None, None],
            "marketing_status": ["Rx", "OTC"],
        }
    )

    with patch("polars.read_database", return_value=mock_df):
        result_df = process_silver_layer("postgresql://user:pass@localhost:5432/db")

        assert len(result_df) == 0
        assert isinstance(result_df, pl.DataFrame)
