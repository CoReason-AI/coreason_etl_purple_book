# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

import hashlib
import os
import tempfile

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
