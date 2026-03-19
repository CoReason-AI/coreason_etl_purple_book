# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

from typing import Any

import polars as pl
from pydantic import ValidationError

from coreason_etl_purple_book.exceptions import DataIntegrityError
from coreason_etl_purple_book.identity import get_coreason_id_expr
from coreason_etl_purple_book.schemas import SilverFdaPurpleBookManifest
from coreason_etl_purple_book.utils.logger import logger


def process_silver_layer(connection_uri: str) -> pl.DataFrame:
    """
    AGENT INSTRUCTION: Extracts the raw_content JSONB from the PostgreSQL Bronze table,
    normalizes types, generates coreason_id, and filters/validates using Pydantic.
    """
    # The requirement is to pull data from bronze and unpack JSONB in SQL.
    query = """
    SELECT
        raw_content->>'BLA Number' as source_bla_number,
        raw_content->>'Proprietary Name' as proprietary_name,
        raw_content->>'Proper Name' as proper_name,
        raw_content->>'Applicant' as applicant,
        raw_content->>'License Type' as license_type,
        raw_content->>'Approval Date' as approval_date,
        raw_content->>'Exclusivity Expiration' as exclusivity_expiration,
        raw_content->>'Marketing Status' as marketing_status
    FROM bronze.coreason_etl_purple_book_bronze_fda_purple_book
    """
    logger.info("Executing SQL to read from bronze layer.")
    df = pl.read_database(query=query, connection=connection_uri)

    logger.info(f"Loaded {df.height} rows from database.")

    # Rename columns to match Pydantic model.
    # Use strict=False so missing columns from the SQL query won't crash Polars.
    # Missing columns will correctly fail Pydantic validation instead.
    renamed_df = df.rename(
        {
            "source_bla_number": "bla_number",
            "proprietary_name": "trade_name",
            "proper_name": "ingredient",
            "applicant": "applicant_short",
            "exclusivity_expiration": "exclusivity_end_date",
        },
        strict=False,
    )

    valid_rows: list[dict[str, Any]] = []

    # Map the unpacked SQL columns to target schema fields for Pydantic
    try:
        from pydantic import TypeAdapter

        adapter = TypeAdapter(list[SilverFdaPurpleBookManifest])
        raw_dicts = renamed_df.to_dicts()
        validated_models = adapter.validate_python(raw_dicts)
        valid_rows = [model.model_dump() for model in validated_models]
    except ValidationError as e:
        # Pydantic ValidationError contains the list of errors
        raise DataIntegrityError(f"Data validation failed. Error: {e}") from e

    logger.info(f"Validated {len(valid_rows)} rows successfully.")

    if not valid_rows:
        schema: dict[str, pl.DataType | type[pl.DataType]] = {
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
        return pl.DataFrame(schema=schema)

    valid_df = pl.DataFrame(valid_rows)

    # Generate the dual ID using map_batches and PyArrow as required
    return valid_df.with_columns(source_id=pl.col("bla_number"), coreason_id=get_coreason_id_expr("bla_number"))


def load_silver_layer(df: pl.DataFrame, connection_uri: str) -> None:
    """
    AGENT INSTRUCTION: Loads the Silver Polars DataFrame into the PostgreSQL
    silver_FDA_PURPLE_BOOK table.
    """
    logger.info(f"Loading {df.height} rows into the silver layer database.")

    if df.height == 0:
        logger.info("Empty DataFrame provided. Skipping load.")
        return

    # Write the dataframe to the database
    df.write_database(
        table_name="silver.coreason_etl_purple_book_silver_fda_purple_book",
        connection=connection_uri,
        if_table_exists="replace",
        engine="adbc",
    )
    logger.info("Successfully loaded data into the silver layer.")
