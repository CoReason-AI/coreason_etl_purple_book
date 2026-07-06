# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

import os
from unittest.mock import MagicMock, patch

import polars as pl

from coreason_etl_purple_book.main import hello_world, run_pipeline


def test_hello_world() -> None:
    assert hello_world() == "Hello World!"


def test_run_pipeline_schema_failure() -> None:
    # Verify that the pipeline continues even if the CREATE SCHEMA statements fail
    with (
        patch("coreason_etl_purple_book.main.fda_purple_book_source"),
        patch("coreason_etl_purple_book.main.load_gold_layer"),
        patch("coreason_etl_purple_book.main.process_gold_layer"),
        patch("coreason_etl_purple_book.main.load_silver_layer"),
        patch("coreason_etl_purple_book.main.process_silver_layer"),
        patch("dlt.pipeline"),
        patch("psycopg2.connect", side_effect=Exception("DB Error")),
        patch.dict(os.environ, {"FDA_PURPLE_BOOK_URL": "http://test.url"}, clear=True),
    ):
        run_pipeline()


@patch("coreason_etl_purple_book.main.load_gold_layer")
@patch("coreason_etl_purple_book.main.process_gold_layer")
@patch("coreason_etl_purple_book.main.load_silver_layer")
@patch("coreason_etl_purple_book.main.process_silver_layer")
@patch("dlt.pipeline")
@patch.dict(os.environ, {"FDA_PURPLE_BOOK_URL": "http://test.url", "PGUSER": "testuser"}, clear=True)
def test_run_pipeline(
    mock_pipeline_cls: MagicMock,
    mock_process_silver: MagicMock,
    mock_load_silver: MagicMock,
    mock_process_gold: MagicMock,
    mock_load_gold: MagicMock,
) -> None:
    # Setup mocks
    mock_pipeline_instance = MagicMock()
    mock_pipeline_cls.return_value = mock_pipeline_instance
    mock_pipeline_instance.run.return_value = "LoadInfoMock"

    mock_silver_df = pl.DataFrame({"test": [1]})
    mock_process_silver.return_value = mock_silver_df

    mock_gold_df = pl.DataFrame({"test": [2]})
    mock_process_gold.return_value = mock_gold_df

    # Execute
    with (
        patch("coreason_etl_purple_book.main.fda_purple_book_source") as mock_source,
        patch("psycopg2.connect") as mock_connect,
    ):
        mock_source_obj = MagicMock()
        mock_source.return_value = mock_source_obj

        # Mock psycopg2 connection
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn

        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        run_pipeline()

        # Verify DDL executed
        mock_connect.assert_called_once()
        mock_conn.cursor.assert_called_once()
        assert mock_cursor.execute.call_count == 3

        # Assert Bronze Pipeline
        mock_pipeline_cls.assert_called_once_with(
            pipeline_name="fda_purple_book_pipeline",
            destination="postgres",
            dataset_name="bronze",
        )
        mock_source.assert_called_once_with(url="http://test.url")
        mock_pipeline_instance.run.assert_called_once_with(mock_source_obj)

        expected_conn_uri = "postgresql://testuser:postgres@localhost:5432/postgres"

        # Assert Silver processing
        mock_process_silver.assert_called_once_with(connection_uri=expected_conn_uri)
        mock_load_silver.assert_called_once_with(df=mock_silver_df, connection_uri=expected_conn_uri)

        # Assert Gold processing
        mock_process_gold.assert_called_once_with(df=mock_silver_df, is_active=True)
        mock_load_gold.assert_called_once_with(df=mock_gold_df, connection_uri=expected_conn_uri)
