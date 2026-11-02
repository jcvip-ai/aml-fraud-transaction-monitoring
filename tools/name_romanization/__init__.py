# SPDX-License-Identifier: AGPL-3.0-or-later
"""Romanization-aware matching of Chinese names (Wade-Giles, Hanyu, Tongyong)."""

from .romanization import (
    DEFAULT_TABLE_PATH,
    SYSTEMS,
    RomanizationTable,
    could_be_same_person,
    equivalent_spellings,
    load_table,
    segment_syllables,
)

__all__ = [
    "DEFAULT_TABLE_PATH",
    "SYSTEMS",
    "RomanizationTable",
    "could_be_same_person",
    "equivalent_spellings",
    "load_table",
    "segment_syllables",
]
