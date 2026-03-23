# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

from datetime import datetime

import polars as pl

from coreason_etl_purple_book.utils.logger import logger


def process_gold_layer(df: pl.DataFrame, is_active: bool = True) -> pl.DataFrame:
    """
    AGENT INSTRUCTION: Processes the Silver layer DataFrame into the Gold layer schema.
    Applies filtering, derives boolean flags, and concatenates fields for vector embeddings.
    """
    logger.info("Starting Gold layer processing.")

    # Schema definition for empty dataframes to prevent downstream crashes
    expected_schema: dict[str, pl.DataType | type[pl.DataType]] = {
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
        "is_biosimilar": pl.Boolean,
        "is_protected": pl.Boolean,
        "vector_prep": pl.String,
    }

    if df.height == 0:
        logger.info("Empty Silver DataFrame provided. Returning empty Gold DataFrame with expected schema.")
        return pl.DataFrame(schema=expected_schema)

    # 1. Filter out discontinued products
    if is_active:
        logger.info("Filtering active products.")
        # Only exclude specifically 'DISCN' as per the spec, keep everything else
        df = df.filter(pl.col("marketing_status") != "DISCN")

        if df.height == 0:
            logger.info("No active products remained after filtering. Returning empty Gold DataFrame.")
            return pl.DataFrame(schema=expected_schema)

    # 2. Derive columns
    logger.info("Adding derived columns (is_biosimilar, is_protected, vector_prep).")
    # Pydantic validates as date, use timezone-naive date here to avoid ComputeError
    current_date = datetime.now().date()

    df = df.with_columns(
        is_biosimilar=(pl.col("license_type") == "351(k)"),
        is_protected=(pl.lit(current_date) < pl.col("exclusivity_expiration")).fill_null(False),
        vector_prep=pl.concat_str(
            [pl.col("proprietary_name"), pl.col("proper_name"), pl.col("applicant")], separator=" "
        ),
    )

    # Select the columns matching the target schema to ensure consistent ordering
    target_columns = list(expected_schema.keys())
    # The incoming df from silver might not have exactly all columns ordered perfectly.
    # Selecting the keys aligns them to the expected schema order.
    # But note that we might not have all columns if silver is missing them,
    # though the schema mapping in Silver handles that.

    logger.info(f"Gold layer processing complete. Returning {df.height} rows.")
    return df.select(target_columns)


def load_gold_layer(df: pl.DataFrame, connection_uri: str) -> None:
    """
    AGENT INSTRUCTION: Persists the transformed Gold Polars DataFrame
    into the PostgreSQL gold.coreason_etl_purple_book_gold_fda_purple_book table.
    """
    logger.info(f"Loading {df.height} rows into the gold layer database.")

    if df.height == 0:
        logger.info("Empty DataFrame provided. Skipping load.")
        return

    # Write the dataframe to the database
    df.write_database(
        table_name="gold.coreason_etl_purple_book_gold_fda_purple_book",
        connection=connection_uri,
        if_table_exists="replace",
        engine="adbc",
    )
    logger.info("Successfully loaded data into the gold layer.")
