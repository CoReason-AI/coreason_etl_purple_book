# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

import re
from datetime import datetime

from pydantic import BaseModel, Field, StrictStr, field_validator

from coreason_etl_purple_book.exceptions import DataIntegrityError


class SilverFdaPurpleBookManifest(BaseModel):
    """
    AGENT INSTRUCTION: This model represents the Silver layer schema for FDA Purple Book records.
    Fields must strictly follow the target schema names from the Bronze-to-Silver handoff.
    """

    bla_number: StrictStr = Field(
        ...,
        description="BLA number. Sanitized, validated for length (max 6), and 6-digit left-padded.",
    )
    trade_name: str = Field(..., description="Brand name (Proprietary Name)")
    ingredient: str = Field(..., description="Biological/Core name (Active substance) (Proper Name)")
    applicant_short: str = Field(..., description="Sponsor (Applicant)")
    license_type: str = Field(..., description="e.g., 351(a) Reference, 351(k) Biosimilar")
    approval_date: datetime = Field(..., description="Parsed datetime format")
    exclusivity_end_date: datetime | None = Field(None, description="Optional exclusivity expiration date")
    marketing_status: str = Field(..., description="Rx, OTC, DISCN")

    @field_validator("approval_date", "exclusivity_end_date", mode="before")
    @classmethod
    def parse_fda_dates(cls, v: str | datetime | None) -> datetime | None:
        """
        Parses FDA specific date formats into Python datetime objects.
        Expected formats include ISO 8601 (YYYY-MM-DD), MM/DD/YYYY, and Month DD, YYYY.
        """
        if not v:
            return None
        if isinstance(v, datetime):
            return v
        if not isinstance(v, str):
            raise ValueError(f"Expected a string or datetime, got {type(v).__name__}")

        v = v.strip()
        if not v:
            return None

        # Try various date formats
        formats_to_try = [
            "%Y-%m-%d",  # 2024-02-28
            "%m/%d/%Y",  # 02/28/2024
            "%B %d, %Y",  # February 28, 2024
            "%b %d, %Y",  # Feb 28, 2024
        ]

        for fmt in formats_to_try:
            try:
                return datetime.strptime(v, fmt)
            except ValueError:
                continue

        raise ValueError(f"Unrecognized date format: '{v}'")

    @field_validator("bla_number", mode="before")
    @classmethod
    def sanitize_and_pad_bla(cls, v: str) -> str:
        """
        Strips whitespace and non-alphanumeric chars. Validates length <= 6. Left-pads with zeros to 6 digits.
        """
        # Type validation is implicitly handled by StrictStr, but if we're in 'before' validator,
        # we need to be careful. StrictStr actually validates during parsing. Let's do a strict check here.
        if not isinstance(v, str):
            raise ValueError(f"BLA Number must be a string, got {type(v).__name__}")

        # Strip all whitespace and non-alphanumeric characters
        sanitized = re.sub(r"[^a-zA-Z0-9]", "", v).strip()

        if len(sanitized) > 6:
            raise DataIntegrityError(f"BLA Number exceeds 6 characters after sanitization: '{sanitized}'")

        # Left-pad with zeros
        return sanitized.zfill(6)
