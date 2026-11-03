# Copyright (C) 2022-present Jube Holdings Limited.
# This file is part of Jube(TM) software, licensed under the GNU Affero General
# Public License v3.0 or later. See <https://www.gnu.org/licenses/>.
"""Equivalent spellings of Chinese names across three romanization systems.

Supported systems: Wade-Giles, Hanyu Pinyin and Tongyong Pinyin. The syllable
table lives in ``syllables.csv`` next to this file; adding a row there extends
the module without code changes (FR3.3). Standard library only (NFR1),
Python 3.10+ (NFR2).
"""

from __future__ import annotations

import csv
import functools
import itertools
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

SYSTEMS = ("wade_giles", "hanyu", "tongyong")
DEFAULT_TABLE_PATH = Path(__file__).with_name("syllables.csv")

# Typographic apostrophes are folded into ASCII "'" so that the Wade-Giles
# aspiration mark survives normalization (FR1.3).
_APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "`": "'"})


def normalize_text(text: str) -> str:
    """Lower-case, trim and unify apostrophes (FR1.1, FR1.3)."""
    return text.translate(_APOSTROPHES).strip().lower()


@dataclass(frozen=True)
class Token:
    """One recognised syllable, or one unrecognised piece kept as-is (FR7.1).

    ``readings`` maps each system to the spellings this token can stand for;
    it is ``None`` for an unrecognised piece.
    """

    text: str
    readings: dict[str, frozenset[str]] | None

    @property
    def known(self) -> bool:
        return self.readings is not None


class SyllableTable:
    """Syllable rows (Wade-Giles, Hanyu, Tongyong) and the lookups built on them."""

    def __init__(self, rows: Iterable[tuple[str, str, str]]) -> None:
        self._rows = tuple(tuple(row) for row in rows)
        index: dict[str, set[int]] = {}
        for row_number, (wade_giles, hanyu, tongyong) in enumerate(self._rows):
            # The apostrophe-less Wade-Giles form is a key too, so an omitted
            # aspiration mark reads as both aspirated and unaspirated (FR4.2).
            keys = {wade_giles, wade_giles.replace("'", ""), hanyu, tongyong}
            for key in keys:
                index.setdefault(key, set()).add(row_number)
        self._index = {key: frozenset(rows_) for key, rows_ in index.items()}
        self._longest = max((len(key) for key in self._index), default=0)

    @classmethod
    def from_csv(cls, path: str | Path | None = None) -> SyllableTable:
        """Load a table; the CSV needs the columns named in ``SYSTEMS`` (FR3.1)."""
        csv_path = Path(path) if path is not None else DEFAULT_TABLE_PATH
        with csv_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = [name for name in SYSTEMS if name not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"{csv_path}: missing column(s): {', '.join(missing)}")
            rows = []
            for line_number, record in enumerate(reader, start=2):
                values = tuple(normalize_text(record[name] or "") for name in SYSTEMS)
                if not all(values):
                    raise ValueError(f"{csv_path}:{line_number}: every column needs a value")
                rows.append(values)
        return cls(rows)

    @property
    def rows(self) -> tuple[tuple[str, ...], ...]:
        return self._rows

    @property
    def syllables(self) -> frozenset[str]:
        """Union of every spelling in every column (FR2.3)."""
        return frozenset(self._index)

    def segment(self, piece: str) -> list[str] | None:
        """Split one piece into syllables, greedy longest match from the left.

        Only one segmentation is tried and there is no backtracking (FR2.1).
        Returns ``None`` when the piece cannot be split completely (FR7.3).
        """
        syllables: list[str] = []
        position = 0
        while position < len(piece):
            for end in range(min(len(piece), position + self._longest), position, -1):
                if piece[position:end] in self._index:
                    syllables.append(piece[position:end])
                    position = end
                    break
            else:
                return None
        return syllables

    def readings(self, syllable: str) -> dict[str, frozenset[str]] | None:
        """Every reading of a syllable, per system, over all matching rows (FR4.3)."""
        rows = self._index.get(syllable)
        if rows is None:
            return None
        return {
            system: frozenset(self._rows[row][column] for row in rows)
            for column, system in enumerate(SYSTEMS)
        }


@functools.lru_cache(maxsize=1)
def default_table() -> SyllableTable:
    return SyllableTable.from_csv(DEFAULT_TABLE_PATH)


def tokenize(name: str, table: SyllableTable | None = None) -> list[list[Token]]:
    """Normalize a name into words, each a list of tokens.

    Words are separated by whitespace; inside a word, hyphen-separated pieces
    are segmented independently (FR1.2, FR2.2).
    """
    table = default_table() if table is None else table
    words: list[list[Token]] = []
    for raw_word in normalize_text(name).split():
        tokens: list[Token] = []
        for piece in raw_word.split("-"):
            if not piece:
                continue
            syllables = table.segment(piece)
            if syllables is None:
                tokens.append(Token(piece, None))
            else:
                tokens.extend(Token(text, table.readings(text)) for text in syllables)
        if tokens:
            words.append(tokens)
    return words


def generate_variants(name: str, table: SyllableTable | None = None) -> dict[str, list[str]]:
    """Equivalent spellings of ``name`` grouped by system (FR4.1).

    Every combination of every syllable reading is listed (FR4.4) in the
    input's name order (FR5.2). Output is lower case; syllables of one word are
    joined with "-", words with a space; each list is sorted and unique.
    """
    words = tokenize(name, table)
    variants: dict[str, list[str]] = {}
    for system in SYSTEMS:
        if not words:
            variants[system] = []
            continue
        per_word = []
        for tokens in words:
            options = [sorted(token.readings[system]) if token.known else [token.text] for token in tokens]
            per_word.append(["-".join(combo) for combo in itertools.product(*options)])
        variants[system] = sorted({" ".join(combo) for combo in itertools.product(*per_word)})
    return variants


def is_possible_match(first: str, second: str, table: SyllableTable | None = None) -> bool:
    """True when two spellings may name the same person (FR6.1).

    The surname is the first or the last word (FR5.1, FR5.3); surname and given
    name must align syllable by syllable, with equal counts (FR6.2, FR6.4).
    A name without a given name never matches.
    """
    table = default_table() if table is None else table
    left = tokenize(first, table)
    right = tokenize(second, table)
    if len(left) < 2 or len(right) < 2:
        return False
    return any(
        _same_syllables(left_surname, right_surname) and _same_syllables(left_given, right_given)
        for left_surname, left_given in _surname_splits(left)
        for right_surname, right_given in _surname_splits(right)
    )


def _surname_splits(words: list[list[Token]]) -> Iterator[tuple[list[Token], list[Token]]]:
    yield words[0], _flatten(words[1:])
    yield words[-1], _flatten(words[:-1])


def _flatten(words: list[list[Token]]) -> list[Token]:
    return [token for word in words for token in word]


def _same_syllables(left: list[Token], right: list[Token]) -> bool:
    return len(left) == len(right) and all(_same_token(a, b) for a, b in zip(left, right))


def _same_token(a: Token, b: Token) -> bool:
    """Syllables match when their Hanyu readings intersect (FR6.3); unrecognised
    pieces must be identical (FR7.2) and never match a recognised syllable."""
    if a.readings is not None and b.readings is not None:
        return bool(a.readings["hanyu"] & b.readings["hanyu"])
    if a.readings is None and b.readings is None:
        return a.text == b.text
    return False
