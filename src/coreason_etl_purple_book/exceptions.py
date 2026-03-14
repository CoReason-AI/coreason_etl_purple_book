# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book


class SourceSchemaError(Exception):
    """
    AGENT INSTRUCTION: Exception raised when the source data schema differs from what is expected.
    """


class DataIntegrityError(Exception):
    """
    AGENT INSTRUCTION: Exception raised when there is an integrity issue with the data.
    """
