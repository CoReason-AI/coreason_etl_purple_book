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
from unittest.mock import patch

import polars as pl

from coreason_etl_purple_book.identity import NAMESPACE_FDA_PURPLE_BOOK
from coreason_etl_purple_book.silver import load_silver_layer, process_silver_layer


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
        from datetime import date

        assert result_df["approval_date"][0] == date(2023, 1, 1)
        assert result_df["approval_date"][1] == date(2024, 5, 15)
        assert result_df["exclusivity_end_date"][0] == date(2030, 1, 1)
        assert result_df["exclusivity_end_date"][1] is None


def test_process_silver_layer_mixed_valid_and_invalid() -> None:
    mock_df = pl.DataFrame(
        {
            "source_bla_number": ["123", "toolong123"],
            "proprietary_name": ["Brand A", "Brand B"],
            "proper_name": ["Ingredient A", "Ingredient B"],
            "applicant": ["Sponsor A", "Sponsor B"],
            "license_type": ["351(a)", "351(k)"],
            "approval_date": ["2023-01-01", "2024-05-15"],
            "exclusivity_expiration": [None, None],
            "marketing_status": ["Rx", "OTC"],
        }
    )

    with patch("polars.read_database", return_value=mock_df):
        result_df = process_silver_layer("postgresql://user:pass@localhost:5432/db")

        # 1st row is valid
        # 2nd row has BLA too long, but now only logs a warning instead of dropping
        assert len(result_df) == 2
        assert result_df["bla_number"][0] == "000123"
        assert result_df["bla_number"][1] == "toolong123"


def test_process_silver_layer_data_integrity_error_propagation() -> None:
    mock_df = pl.DataFrame(
        {
            "source_bla_number": ["123"],
            "proprietary_name": ["Brand A"],
            "proper_name": ["Ingredient A"],
            "applicant": ["Sponsor A"],
            "license_type": ["351(a)"],
            "approval_date": ["2023-01-01"],
            "exclusivity_expiration": [None],
            "marketing_status": ["Rx"],
        }
    )

    with patch("polars.read_database", return_value=mock_df):
        from coreason_etl_purple_book.exceptions import DataIntegrityError

        with patch(
            "pydantic.TypeAdapter.validate_python",
            side_effect=DataIntegrityError("Critical Failure"),
        ):
            import pytest

            with pytest.raises(DataIntegrityError, match="Critical Failure"):
                process_silver_layer("postgresql://user:pass@localhost:5432/db")


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


def test_load_silver_layer_valid() -> None:
    mock_df = pl.DataFrame(
        {
            "bla_number": ["000123"],
            "trade_name": ["Brand A"],
            "ingredient": ["Ingredient A"],
            "applicant_short": ["Sponsor A"],
            "license_type": ["351(a)"],
            "marketing_status": ["Rx"],
            "source_id": ["000123"],
            "coreason_id": ["uuid1"],
        }
    )

    with patch.object(pl.DataFrame, "write_database") as mock_write_db:
        load_silver_layer(mock_df, "postgresql://user:pass@localhost:5432/db")

        mock_write_db.assert_called_once_with(
            table_name="silver_FDA_PURPLE_BOOK",
            connection="postgresql://user:pass@localhost:5432/db",
            if_table_exists="replace",
            engine="adbc",
        )


def test_load_silver_layer_empty() -> None:
    mock_df = pl.DataFrame(
        {
            "bla_number": [],
            "trade_name": [],
        }
    )

    with patch.object(pl.DataFrame, "write_database") as mock_write_db:
        load_silver_layer(mock_df, "postgresql://user:pass@localhost:5432/db")

        # It should skip writing to database if height is 0
        mock_write_db.assert_not_called()


def test_process_silver_layer_all_invalid() -> None:
    # DB response with all invalid data
    mock_df = pl.DataFrame(
        {
            "source_bla_number": ["123", "456"],
            "proprietary_name": ["A", "B"],
            "proper_name": ["A", "B"],
            "applicant": ["A", "B"],
            "license_type": ["A", "B"],
            "approval_date": ["invalid_date", "invalid_date"],
            "exclusivity_expiration": [None, None],
            "marketing_status": ["Rx", "OTC"],
        }
    )

    with patch("polars.read_database", return_value=mock_df):
        import pytest

        from coreason_etl_purple_book.exceptions import DataIntegrityError

        with pytest.raises(DataIntegrityError, match=r"Data validation failed\. Error:"):
            process_silver_layer("postgresql://user:pass@localhost:5432/db")


def test_process_silver_layer_complex_dates_and_edge_cases() -> None:
    # DB response with edge cases:
    # 1. Various valid date formats
    # 2. Empty strings in optional date fields
    # 3. Extra columns that should be ignored by Pydantic
    mock_df = pl.DataFrame(
        {
            "source_bla_number": ["001", "002", "003", "004"],
            "proprietary_name": ["A", "B", "C", "D"],
            "proper_name": ["A", "B", "C", "D"],
            "applicant": ["A", "B", "C", "D"],
            "license_type": ["A", "B", "C", "D"],
            "approval_date": [
                "2023-01-01",  # ISO 8601
                "02/28/2024",  # MM/DD/YYYY
                "February 28, 2024",  # Month DD, YYYY
                "Feb 28, 2024",  # Mon DD, YYYY
            ],
            "exclusivity_expiration": [
                "",  # Empty string (should parse to None)
                " ",  # Whitespace string (should parse to None)
                None,  # Explicit None
                "2030-12-31",  # Valid date
            ],
            "marketing_status": ["Rx", "OTC", "Rx", "Rx"],
            "extra_unexpected_column": ["ignore", "this", "column", "entirely"],
        }
    )

    with patch("polars.read_database", return_value=mock_df):
        result_df = process_silver_layer("postgresql://user:pass@localhost:5432/db")

        assert len(result_df) == 4
        from datetime import date

        # Verify parsed approval dates
        assert result_df["approval_date"][0] == date(2023, 1, 1)
        assert result_df["approval_date"][1] == date(2024, 2, 28)
        assert result_df["approval_date"][2] == date(2024, 2, 28)
        assert result_df["approval_date"][3] == date(2024, 2, 28)

        # Verify parsed exclusivity dates (handling empty/whitespace strings vs valid ones)
        assert result_df["exclusivity_end_date"][0] is None
        assert result_df["exclusivity_end_date"][1] is None
        assert result_df["exclusivity_end_date"][2] is None
        assert result_df["exclusivity_end_date"][3] == date(2030, 12, 31)

        # Verify extra columns are cleanly ignored and not present in the output
        assert "extra_unexpected_column" not in result_df.columns


def test_process_silver_layer_missing_required_fields() -> None:
    # DB response missing required columns, simulating structural change in the source/bronze layer
    mock_df = pl.DataFrame(
        {
            "source_bla_number": ["123"],
            "proprietary_name": ["A"],
            # missing "proper_name" which maps to "ingredient"
            "applicant": ["A"],
            "license_type": ["A"],
            "approval_date": ["2023-01-01"],
            "exclusivity_expiration": [None],
            "marketing_status": ["Rx"],
        }
    )

    with patch("polars.read_database", return_value=mock_df):
        import pytest

        from coreason_etl_purple_book.exceptions import DataIntegrityError

        with pytest.raises(
            DataIntegrityError, match=r"(?s)Data validation failed\. Error:.*ingredient.*Field required"
        ):
            process_silver_layer("postgresql://user:pass@localhost:5432/db")
