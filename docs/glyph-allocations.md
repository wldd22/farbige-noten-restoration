# Glyph Allocations

> For identifier formats, see [Coding & Identifier Standards](docs/coding-standards.md)

Each font glyph receives an ID based on its position in the glyph allocation blocks specified here.

- `0000`: Space
- `0001`-`0026`: Uppercase A-Z (26 slots)
- `0027`-`0052`: Lowercase a-z (26 slots)
- `0053`-`0062`: Digits 0-9 (10 slots)
- `0063`-`0088`: Uppercase superscripts (26 slots)
- `0088`-`0113`: Lowercase superscripts (26 slots)
- `0114`-`0123`: Digits superscripts (10 slots)
- `0124`-`0149`: Uppercase subscripts (26 slots)
- `0150`-`0175`: Lowercase subscripts (26 slots)
- `0176`-`0185`: Digits subscripts (10 slots)
- `0186`-`0225`: Punctuation and common marks (40 slots)
- `0226`-`0275`: Combining marks & diacritics (50 slots)
- `0276`-`0355`: Precomposed accented letters (80 slots)
- `0356`-`0415`: Ligatures (60 slots)
- `0416`-`0465`: Math/notation symbols (50 slots)
