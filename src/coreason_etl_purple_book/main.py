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

import dlt

from coreason_etl_purple_book.gold import load_gold_layer, process_gold_layer
from coreason_etl_purple_book.silver import load_silver_layer, process_silver_layer
from coreason_etl_purple_book.source import fda_purple_book_source
from coreason_etl_purple_book.utils.logger import logger


def run_pipeline() -> None:
    """
    AGENT INSTRUCTION: Orchestrates the execution of the Bronze, Silver, and Gold pipelines.
    Expects standard database credentials to be configured via environment variables.
    """
    logger.info("Starting FDA Purple Book ETL Pipeline")

    # Construct PostgreSQL URI from environment variables (standard configuration)
    pg_host = os.environ.get("PGHOST", "localhost")
    pg_port = os.environ.get("PGPORT", "5432")
    pg_user = os.environ.get("PGUSER", "postgres")
    pg_password = os.environ.get("PGPASSWORD", "postgres")
    pg_database = os.environ.get("PGDATABASE", "postgres")

    connection_uri = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"

    # 1. Bronze Layer Extraction and Loading (using dlt)
    logger.info("Executing Bronze Layer Pipeline")
    pipeline = dlt.pipeline(
        pipeline_name="fda_purple_book_pipeline",
        destination="postgres",
        dataset_name="public",  # Use public or target schema as required
    )

    # We allow parameterized URL if provided in env, otherwise fallback to source default
    url = os.environ.get("FDA_PURPLE_BOOK_URL", "https://purplebooksearch.fda.gov/downloads/data-download")
    source = fda_purple_book_source(url=url)

    load_info = pipeline.run(source)
    logger.info(f"Bronze Layer Pipeline completed: {load_info}")

    # 2. Silver Layer Normalization and Loading
    logger.info("Executing Silver Layer Pipeline")
    silver_df = process_silver_layer(connection_uri=connection_uri)
    load_silver_layer(df=silver_df, connection_uri=connection_uri)

    # 3. Gold Layer Enrichment and Loading
    logger.info("Executing Gold Layer Pipeline")
    gold_df = process_gold_layer(df=silver_df, is_active_only=True)
    load_gold_layer(df=gold_df, connection_uri=connection_uri)

    logger.info("FDA Purple Book ETL Pipeline completed successfully.")


def hello_world() -> str:
    logger.info("Hello World!")
    return "Hello World!"
