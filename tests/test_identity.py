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

import polars as pl

from coreason_etl_purple_book.identity import (
    NAMESPACE_FDA_PURPLE_BOOK,
    generate_coreason_id_batch,
    get_coreason_id_expr,
)


def test_namespace_fda_purple_book_is_deterministic() -> None:
    expected_namespace = uuid.uuid5(uuid.NAMESPACE_OID, "FDA_PURPLE_BOOK")
    assert expected_namespace == NAMESPACE_FDA_PURPLE_BOOK


def test_generate_coreason_id_batch_valid() -> None:
    test_ids = ["001234", "005678", "009012"]
    series = pl.Series("bla_number", test_ids, dtype=pl.String)

    result = generate_coreason_id_batch(series)

    assert len(result) == 3
    assert result.dtype == pl.String
    assert result[0] == str(uuid.uuid5(NAMESPACE_FDA_PURPLE_BOOK, "001234"))
    assert result[1] == str(uuid.uuid5(NAMESPACE_FDA_PURPLE_BOOK, "005678"))
    assert result[2] == str(uuid.uuid5(NAMESPACE_FDA_PURPLE_BOOK, "009012"))


def test_generate_coreason_id_batch_empty() -> None:
    series = pl.Series("bla_number", [], dtype=pl.String)

    result = generate_coreason_id_batch(series)

    assert len(result) == 0
    assert result.dtype == pl.String


def test_generate_coreason_id_batch_with_nulls() -> None:
    test_ids = ["001234", None, "009012"]
    series = pl.Series("bla_number", test_ids, dtype=pl.String)

    result = generate_coreason_id_batch(series)

    assert len(result) == 3
    assert result[0] == str(uuid.uuid5(NAMESPACE_FDA_PURPLE_BOOK, "001234"))
    assert result[1] is None
    assert result[2] == str(uuid.uuid5(NAMESPACE_FDA_PURPLE_BOOK, "009012"))


def test_get_coreason_id_expr() -> None:
    df = pl.DataFrame({"bla_number": ["001234", "005678"]})

    result_df = df.with_columns(coreason_id=get_coreason_id_expr("bla_number"))

    assert "coreason_id" in result_df.columns
    assert len(result_df) == 2
    assert result_df["coreason_id"][0] == str(uuid.uuid5(NAMESPACE_FDA_PURPLE_BOOK, "001234"))
    assert result_df["coreason_id"][1] == str(uuid.uuid5(NAMESPACE_FDA_PURPLE_BOOK, "005678"))
