# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

import csv
import hashlib
import os
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import dlt
from dlt.extract.source import DltSource
from dlt.sources.helpers import requests

from coreason_etl_purple_book.utils.logger import logger


class FdaPurpleBookSource:
    """
    AGENT INSTRUCTION: This class encapsulates the extraction logic for the FDA Purple Book dataset.
    It provides capabilities to download the dataset in a memory-efficient manner.
    """

    def download_and_hash_csv(self, url: str) -> tuple[str, str]:
        """
        Downloads a file from the provided URL, streaming it to a temporary local file,
        and computes the MD5 hash incrementally.

        Args:
            url (str): The URL to download the CSV file from.

        Returns:
            Tuple[str, str]: A tuple containing the local file path and the MD5 hex digest.
        """
        logger.info(f"Starting file download from {url}")
        md5_hash = hashlib.md5()  # noqa: S324

        fd, file_path = tempfile.mkstemp(suffix=".csv")

        try:
            with os.fdopen(fd, "wb") as f, requests.get(url, stream=True) as response:
                response.raise_for_status()
                # Stream the response in chunks to avoid OOM errors
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        md5_hash.update(chunk)
                        f.write(chunk)

            md5_digest = md5_hash.hexdigest()
            logger.info(f"File downloaded successfully to {file_path}. MD5: {md5_digest}")
            return file_path, md5_digest
        except Exception as e:
            logger.exception(f"Failed to download file from {url}")
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e


@dlt.resource(name="bronze_FDA_PURPLE_BOOK", write_disposition="replace", max_table_nesting=0)
def fda_purple_book_resource(url: str) -> Iterator[dict[str, Any]]:
    """
    Downloads the FDA Purple Book dataset and yields raw CSV rows in a single "raw_content" JSON key.
    """
    source = FdaPurpleBookSource()
    file_path, md5_digest = source.download_and_hash_csv(url)

    # Use timezone-aware UTC datetime
    ingestion_ts = datetime.now(UTC).isoformat()

    # Determine source_file name
    source_file = url.split("/")[-1] if "/" in url else "purplebook-search-data.csv"

    try:
        with open(file_path, encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                yield {
                    "source_file": source_file,
                    "ingestion_ts": ingestion_ts,
                    "source_hash": md5_digest,
                    "raw_content": row,
                }
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@dlt.source
def fda_purple_book_source(url: str = "https://purplebooksearch.fda.gov/downloads/data-download") -> Any:
    """
    Creates a dlt source for the FDA Purple Book dataset.
    """
    return [fda_purple_book_resource(url=url)]
