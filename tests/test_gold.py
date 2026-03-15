# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

from datetime import UTC, date, datetime, timedelta

import polars as pl

from coreason_etl_purple_book.gold import process_gold_layer


def test_process_gold_layer_happy_path() -> None:
    current_date = datetime.now(UTC).date()
    future_date = current_date + timedelta(days=365)
    past_date = current_date - timedelta(days=365)

    silver_df = pl.DataFrame(
        {
            "bla_number": ["000123", "000456", "000789"],
            "trade_name": ["Brand A", "Brand B", "Brand C"],
            "ingredient": ["Ingredient A", "Ingredient B", "Ingredient C"],
            "applicant_short": ["Sponsor A", "Sponsor B", "Sponsor C"],
            "license_type": ["351(a)", "351(k)", "351(a)"],
            "approval_date": [date(2023, 1, 1), date(2024, 5, 15), date(2020, 1, 1)],
            "exclusivity_end_date": [future_date, None, past_date],
            "marketing_status": ["Rx", "OTC", "Rx"],
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
            "trade_name": ["Brand A", "Brand B"],
            "ingredient": ["Ingredient A", "Ingredient B"],
            "applicant_short": ["Sponsor A", "Sponsor B"],
            "license_type": ["351(a)", "351(k)"],
            "approval_date": [date(2023, 1, 1), date(2024, 5, 15)],
            "exclusivity_end_date": [None, None],
            "marketing_status": ["Rx", "DISCN"],
            "source_id": ["000123", "000456"],
            "coreason_id": ["uuid1", "uuid2"],
        }
    )

    # By default, is_active_only=True
    gold_df_active = process_gold_layer(silver_df)
    assert gold_df_active.height == 1
    assert gold_df_active["marketing_status"][0] == "Rx"

    # With is_active_only=False
    gold_df_all = process_gold_layer(silver_df, is_active_only=False)
    assert gold_df_all.height == 2
    assert "DISCN" in gold_df_all["marketing_status"].to_list()


def test_process_gold_layer_empty() -> None:
    # Testing empty DataFrame input
    empty_schema = {
        "bla_number": pl.String,
        "trade_name": pl.String,
        "ingredient": pl.String,
        "applicant_short": pl.String,
        "license_type": pl.String,
        "approval_date": pl.Date,
        "exclusivity_end_date": pl.Date,
        "marketing_status": pl.String,
        "source_id": pl.String,
        "coreason_id": pl.String,
    }
    empty_df = pl.DataFrame(schema=empty_schema)

    gold_df = process_gold_layer(empty_df)
    assert gold_df.height == 0
    # Expected columns check
    expected_cols = [
        "bla_number",
        "trade_name",
        "ingredient",
        "applicant_short",
        "license_type",
        "approval_date",
        "exclusivity_end_date",
        "marketing_status",
        "source_id",
        "coreason_id",
        "is_biosimilar",
        "is_protected",
        "vector_prep",
    ]
    assert list(gold_df.columns) == expected_cols


def test_process_gold_layer_all_discontinued() -> None:
    silver_df = pl.DataFrame(
        {
            "bla_number": ["000123"],
            "trade_name": ["Brand A"],
            "ingredient": ["Ingredient A"],
            "applicant_short": ["Sponsor A"],
            "license_type": ["351(a)"],
            "approval_date": [date(2023, 1, 1)],
            "exclusivity_end_date": [None],
            "marketing_status": ["DISCN"],
            "source_id": ["000123"],
            "coreason_id": ["uuid1"],
        }
    )

    gold_df = process_gold_layer(silver_df)
    assert gold_df.height == 0
    # Expected columns check
    expected_cols = [
        "bla_number",
        "trade_name",
        "ingredient",
        "applicant_short",
        "license_type",
        "approval_date",
        "exclusivity_end_date",
        "marketing_status",
        "source_id",
        "coreason_id",
        "is_biosimilar",
        "is_protected",
        "vector_prep",
    ]
    assert list(gold_df.columns) == expected_cols
