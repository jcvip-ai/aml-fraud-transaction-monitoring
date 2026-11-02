# SPDX-License-Identifier: AGPL-3.0-or-later
"""Romanization-aware comparison of Chinese names.

Converts a name between Wade-Giles, Hanyu Pinyin and Tongyong Pinyin and
decides whether two spellings could belong to the same person. The syllable
mapping lives in syllables.csv next to this file, so adding a syllable is a
CSV change only (NFR5). Standard library only (NFR2), Python 3.10+ (NFR1).
"""

import csv
import functools
import itertools
from dataclasses import dataclass
from pathlib import Path

SYSTEMS = ("wade_giles", "hanyu", "tongyong")
DEFAULT_TABLE_PATH = Path(__file__).with_name("syllables.csv")

# Typographic marks people type instead of the ASCII apostrophe (FR2.4).
_APOSTROPHE_VARIANTS = ("\u2019", "\u2018", "\u02bb", "\u02bc", "`")


@dataclass(frozen=True)
class RomanizationTable:
    """Equivalent-syllable rows and the spelling index built from them."""

    rows: tuple[dict[str, str], ...]
    index: dict[str, frozenset[int]]
    max_length: int


def _normalize_text(text: str) -> str:
    """Lower-case, trim and unify apostrophes (FR2.1, FR2.4)."""
    normalized = text.strip().lower()
    for variant in _APOSTROPHE_VARIANTS:
        normalized = normalized.replace(variant, "'")
    return normalized


def _lookup_keys(row: dict[str, str]) -> set[str]:
    """Every spelling that should find this row.

    A Wade-Giles spelling also answers without its apostrophe, so CHANG finds
    both chang (zhang) and ch'ang (chang): extra matches beat missed ones (FR4.2).
    """
    wade_giles = row["wade_giles"]
    return {wade_giles, wade_giles.replace("'", ""), row["hanyu"], row["tongyong"]}


def load_table(path: str | Path | None = None) -> RomanizationTable:
    """Load and validate a mapping CSV with header wade_giles,hanyu,tongyong (FR6.1)."""
    table_path = Path(path) if path is not None else DEFAULT_TABLE_PATH
    with table_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != SYSTEMS:
            raise ValueError(
                f"{table_path}: header must be {','.join(SYSTEMS)}, got {reader.fieldnames}"
            )
        rows = []
        for line_number, record in enumerate(reader, start=2):
            row = {}
            for system in SYSTEMS:
                value = _normalize_text(record.get(system) or "")
                if not value:
                    raise ValueError(f"{table_path}:{line_number}: empty {system} cell")
                row[system] = value
            rows.append(row)
    if not rows:
        raise ValueError(f"{table_path}: the table has no syllable rows")
    index: dict[str, set[int]] = {}
    for row_id, row in enumerate(rows):
        for key in _lookup_keys(row):
            index.setdefault(key, set()).add(row_id)
    return RomanizationTable(
        rows=tuple(rows),
        index={key: frozenset(row_ids) for key, row_ids in index.items()},
        max_length=max(len(key) for key in index),
    )


@functools.lru_cache(maxsize=1)
def _default_table() -> RomanizationTable:
    return load_table()


def _segment(piece: str, table: RomanizationTable) -> list[str]:
    """Split a run-together piece, always taking the longest known syllable (FR3.1).

    When no known syllable starts at the current position, the rest of the
    piece is kept unchanged as one unknown syllable (FR3.2).
    """
    syllables = []
    position = 0
    while position < len(piece):
        end = min(len(piece), position + table.max_length)
        while end > position and piece[position:end] not in table.index:
            end -= 1
        if end == position:
            syllables.append(piece[position:])
            break
        syllables.append(piece[position:end])
        position = end
    return syllables


def _parse(name: str, table: RomanizationTable) -> list[list[str]]:
    """Name -> parts (space separated) -> syllables (hyphen or run-together, FR2.2)."""
    if not isinstance(name, str):
        raise TypeError(f"name must be a str, got {type(name).__name__}")
    parts = []
    for word in _normalize_text(name).split():
        syllables = []
        for piece in word.split("-"):
            if piece:
                syllables.extend(_segment(piece, table))
        if syllables:
            parts.append(syllables)
    if not parts:
        raise ValueError("name must contain at least one syllable; got an empty string")
    return parts


def segment_syllables(name: str, table: RomanizationTable | None = None) -> list[str]:
    """Return the normalized syllables of a name in input order."""
    if table is None:
        table = _default_table()
    return [syllable for part in _parse(name, table) for syllable in part]


def _system_spellings(syllable: str, system: str, table: RomanizationTable) -> list[str]:
    row_ids = table.index.get(syllable)
    if row_ids is None:
        return [syllable.capitalize()]
    return sorted({table.rows[row_id][system].capitalize() for row_id in row_ids})


def equivalent_spellings(
    name: str, table: RomanizationTable | None = None
) -> dict[str, list[str]]:
    """Return every candidate spelling of a name per system (FR4.1, FR4.2).

    Keys are wade_giles, hanyu and tongyong. Syllables are capitalized, joined
    with "-" inside a name part, and parts keep the input order, for example
    "Hsiao-Ming Chang" -> hanyu ["Xiao-Ming Chang", "Xiao-Ming Zhang"].
    """
    if table is None:
        table = _default_table()
    parts = _parse(name, table)
    spellings = {}
    for system in SYSTEMS:
        part_options = [
            [
                "-".join(combination)
                for combination in itertools.product(
                    *(_system_spellings(syllable, system, table) for syllable in part)
                )
            ]
            for part in parts
        ]
        spellings[system] = sorted(
            " ".join(combination) for combination in itertools.product(*part_options)
        )
    return spellings


def _part_orders(parts: list[list[str]]) -> list[list[list[str]]]:
    """Original order plus surname moved to the end or to the front (FR5.2)."""
    orders = [parts]
    if len(parts) > 1:
        orders.append(parts[1:] + parts[:1])
        orders.append(parts[-1:] + parts[:-1])
    return orders


def _key_sequences(name: str, table: RomanizationTable) -> list[list[frozenset]]:
    sequences = []
    for order in _part_orders(_parse(name, table)):
        sequences.append(
            [
                table.index.get(syllable, frozenset({("unknown", syllable)}))
                for part in order
                for syllable in part
            ]
        )
    return sequences


def could_be_same_person(
    name_a: str, name_b: str, table: RomanizationTable | None = None
) -> bool:
    """Return True when two spellings could be the same person (FR5.1-FR5.4).

    Each syllable becomes the set of table rows it can stand for; unknown
    syllables only match themselves. The names match when, for some name
    order, they have the same number of syllables and every position shares
    at least one row.
    """
    if table is None:
        table = _default_table()
    sequences_a = _key_sequences(name_a, table)
    sequences_b = _key_sequences(name_b, table)
    return any(
        len(keys_a) == len(keys_b)
        and all(left & right for left, right in zip(keys_a, keys_b))
        for keys_a in sequences_a
        for keys_b in sequences_b
    )
