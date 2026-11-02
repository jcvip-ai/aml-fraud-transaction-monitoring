# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for name_romanization.

Every name in this file is fictional; no sanctions-list data is used (FR7.2, NFR4).
Run: python -m pytest tools/name_romanization/tests/test_romanization.py
"""

import pytest

from name_romanization import (
    DEFAULT_TABLE_PATH,
    could_be_same_person,
    equivalent_spellings,
    load_table,
    segment_syllables,
)

FICTIONAL_NAME = "HSIAO-MING CHANG"


def test_case_is_ignored():
    """FR2.1: upper, title and lower case are the same name."""
    variants = ["HSIAO-MING CHANG", "Hsiao-Ming Chang", "hsiao-ming chang"]
    expected = equivalent_spellings(variants[0])
    for variant in variants[1:]:
        assert equivalent_spellings(variant) == expected
        assert could_be_same_person(variants[0], variant) is True


def test_hyphenated_spaced_and_run_together_given_names_are_equal():
    """FR2.2: Hsiao-Ming, Hsiaoming and Hsiao Ming are the same given name."""
    assert segment_syllables("Hsiaoming Chang") == ["hsiao", "ming", "chang"]
    assert could_be_same_person("Hsiao-Ming Chang", "Hsiaoming Chang") is True
    assert could_be_same_person("Hsiao-Ming Chang", "Hsiao Ming Chang") is True


@pytest.mark.parametrize("blank", ["", "   ", "-", " - "])
def test_empty_input_raises_value_error(blank):
    """FR2.3: an empty (or blank) name is an error, not a non-match."""
    with pytest.raises(ValueError):
        equivalent_spellings(blank)
    with pytest.raises(ValueError):
        could_be_same_person(blank, FICTIONAL_NAME)
    with pytest.raises(ValueError):
        could_be_same_person(FICTIONAL_NAME, blank)


def test_wade_giles_apostrophe_marks_aspiration():
    """FR2.4: Ch'ang is Hanyu chang only; a typographic apostrophe counts too."""
    assert equivalent_spellings("Ch'ang")["hanyu"] == ["Chang"]
    assert equivalent_spellings("Ch\u2019ang")["hanyu"] == ["Chang"]
    assert could_be_same_person("Ch'ang Hsiao-Ming", "Chang Hsiao-Ming") is True
    assert could_be_same_person("Ch'ang Hsiao-Ming", "Zhang Hsiao-Ming") is False


def test_run_together_split_takes_longest_syllable_first():
    """FR3.1: xian stays one syllable rather than xi + an."""
    assert segment_syllables("xian") == ["xian"]
    assert segment_syllables("Hsiaoming") == ["hsiao", "ming"]


def test_unknown_syllable_is_kept_unchanged():
    """FR3.2: a syllable missing from the CSV passes through as written."""
    assert equivalent_spellings("Qwrt Chang")["hanyu"] == ["Qwrt Chang", "Qwrt Zhang"]
    assert could_be_same_person("Qwrt Chang", "QWRT Zhang") is True
    assert could_be_same_person("Qwrt Chang", "Qwrx Chang") is False


def test_equivalent_spellings_in_all_three_systems():
    """FR4.1: one name gives Wade-Giles, Hanyu and Tongyong spellings."""
    spellings = equivalent_spellings(FICTIONAL_NAME)
    assert set(spellings) == {"wade_giles", "hanyu", "tongyong"}
    assert "Hsiao-Ming Chang" in spellings["wade_giles"]
    assert "Xiao-Ming Zhang" in spellings["hanyu"]
    assert "Siao-Ming Jhang" in spellings["tongyong"]


def test_wade_giles_without_apostrophe_lists_both_readings():
    """FR4.2: CHANG may be unaspirated (zhang) or aspirated with a lost apostrophe."""
    spellings = equivalent_spellings("CHANG")
    assert spellings["hanyu"] == ["Chang", "Zhang"]
    assert spellings["wade_giles"] == ["Ch'ang", "Chang"]
    assert spellings["tongyong"] == ["Chang", "Jhang"]


@pytest.mark.parametrize(
    ("first", "second"),
    [("CHANG HSIAO-MING", "HSIAO-MING CHANG"), ("Chang Hsiao Ming", "Hsiao Ming Chang")],
)
def test_surname_first_and_last_both_match(first, second):
    """FR5.2"""
    assert could_be_same_person(first, second) is True
    assert could_be_same_person(second, first) is True


@pytest.mark.parametrize("other", ["Xiaoming Zhang", "Siao-Ming Jhang", "Xiao-Ming Chang"])
def test_spellings_that_differ_only_in_system_match(other):
    """FR5.3: HSIAO/XIAO/SIAO and CHANG/ZHANG/JHANG are the same person."""
    assert could_be_same_person("Hsiao-Ming Chang", other) is True


def test_different_names_return_false():
    """FR5.1: the answer is a plain bool."""
    assert could_be_same_person("Hsiao-Ming Chang", "Hsien Chang") is False
    assert could_be_same_person("Hsiao-Ming Chang", "Hsi-An Chang") is False


def test_case_and_hyphen_differences_do_not_change_the_result():
    """FR5.4"""
    assert could_be_same_person("HSIAO-MING CHANG", "xiaoming zhang") is True
    assert could_be_same_person("hsiao-ming ch'ang", "XIAOMING ZHANG") is False


def test_new_syllable_is_added_in_csv_only(tmp_path):
    """FR6.1, NFR5: extending the CSV extends matching without code changes."""
    extended = tmp_path / "syllables.csv"
    base = DEFAULT_TABLE_PATH.read_text(encoding="utf-8")
    extended.write_text(base + "kuo,guo,guo\n", encoding="utf-8")
    table = load_table(extended)
    assert could_be_same_person("Kuo Hsiao-Ming", "Guo Xiaoming", table=table) is True
    assert could_be_same_person("Kuo Hsiao-Ming", "Guo Xiaoming") is False
