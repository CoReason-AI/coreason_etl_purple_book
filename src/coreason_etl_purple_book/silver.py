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

import adbc_driver_postgresql  # type: ignore[import-untyped, unused-ignore]
import polars as pl
from pydantic import ValidationError

from coreason_etl_purple_book.exceptions import DataIntegrityError
from coreason_etl_purple_book.identity import get_coreason_id_expr
from coreason_etl_purple_book.schemas import SILVER_BASE_SCHEMA, SilverFdaPurpleBookManifest
from coreason_etl_purple_book.utils.logger import logger

# Just so it's not removed by ruff or flagged by deptry as unused:
_ = adbc_driver_postgresql


def process_silver_layer(connection_uri: str) -> pl.DataFrame:
    """
    AGENT INSTRUCTION: Extracts the raw_content JSONB from the PostgreSQL Bronze table,
    normalizes types, generates coreason_id, and filters/validates using Pydantic.
    """
    query = """
    SELECT
        raw_content->>'BLA Number' as bla_number,
        raw_content->>'Proprietary Name' as proprietary_name,
        raw_content->>'Proper Name' as proper_name,
        raw_content->>'Applicant' as applicant,
        raw_content->>'License Type' as license_type,
        raw_content->>'Approval Date' as approval_date,
        raw_content->>'Exclusivity Expiration' as exclusivity_expiration,
        raw_content->>'Marketing Status' as marketing_status,
        raw_content->>'Strength' as strength,
        raw_content->>'Route of Administration' as route_of_administration,
        raw_content->>'Product Presentation' as product_presentation
    FROM bronze.coreason_etl_purple_book_bronze_fda_purple_book
    """
    logger.info("Executing SQL to read from bronze layer.")
    df = pl.read_database_uri(query=query, uri=connection_uri)

    logger.info(f"Loaded {df.height} rows from database.")

    # Filter out any repeated header rows that sneak into the dataset
    df = df.filter(pl.col("bla_number") != "BLA Number")

    valid_rows: list[dict[str, Any]] = []

    try:
        from pydantic import TypeAdapter

        adapter = TypeAdapter(list[SilverFdaPurpleBookManifest])
        raw_dicts = df.to_dicts()
        validated_models = adapter.validate_python(raw_dicts)
        valid_rows = [model.model_dump() for model in validated_models]
    except ValidationError as e:
        raise DataIntegrityError(f"Data validation failed. Error: {e}") from e

    logger.info(f"Validated {len(valid_rows)} rows successfully.")

    if not valid_rows:
        empty_schema = SILVER_BASE_SCHEMA.copy()
        empty_schema["source_id"] = pl.String
        empty_schema["coreason_id"] = pl.String
        return pl.DataFrame(schema=empty_schema)

    # Force the schema during DataFrame creation
    valid_df = pl.DataFrame(valid_rows, schema=SILVER_BASE_SCHEMA)

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
