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
from datetime import date, datetime

import polars as pl
from pydantic import BaseModel, Field, StrictStr, field_validator

from coreason_etl_purple_book.utils.logger import logger


class SilverFdaPurpleBookManifest(BaseModel):
    """
    AGENT INSTRUCTION: This model represents the Silver layer schema for FDA Purple Book records.
    Fields must strictly follow the target schema names from the Bronze-to-Silver handoff.
    """

    bla_number: StrictStr = Field(
        ...,
        description="BLA number. Sanitized, validated for length (max 6), and 6-digit left-padded.",
    )
    proprietary_name: str = Field(..., description="Brand name (Proprietary Name)")
    proper_name: str = Field(..., description="Biological/Core name (Active substance) (Proper Name)")
    applicant: str = Field(..., description="Sponsor (Applicant)")
    license_type: str = Field(..., description="e.g., 351(a) Reference, 351(k) Biosimilar")

    # UPDATED: Made approval_date optional to handle missing historical dates
    approval_date: date | None = Field(None, description="Parsed date format")
    exclusivity_expiration: date | None = Field(None, description="Optional exclusivity expiration date")
    marketing_status: str = Field(..., description="Rx, OTC, DISCN")
    strength: str | None = Field(None, description="Strength")
    route_of_administration: str | None = Field(None, description="Route of Administration")
    product_presentation: str | None = Field(None, description="Product Presentation")

    @field_validator("approval_date", "exclusivity_expiration", mode="before")
    @classmethod
    def parse_fda_dates(cls, v: str | date | datetime | None) -> date | None:
        """
        Parses FDA specific date formats into Python date objects.
        Expected formats include ISO 8601 (YYYY-MM-DD), MM/DD/YYYY, Month DD, YYYY, and DD-Mon-YY.
        """
        if not v:
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        if not isinstance(v, str):
            raise ValueError(f"Expected a string, date, or datetime, got {type(v).__name__}")

        v = v.strip()
        if not v:
            return None

        formats_to_try = [
            "%Y-%m-%d",  # 2024-02-28
            "%m/%d/%Y",  # 02/28/2024
            "%B %d, %Y",  # February 28, 2024
            "%b %d, %Y",  # Feb 28, 2024
            "%d-%b-%y",  # 21-May-04 (New FDA Format)
        ]

        for fmt in formats_to_try:
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Unrecognized date format: '{v}'")

    @field_validator("bla_number", mode="before")
    @classmethod
    def sanitize_and_pad_bla(cls, v: str) -> str:
        """
        Strips whitespace and non-alphanumeric chars. Validates length <= 6. Left-pads with zeros to 6 digits.
        """
        if not isinstance(v, str):
            raise ValueError(f"BLA Number must be a string, got {type(v).__name__}")

        # Strip all whitespace and non-alphanumeric characters
        sanitized = re.sub(r"[^a-zA-Z0-9]", "", v).strip()

        if len(sanitized) > 6:
            logger.warning(f"BLA Number exceeds 6 characters after sanitization: '{sanitized}'")

        # Left-pad with zeros
        return sanitized.zfill(6)


# Define the strict schemas to prevent PyArrow 'na' type inference errors on empty columns
SILVER_BASE_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
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
}

GOLD_EXPECTED_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
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
