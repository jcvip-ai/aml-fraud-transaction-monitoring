# name_romanization

Standalone Python tool that relates the Wade-Giles, Hanyu Pinyin and Tongyong
Pinyin spellings of Chinese names, for sanctions-list screening. It is not
wired into Jube.Engine. Standard library only; Python 3.10+.

```python
from name_romanization import generate_variants, is_possible_match

generate_variants("HSIAO-MING CHANG")["hanyu"]  # ['xiao-ming chang', 'xiao-ming zhang']
is_possible_match("HSIAO-MING CHANG", "Zhang Xiaoming")  # True
```

## Rules

- Case, hyphens, spaces and concatenation are normalized; the Wade-Giles
  apostrophe is kept as the aspiration mark, and a missing one is ambiguous.
- Concatenated words are split once, greedily, by the longest syllable in the
  union of all three columns of `syllables.csv`.
- The surname is the first or the last word; surname and given name must match
  syllable by syllable (two syllables match when their Hanyu readings overlap).
- Words not in the table are kept as-is and must match exactly.
- A name with no given name never matches.

## Extending the table

Add a row `wade_giles,hanyu,tongyong` to `syllables.csv`. Version 1 holds only
the syllables used by the tests. Not handled yet: syllables with u-umlaut, and
two-syllable surnames written as two separate words.

## Tests

From the repository root: `python -m pytest tools/name_romanization/tests -q`
(needs pytest). The existing CI runs only the .NET tests.

## Licence

Part of Jube, licensed under the GNU Affero General Public License v3.0.
