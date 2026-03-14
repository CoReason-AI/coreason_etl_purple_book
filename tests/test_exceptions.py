# Copyright (c) 2026 CoReason Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_purple_book

import pytest

from coreason_etl_purple_book.exceptions import DataIntegrityError, SourceSchemaError


def test_source_schema_error() -> None:
    with pytest.raises(SourceSchemaError) as exc_info:
        raise SourceSchemaError("Schema mismatch")
    assert str(exc_info.value) == "Schema mismatch"


def test_data_integrity_error() -> None:
    with pytest.raises(DataIntegrityError) as exc_info:
        raise DataIntegrityError("Integrity check failed")
    assert str(exc_info.value) == "Integrity check failed"
