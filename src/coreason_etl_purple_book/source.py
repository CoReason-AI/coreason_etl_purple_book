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
from datetime import UTC, date, datetime
from typing import Any

import dlt
from dlt.sources.helpers import requests

from coreason_etl_purple_book.exceptions import SourceSchemaError
from coreason_etl_purple_book.utils.logger import logger


class FdaPurpleBookSource:
    """
    AGENT INSTRUCTION: This class encapsulates the extraction logic for the FDA Purple Book dataset.
    It provides capabilities to download the dataset in a memory-efficient manner.
    """

    def get_latest_csv_url(self) -> str:
        """
        AGENT INSTRUCTION: Dynamically resolve the true underlying CSV URL
        by probing the FDA's predictable file storage pattern.
        """
        now = datetime.now()
        
        # Probe up to 3 months back to find the latest published file
        for i in range(3):
            month_offset = now.month - i
            year = now.year
            if month_offset <= 0:
                month_offset += 12
                year -= 1
                
            month_name = date(year, month_offset, 1).strftime('%B').lower()
            
            # The FDA uses both '/files/' and '/downloads/files/' inconsistently. We must check both.
            candidate_urls = [
                f"https://purplebooksearch.fda.gov/files/{year}/purplebook-search-{month_name}-data-download.csv",
                f"https://purplebooksearch.fda.gov/downloads/files/{year}/purplebook-search-{month_name}-data-download.csv"
            ]
            
            for direct_url in candidate_urls:
                logger.info(f"Probing FDA direct URL: {direct_url}")
                
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    # Use a streaming GET request to bypass HEAD blocks, fetching only headers initially
                    response = requests.get(direct_url, headers=headers, stream=True, timeout=10)
                    
                    content_type = response.headers.get("Content-Type", "")
                    
                    # If we get a 200 OK and it is NOT an HTML page, we found the true CSV file
                    if response.status_code == 200 and "text/html" not in content_type:
                        logger.info(f"Resolved valid CSV URL: {direct_url}")
                        response.close()  # Close the stream, we just needed to verify it exists
                        return direct_url
                        
                    response.close()
                except Exception as e:
                    logger.warning(f"Probe failed for {direct_url}: {e}")
                
        raise SourceSchemaError("Could not resolve the FDA Purple Book CSV URL via predictive routing.")

    def download_and_hash_csv(self, url: str) -> tuple[str, str]:
        """
        Downloads a file from the provided URL, streaming it to a temporary local file,
        and computes the MD5 hash incrementally.

        Args:
            url (str): The URL to download the CSV file from.

        Returns:
            Tuple[str, str]: A tuple containing the local file path and the MD5 hex digest.
        """
        # Intercept the generic SPA route and replace it with the true file URL
        if url.endswith("data-download"):
            logger.info("Intercepted generic SPA route. Resolving direct CSV link...")
            url = self.get_latest_csv_url()

        logger.info(f"Starting file download from {url}")
        md5_hash = hashlib.md5()  # noqa: S324

        fd, file_path = tempfile.mkstemp(suffix=".csv")

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            with os.fdopen(fd, "wb") as f, requests.get(url, stream=True, headers=headers) as response:
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


@dlt.resource(name="coreason_etl_purple_book_bronze_fda_purple_book", write_disposition="replace", max_table_nesting=0)  # type: ignore[untyped-decorator, unused-ignore]
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
            # Skip introductory metadata lines until we hit the actual header
            for line in csv_file:
                if line.startswith("N/R/U,Applicant,BLA Number"):
                    fieldnames = next(csv.reader([line]))
                    break
            else:
                raise SourceSchemaError("Could not find the header row in the CSV file.")

            reader = csv.DictReader(csv_file, fieldnames=fieldnames)

            # Validating against the updated FDA column names
            required_columns = {
                "BLA Number",
                "Proprietary Name",
                "Proper Name",
                "Applicant",
                "BLA Type",
                "Approval Date",
                "Exclusivity Expiration Date",
                "Marketing Status",
            }
            if reader.fieldnames:
                missing_columns = required_columns - set(reader.fieldnames)
                if missing_columns:
                    raise SourceSchemaError(f"Missing required columns in CSV header: {missing_columns}")
            else:
                raise SourceSchemaError("CSV file is empty or missing a header row.")

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


@dlt.source  # type: ignore[untyped-decorator, unused-ignore]
def fda_purple_book_source(url: str = "https://purplebooksearch.fda.gov/downloads/data-download") -> Any:
    """
    Creates a dlt source for the FDA Purple Book dataset.
    """
    return [fda_purple_book_resource(url=url)]
