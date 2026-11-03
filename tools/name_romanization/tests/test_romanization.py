# Copyright (C) 2022-present Jube Holdings Limited.
# This file is part of Jube(TM) software, licensed under the GNU Affero General
# Public License v3.0 or later. See <https://www.gnu.org/licenses/>.
"""pytest suite for name_romanization. Every name here is fictional."""

import pytest

from name_romanization import (
    DEFAULT_TABLE_PATH,
    SyllableTable,
    generate_variants,
    is_possible_match,
    tokenize,
)


def syllables_of(name, table=None):
    return [[token.text for token in word] for word in tokenize(name, table)]


def flat_syllables(name):
    return [text for word in syllables_of(name) for text in word]


# FR1.1
def test_case_is_ignored():
    assert generate_variants("HSIAO-MING CHANG") == generate_variants("hsiao-ming chang")
    assert is_possible_match("HSIAO-MING CHANG", "hsiao-ming chang")


# FR1.2, FR2.2
def test_hyphen_space_and_concatenation_are_equivalent():
    expected = ["hsiao", "ming", "chang"]
    assert flat_syllables("Hsiao-Ming Chang") == expected
    assert flat_syllables("Hsiao Ming Chang") == expected
    assert flat_syllables("Hsiaoming Chang") == expected
    assert is_possible_match("Hsiao Ming Chang", "Hsiaoming Chang")


# FR1.3
def test_apostrophe_is_an_aspiration_mark():
    assert syllables_of("Ch'ang Hsin") == [["ch'ang"], ["hsin"]]
    assert syllables_of("Ch\u2019ang Hsin") == [["ch'ang"], ["hsin"]]
    assert generate_variants("Ch'ang Hsin")["hanyu"] == ["chang xin"]
    assert not is_possible_match("Ch'ang Hsin", "Zhang Xin")


# FR2.1, FR2.3, FR2.4
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("hsiaoming", [["hsiao", "ming"]]),
        ("siaoming", [["siao", "ming"]]),
        ("xinli", [["xin", "li"]]),
        ("xian", [["xian"]]),
        ("xi an", [["xi"], ["an"]]),
    ],
)
def test_greedy_longest_segmentation(name, expected):
    assert syllables_of(name) == expected


# FR3.1, FR3.2, FR3.4
def test_csv_holds_the_required_rows():
    required = {
        ("hsiao", "xiao", "siao"), ("ming", "ming", "ming"), ("chang", "zhang", "jhang"),
        ("ch'ang", "chang", "chang"), ("chen", "zhen", "jhen"), ("ch'en", "chen", "chen"),
        ("hsin", "xin", "sin"), ("li", "li", "li"), ("kuo", "guo", "guo"),
        ("k'uo", "kuo", "kuo"), ("hua", "hua", "hua"), ("wei", "wei", "wei"),
        ("lin", "lin", "lin"), ("hsien", "xian", "sian"), ("hsi", "xi", "si"),
        ("an", "an", "an"),
    }
    assert required <= set(SyllableTable.from_csv().rows)


# FR3.3, NFR3
def test_table_is_extended_by_adding_a_csv_row(tmp_path):
    extended = tmp_path / "syllables.csv"
    extended.write_text(DEFAULT_TABLE_PATH.read_text(encoding="utf-8") + "t'ang,tang,tang\n", encoding="utf-8")
    table = SyllableTable.from_csv(extended)
    assert not is_possible_match("T'ang Ming", "Tang Ming")
    assert is_possible_match("T'ang Ming", "Tang Ming", table=table)


def test_csv_without_a_required_column_is_rejected(tmp_path):
    broken = tmp_path / "broken.csv"
    broken.write_text("wade_giles,hanyu\nhsiao,xiao\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tongyong"):
        SyllableTable.from_csv(broken)


# FR4.1, FR4.3, FR4.4, FR4.5, FR5.2
def test_variants_are_grouped_by_system():
    assert generate_variants("HSIAO-MING CHANG") == {
        "wade_giles": ["hsiao-ming ch'ang", "hsiao-ming chang"],
        "hanyu": ["xiao-ming chang", "xiao-ming zhang"],
        "tongyong": ["siao-ming chang", "siao-ming jhang"],
    }


# FR4.2
def test_missing_aspiration_mark_is_ambiguous():
    assert generate_variants("Chang Hsin")["hanyu"] == ["chang xin", "zhang xin"]
    assert is_possible_match("Chang Hsin", "Zhang Xin")
    assert is_possible_match("Chang Hsin", "Chang Xin")


# FR5.1, FR5.3
def test_surname_first_or_last():
    assert is_possible_match("Chang Hsiao-Ming", "Hsiao-Ming Chang")
    assert is_possible_match("Chang Hsiao Ming", "Xiao Ming Zhang")


# FR6.1
def test_match_returns_a_bool():
    assert is_possible_match("Lin Wei", "Lin Wei") is True
    assert is_possible_match("Lin Wei", "Lin Hua") is False


# FR6.2, FR6.3, FR6.4, FR8.2, FR9
@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        pytest.param("HSIAO-MING CHANG", "Zhang Xiaoming", True, id="FR9.1"),
        pytest.param("Jhang Siao-Ming", "Hsiao-Ming Chang", True, id="FR9.2"),
        pytest.param("Ch'en Hsin-Li", "XINLI CHEN", True, id="FR9.3"),
        pytest.param("Kuo Ming-Hua", "Guo Minghua", True, id="FR9.4"),
        pytest.param("Chang Hsiao-Ming", "Zhang Xiaowei", False, id="FR9.5"),
        pytest.param("Hsiao-Ming Chang", "Ming-Hsiao Chang", False, id="FR9.6"),
        pytest.param("Lin Hsiao-Ming", "Zhang Xiaoming", False, id="FR9.7"),
        pytest.param("Chang Hsiao-Ming", "Zhang Xiao", False, id="FR9.8"),
        pytest.param("Ch'en Hsin", "Zhen Xin", False, id="FR9.9"),
    ],
)
def test_acceptance_examples(first, second, expected):
    assert is_possible_match(first, second) is expected
    assert is_possible_match(second, first) is expected


# FR7.1, FR7.2
def test_unknown_word_is_kept_and_must_match_exactly():
    assert generate_variants("David Chang")["hanyu"] == ["david chang", "david zhang"]
    assert is_possible_match("DAVID Chang", "david zhang")
    assert not is_possible_match("David Chang", "Davis Zhang")


# FR7.3
def test_word_that_cannot_be_fully_segmented_is_unknown():
    assert syllables_of("Hsiaox Chang") == [["hsiaox"], ["chang"]]
    assert generate_variants("Hsiaox Chang")["tongyong"] == ["hsiaox chang", "hsiaox jhang"]


def test_name_without_given_name_never_matches():
    assert not is_possible_match("Chang", "Zhang")
    assert not is_possible_match("", "Zhang Xiaoming")
    assert generate_variants("") == {"wade_giles": [], "hanyu": [], "tongyong": []}
