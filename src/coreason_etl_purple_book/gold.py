# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

import polars as pl

from coreason_etl_purple_book.schemas import GOLD_EXPECTED_SCHEMA
from coreason_etl_purple_book.utils.logger import logger


def process_gold_layer(df: pl.DataFrame, is_active: bool = True) -> pl.DataFrame:
    """
    AGENT INSTRUCTION: Processes the Silver layer DataFrame into the Gold layer schema.
    Applies filtering, derives boolean flags.
    """
    logger.info("Starting Gold layer processing.")

    if df.height == 0:
        logger.info("Empty Silver DataFrame provided. Returning empty Gold DataFrame with expected schema.")
        return pl.DataFrame(schema=GOLD_EXPECTED_SCHEMA)

    # 1. Filter out discontinued products
    if is_active:
        logger.info("Filtering active products.")
        # Only exclude specifically 'DISCN' as per the spec, keep everything else
        df = df.filter(pl.col("marketing_status") != "DISCN")

        if df.height == 0:
            logger.info("No active products remained after filtering. Returning empty Gold DataFrame.")
            return pl.DataFrame(schema=GOLD_EXPECTED_SCHEMA)

    # 2. Derive columns
    logger.info("Adding derived columns (is_biosimilar, bla_type).")

    df = df.with_columns(
        is_biosimilar=(pl.col("licensure") == "351(k)"),
        bla_type=pl.when(pl.col("licensure") == "351(a)").then(pl.lit("Reference"))
                   .when(pl.col("licensure") == "351(k)").then(pl.lit("Biosimilar"))
                   .otherwise(pl.lit("Unknown"))
    )

    # Select the columns matching the target schema to ensure consistent ordering
    target_columns = list(GOLD_EXPECTED_SCHEMA.keys())

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
