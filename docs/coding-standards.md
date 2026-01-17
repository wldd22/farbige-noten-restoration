# Coding & Identifier Standards
## Scope

This document defines all identifier formats and coding conventions used
throughout this project.

These standards apply to:
- Pages
- Fonts
- Graphics
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
- Chronologically, the explanatory booklet (Erklärung des farbigen Notensystems) was published before Volume II, however, it is given Part III to maintain volume order

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
- The page number is based on the sequence of pages as scanned, not the printed pagination

See: [Page Types](docs/page-types.md)

---

## Font Identifiers

**Format**
```
FN-F-##

##: Two-digit sequential font index
```

Example: `FN-F-02`

**Notes:**
- Font indices don't necessarily follow a pattern, but are generally in the order of occurance in the work

See: [Font Catalogue](fonts/README.md)

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
