# SNU Edge v0.6.2

SNU Edge 0.6.2 aligns its Hangul baseline geometry with the current SNU font
family while preserving the established optical size and horizontal rhythm.

## Hangul geometry

- Every encoded Hangul syllable and Hangul Jamo receives a `+19.386` unit
  vertical shift.
- The adjustment is the reviewed Original:Appendard `2:1` baseline fit with
  full optical-size restoration.
- Hangul outline scale, width, and advance remain unchanged.
- Han, kana, Bopomofo, CJK punctuation, Montserrat Latin, figures, kerning,
  weight assignments, and native italic outlines remain unchanged.
- Automated tests cover the Hangul ranges and ensure the adjustment does not
  extend to unrelated CJK or Latin glyphs.

## Distribution

The release asset is `SNUEdge-0.6.2.zip`. Its flat archive root contains 16
static OTF files plus `LICENSE.txt`, `LICENSE-Montserrat.txt`, and
`LICENSE-NanumSquare.txt`. Proofs, source fonts, and project files are not
included.

Every font reports `Version 0.6.2` in OpenType name ID 5 and `0.602` in
`head.fontRevision`.
