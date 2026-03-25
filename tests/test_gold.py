# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

from datetime import date, datetime, timedelta
from unittest.mock import patch

import polars as pl

from coreason_etl_purple_book.gold import load_gold_layer, process_gold_layer


def test_process_gold_layer_happy_path() -> None:
    current_date = datetime.now().date()
    future_date = current_date + timedelta(days=365)
    past_date = current_date - timedelta(days=365)

    silver_df = pl.DataFrame(
        {
            "bla_number": ["000123", "000456", "000789"],
            "proprietary_name": ["Brand A", "Brand B", "Brand C"],
            "proper_name": ["Ingredient A", "Ingredient B", "Ingredient C"],
            "applicant": ["Sponsor A", "Sponsor B", "Sponsor C"],
            "license_type": ["351(a)", "351(k)", "351(a)"],
            "approval_date": [date(2023, 1, 1), date(2024, 5, 15), date(2020, 1, 1)],
            "exclusivity_expiration": [future_date, None, past_date],
            "marketing_status": ["Rx", "OTC", "Rx"],
            "strength": ["10mg", None, "20mg"],
            "route_of_administration": ["Oral", "IV", "Oral"],
            "product_presentation": ["Tablet", "Vial", "Capsule"],
            "source_id": ["000123", "000456", "000789"],
            "coreason_id": ["uuid1", "uuid2", "uuid3"],
        }
    )

    gold_df = process_gold_layer(silver_df)

    assert gold_df.height == 3

    # Check boolean derivations
    assert gold_df["is_biosimilar"][0] is False
    assert gold_df["is_biosimilar"][1] is True
    assert gold_df["is_biosimilar"][2] is False

    assert gold_df["is_protected"][0] is True
    assert gold_df["is_protected"][1] is False
    assert gold_df["is_protected"][2] is False

    # Check vector prep
    assert gold_df["vector_prep"][0] == "Brand A Ingredient A Sponsor A"
    assert gold_df["vector_prep"][1] == "Brand B Ingredient B Sponsor B"
    assert gold_df["vector_prep"][2] == "Brand C Ingredient C Sponsor C"


def test_process_gold_layer_filter_active() -> None:
    silver_df = pl.DataFrame(
        {
            "bla_number": ["000123", "000456"],
            "proprietary_name": ["Brand A", "Brand B"],
            "proper_name": ["Ingredient A", "Ingredient B"],
            "applicant": ["Sponsor A", "Sponsor B"],
            "license_type": ["351(a)", "351(k)"],
            "approval_date": [date(2023, 1, 1), date(2024, 5, 15)],
            "exclusivity_expiration": [None, None],
            "marketing_status": ["Rx", "DISCN"],
            "strength": [None, None],
            "route_of_administration": [None, None],
            "product_presentation": [None, None],
            "source_id": ["000123", "000456"],
            "coreason_id": ["uuid1", "uuid2"],
        }
    )

    # By default, is_active=True
    gold_df_active = process_gold_layer(silver_df)
    assert gold_df_active.height == 1
    assert gold_df_active["marketing_status"][0] == "Rx"

    # With is_active=False
    gold_df_all = process_gold_layer(silver_df, is_active=False)
    assert gold_df_all.height == 2
    assert "DISCN" in gold_df_all["marketing_status"].to_list()


def test_process_gold_layer_empty() -> None:
    # Testing empty DataFrame input
    empty_schema: dict[str, pl.DataType | type[pl.DataType]] = {
        "bla_number": pl.String,
        "proprietary_name": pl.String,
        "proper_name": pl.String,
        "applicant": pl.String,
        "license_type": pl.String,
        "approval_date": pl.Date,
        "exclusivity_expiration": pl.Date,
        "marketing_status": pl.String,
        "strength": pl.String,
        "route_of_administration": pl.String,
        "product_presentation": pl.String,
        "source_id": pl.String,
        "coreason_id": pl.String,
    }
    empty_df = pl.DataFrame(schema=empty_schema)

    gold_df = process_gold_layer(empty_df)
    assert gold_df.height == 0
    # Expected columns check
    expected_cols = [
        "bla_number",
        "proprietary_name",
        "proper_name",
        "applicant",
        "license_type",
        "approval_date",
        "exclusivity_expiration",
        "marketing_status",
        "strength",
        "route_of_administration",
        "product_presentation",
        "source_id",
        "coreason_id",
        "is_biosimilar",
        "is_protected",
        "vector_prep",
    ]
    assert list(gold_df.columns) == expected_cols


def test_load_gold_layer_valid() -> None:
    mock_df = pl.DataFrame(
        {
            "bla_number": ["000123"],
            "proprietary_name": ["Brand A"],
            "proper_name": ["Ingredient A"],
            "applicant": ["Sponsor A"],
            "license_type": ["351(a)"],
            "approval_date": [date(2023, 1, 1)],
            "marketing_status": ["Rx"],
            "strength": ["10mg"],
            "route_of_administration": ["Oral"],
            "product_presentation": ["Tablet"],
            "source_id": ["000123"],
            "coreason_id": ["uuid1"],
            "is_biosimilar": [False],
            "is_protected": [True],
            "vector_prep": ["prep"],
        }
    )

    with patch.object(pl.DataFrame, "write_database") as mock_write_db:
        load_gold_layer(mock_df, "postgresql://user:pass@localhost:5432/db")

        mock_write_db.assert_called_once_with(
            table_name="gold.coreason_etl_purple_book_gold_fda_purple_book",
            connection="postgresql://user:pass@localhost:5432/db",
            if_table_exists="replace",
            engine="adbc",
        )


def test_load_gold_layer_empty() -> None:
    mock_df = pl.DataFrame(
        {
            "bla_number": [],
            "trade_name": [],
        }
    )

    with patch.object(pl.DataFrame, "write_database") as mock_write_db:
        load_gold_layer(mock_df, "postgresql://user:pass@localhost:5432/db")

        # It should skip writing to database if height is 0
        mock_write_db.assert_not_called()


def test_process_gold_layer_all_discontinued() -> None:
    silver_df = pl.DataFrame(
        {
            "bla_number": ["000123"],
            "proprietary_name": ["Brand A"],
            "proper_name": ["Ingredient A"],
            "applicant": ["Sponsor A"],
            "license_type": ["351(a)"],
            "approval_date": [date(2023, 1, 1)],
            "exclusivity_expiration": [None],
            "marketing_status": ["DISCN"],
            "strength": [None],
            "route_of_administration": [None],
            "product_presentation": [None],
            "source_id": ["000123"],
            "coreason_id": ["uuid1"],
        }
    )

    gold_df = process_gold_layer(silver_df)
    assert gold_df.height == 0
    # Expected columns check
    expected_cols = [
        "bla_number",
        "proprietary_name",
        "proper_name",
        "applicant",
        "license_type",
        "approval_date",
        "exclusivity_expiration",
        "marketing_status",
        "strength",
        "route_of_administration",
        "product_presentation",
        "source_id",
        "coreason_id",
        "is_biosimilar",
        "is_protected",
        "vector_prep",
    ]
    assert list(gold_df.columns) == expected_cols
