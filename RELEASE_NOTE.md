# SNU Edge v0.6.1

SNU Edge 0.6.1 strengthens copyright and SIL Open Font License metadata without
changing glyph outlines, metrics, kerning, weight assignments, or family names.

## Copyright and license changes

- The main license now identifies Hyeshik Chang's modifications alongside the
  preserved NAVER and Montserrat copyright statements.
- Every OTF carries NAVER's complete Nanum Reserved Font Name declaration, the
  Montserrat copyright, and the modification copyright in OpenType name ID 0.
- OpenType name ID 13 records the SIL Open Font License 1.1 and the complete
  NAVER RFN list. Name ID 14 links to the official OFL site.
- `OS/2.fsType` is normalized from the upstream value to `0` so the fonts
  advertise installable embedding consistently with the OFL.
- The production verifier and unit tests require the RFN declaration in
  copyright and license metadata while rejecting `Nanum` from all user-facing
  SNU Edge primary names.

The family remains `SNU Edge` / `SNUEdge`; upstream font names appear only in
copyright, license, attribution, and source documentation contexts.

## Distribution

The release asset is `SNUEdge-0.6.1.zip`. Its flat archive root contains 16
static OTF files plus `LICENSE.txt`, `LICENSE-Montserrat.txt`, and
`LICENSE-NanumSquare.txt`. Proofs, source fonts, and project files are not
included.

Every font reports `Version 0.6.1` in OpenType name ID 5 and `0.601` in
`head.fontRevision`.
