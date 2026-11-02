# name_romanization

A standalone Python tool (standard library only, Python 3.10+) that compares
Chinese names written in Wade-Giles, Hanyu Pinyin and Tongyong Pinyin, so that
spellings such as HSIAO/XIAO or CHANG/ZHANG are treated as possibly the same person.
It is not wired into the Jube C# engine.

## Usage

```python
from name_romanization import could_be_same_person, equivalent_spellings

equivalent_spellings("HSIAO-MING CHANG")["hanyu"]
# ['Xiao-Ming Chang', 'Xiao-Ming Zhang']
could_be_same_person("CHANG HSIAO-MING", "Xiaoming Zhang")  # True
```

Run from `tools/` (or put `tools/` on `PYTHONPATH`) so `name_romanization` is importable.

- Case, hyphens and run-together given names are normalized (Hsiao-Ming = Hsiaoming).
- Run-together names are split longest syllable first; syllables not in the table are kept unchanged.
- A Wade-Giles apostrophe (Ch'ang) marks aspiration; without it (CHANG) both readings are candidates.
- Surname-first and surname-last orders both match.
- An empty name raises `ValueError`.
- Out of scope for this version: ü spellings, compound surnames, Hanzi, other romanizations.

## Extending the syllable table

Add a row to `syllables.csv` (`wade_giles,hanyu,tongyong`, lower case). No code change is needed.
The first version only holds the syllables used by the tests and the examples.

## Tests

```
python -m pip install pytest
python -m pytest tools/name_romanization/tests/test_romanization.py
```

All example and test names are fictional.

## License

Part of Jube, licensed under AGPL-3.0 (AGPL-3.0-or-later).
