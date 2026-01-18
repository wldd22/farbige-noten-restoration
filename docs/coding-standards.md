# Coding & Identifier Standards
## Scope

This document defines all identifier formats and coding conventions used
throughout this project.

These standards apply to:
- Pages
- Fonts
- Graphics
- Layouts
- Metadata references
- Filenames (where applicable)

All identifiers defined here are **stable** and **never renamed**.

---

## Project Prefix

All identifiers begin with: `FN`, representing *Farbige Noten*.

---

## Part Codes

| Code | Description                    |
| ---- | ------------------------------ |
| `P1` | Part I (Volume I)              |
| `P2` | Part II (Volume II)            |
| `P3` | Part III (Explanatory booklet) |

**Notes:**
- Chronologically, the explanatory booklet (Erklärung des farbigen Notensystems) was published before Volume II, however, it is assigned Part III to maintain volume order

---

## Page Identifiers

**Format**
```
FN-PG-P#-##

P#: Part number (P1, P2, or P3)
##: Two-digit sequential page number
```

```
For page ranges:
FN-PG-P#-(## | ##-##)(, ## | ##-##)*(, P#-##(, ## | ##-##)*)*

P#: Part number (P1, P2, or P3)
##: Two-digit sequential page number
##-##: Inclusive page range within the same part

VALID:
FN-PG-P1-01
FN-PG-P1-03-05
FN-PG-P1-01, 03-05, 07
FN-PG-P1-01, P2-04
FN-PG-P1-01-03, 05, P2-07, 09-11, P3-02

INVALID:
FN-PG-01
FN-PG-P1-1
FN-PG-P1-01-03-05
FN-PG-P1-01, P1-03
FN-PG-P1-01, P2
```

Example: `FN-PG-P1-12`

**Notes:**
- The page number is based on the sequence of pages as scanned, not any printed pagination

See: [Page Types](docs/page-types.md)

---

## Transcription Identifiers

**Format**
```
FN-TR-P#-##

P#: Part number (P1, P2, or P3)
##: Two-digit sequential page number
```

Example: `FN-TR-P1-12`

**Notes:**
- Not all page numbers have a corresponding transcription. Pages with only graphics don't contain body text and so, don't have a transcription.

---

## Translation Identifiers

**Format**
```
FN-TL-P#-##-XX

P#: Part number (P1, P2, or P3)
##: Two-digit sequential page number
XX: Two-character language (ISO 639-1)
```

Example: `FN-TL-P1-12-EN`

**Notes:**
- Not all page numbers have a corresponding transcription. Pages with only graphics don't contain body text and so, don't have a transcription.

---

## Font Identifiers

**Format**
```
FN-F-##

##: Two-digit sequential font index
```

Example: `FN-F-02`

**Notes:**
- Font indices don't necessarily follow a pattern, but are generally in order of appearance

See: [Font Catalogue](fonts/README.md)

---

## Font Glyph Identifiers

**Format**
```
FN-FG-##-####

##: Two-digit sequential font index
####: Four-digit glyph ID
```

Example: `FN-FG-02-053`

**Notes:**
- Glyph ID is based on the [Glyph Allocations](docs/glyph-allocations.md).

---

## Graphic Identifiers

**Format**
```
FN-GR-XX-##

XX: Two-character graphic type
##: Two-digit sequential graphic index
```

Example: `FN-GR-OR-02`

**Notes:**
- Graphic indices don't necessarily follow a pattern, but are generally sorted and grouped in order of appearance
- Type codes are defined in [Graphic Types](docs/graphic-types.md)

See: [Graphic Catalogue](graphics/README.md)

---

## Layout Identifiers

**Format**
```
FN-L-##

##: Two-digit sequential layout index
```

Example: `FN-L-03`

**Notes:**
- Layout indices don't necessarily follow a pattern, but are generally in order of appearance

See: [Layout Catalogue](layouts/README.md)
