# SNU Edge

SNU Edge combines NanumSquare CJK glyphs with Montserrat non-CJK glyphs in
one OpenType family. A fresh build downloads and verifies both upstream sources,
selects the measured Montserrat weight for each SNU Edge style, applies the
chosen geometry and proportional spacing model, and generates upright and
italic OTF instances. Italic styles use Montserrat true italics while keeping
NanumSquare CJK glyphs upright. Synthetic intermediate weight steps are applied
only to the NanumSquare CJK glyphs.

## Requirements

- FontForge with Python scripting support
- fontTools for OpenType inspection and the italic Latin-to-Hangul GPOS guard
- freetype-py, NumPy, Pillow, and uharfbuzz for the raster audits
- Python 3.10 or newer
- `make` for the convenience commands
- Typst 0.15 or newer for the Montserrat comparison proof

On macOS with Homebrew:

```sh
brew install fontforge
python3 -m pip install --requirement requirements.txt
```

## Quick Start

Build the complete family:

```sh
make build
```

The first build downloads the NanumSquare archive from NAVER and the pinned
Montserrat 9.000 variable fonts plus OFL license from Google Fonts. SHA-256
verification is required for every Montserrat input. Cached sources live under
`vendor/`, and the generated OTF files are written to `instance_otf/`.

Run the tests:

```sh
make test
```

## Montserrat Comparison Proof

The proof targets Montserrat 9.000. Fetch its two variable fonts and OFL license
from the pinned Google Fonts sources with:

```sh
make montserrat
```

The downloader verifies every file with SHA-256 and stores the inputs under
`vendor/montserrat/`. A valid cached file is reused; a missing or invalid file
is downloaded and verified before it replaces the cache. The proof and audit
targets run this step automatically, so a fresh checkout does not need a local
Montserrat installation or committed font binaries.

Build the current SNU Edge family and compile the Typst proof:

```sh
make proof
```

Build the long-form proof using the selected round-density weights, New B
vertical geometry, and proportional `q 0.90` spacing:

```sh
make long-proof
```

This writes `proof/SNUEdge-Montserrat-LongText-Proof.pdf`.

The proof is written to:

```text
proof/SNUEdge-Montserrat-Proof.pdf
```

It contains the measured weight candidates for all eight upright and italic
styles, a complete `84/86/88%` width by `-10/0/+10` tracking matrix, and
natural mixed-script paragraphs comparing the proof-only SNU Edge v1 reference
with raw and adjusted Montserrat proposals. Later sections cover small sizes,
figures, the discarded additive tracking control, proportional-spacing
candidates, and complete Regular pair matrices.

`make proof` builds the historical v1 family under `proof/generated/v1_otf`
with the non-conflicting family name `SNU Edge v1 Reference`. It is used only
for comparison and is never included in the production package.

### Raster H Weight Audit

Generate the H-stroke report and large raster comparison strips with:

```sh
make weight-audit
```

The audit renders the proof-only SNU Edge v1 reference and pinned Montserrat
without hinting at 2000 ppem. It records the H crossbar match used during weight
selection and the independent 86% vertical-stem check:

```text
proof/generated/h-stroke-weight-audit.json
proof/generated/h-stroke-weight-audit-*.png
```

### Montserrat Spacing Audit

Generate the machine-readable spacing report independently with:

```sh
make spacing-audit
```

The audit rasterizes a 99-character core repertoire, shapes every pair at all
eight selected weights in upright and italic, and writes 153,384 screened cases
to:

```text
proof/generated/montserrat-spacing-audit.json
```

Montserrat's default `kern` feature resolves to PairPos lookups, so its numeric
pair positioning is context-independent after glyph substitution. The discarded
additive control in the Typst design proof follows this rule:

```text
edge_gap = 0.86 * native_gap - 5
```

The proof also shows the selected proportional model. It separates the glyph
outline's contour recession from the nominal pair gap and scales only the
sidebearings plus native kerning:

```text
edge_gap = 0.86 * (contour_recession + q * bbox_gap)
bbox_gap = RSB(left) + LSB(right) + native_kern
```

The selected proportional model is part of the production font build.
Montserrat outlines are scaled to 86% width; sidebearings and native kerning are
scaled by `0.86 * 0.90 = 0.774`. The original Montserrat GPOS/GSUB tables and
transformed mark anchors are retained, so ligatures, combining-mark attachment,
and native pair kerning remain available in the packaged OTFs.

### Italic Latin-to-Hangul Guard

Every italic build automatically appends a non-breaking optical guard for a
terminal Montserrat letter followed by an upright Hangul glyph. It measures the
letter overhang and Hangul left sidebearing, then adds a positive `XAdvance`
lookup to each `kern` feature. Defaults use a 20-unit minimum guard, 30-unit
target ink clearance, and 5-unit buckets at UPM 1000. It does not insert a
space character. Applications that split Latin and Hangul into separate shaping
runs may still need an equivalent typesetting boundary rule.

Build a ZIP package containing the generated OTF files, `README.md`, and
`LICENSE`:

```sh
make package
```

Remove generated fonts and downloaded source files:

```sh
make clean
```

## Generated Styles

The default build creates upright and italic variants with these CJK and Latin
weight sources:

- Thin: NanumSquare Light; Montserrat 285
- Light: NanumSquare Light plus one CJK synthetic step; Montserrat 355
- Regular: NanumSquare Regular; Montserrat 420
- Medium: NanumSquare Regular plus one CJK synthetic step; Montserrat 475
- SemiBold: NanumSquare Bold; Montserrat 535
- Bold: NanumSquare Bold plus one CJK synthetic step; Montserrat 585
- ExtraBlack: NanumSquare ExtraBold; Montserrat 645
- Black: NanumSquare ExtraBold plus one CJK synthetic step; Montserrat 690

This produces 16 OTF files in total.

## Build Details

Default CJK geometry settings:

- NanumSquare horizontal outline scale: `0.96`
- NanumSquare sidebearing scale: `0.86`

Default Montserrat settings selected by the proofs and raster audits:

- Horizontal outline scale: `0.86`
- Proportional sidebearing and kerning ratio: `q 0.90`
- Effective horizontal spacing scale: `0.774`
- Vertical outline and anchor scale: `1.028`
- Vertical shift: `-26` font units
- Posture: native Montserrat true italic

NanumSquare non-CJK glyphs are removed before merging, so the former lowercase
`e` synthetic-weight exception is obsolete and has been removed.

The proof-only v1 reference builder retains that exception solely to reproduce
the historical Light glyph faithfully.

The script accepts optional style names and build flags:

```sh
fontforge -lang=py -script scripts/build_snu_edge.py Regular Bold
fontforge -lang=py -script scripts/build_snu_edge.py --upright-only
fontforge -lang=py -script scripts/build_snu_edge.py --italic-only
```

Use an existing local source directory without downloading:

```sh
fontforge -lang=py -script scripts/build_snu_edge.py \
  --source-dir path/to/NanumSquare/fonts \
  --no-download
```

Override output and transformation settings:

```sh
fontforge -lang=py -script scripts/build_snu_edge.py \
  --montserrat-dir vendor/montserrat \
  --output-dir build/otf \
  --cjk-glyph-x-scale 0.96 \
  --cjk-spacing-scale 0.86 \
  --latin-glyph-x-scale 0.86 \
  --latin-spacing-ratio 0.90 \
  --latin-y-scale 1.028 \
  --latin-y-shift -26
```

The same options can be passed through `make` variables:

```sh
make package SOURCE_DIR=path/to/NanumSquare/fonts BUILD_FLAGS=--no-download
```

## GitHub Actions

The repository includes a GitHub Actions workflow at
`.github/workflows/build-package.yml`. It runs on pushes, pull requests, tag
pushes matching `v*`, and manual dispatches. The workflow installs FontForge,
runs the unit tests, builds all 16 OTF files, creates `dist/SNUEdge.zip`,
verifies the package, and uploads it as a workflow artifact. When the workflow
is triggered by a tag matching `v*`, it also publishes a GitHub Release and
attaches `SNUEdge.zip` as a release asset.

Create and push a release tag:

```sh
git tag v0.1.0
git push origin v0.1.0
```

Reusing an existing release tag is intentionally treated as an error. Use a new
version tag for each published package.

## Repository Layout

```text
.github/workflows/build-package.yml  GitHub Actions package build
LICENSE                       License notice and SIL Open Font License text
scripts/build_snu_edge.py  FontForge build script
scripts/build_v1_reference.py  Proof-only historical v1 family builder
scripts/fetch_montserrat.py  Pinned Montserrat downloader and verifier
scripts/add_italic_cjk_guard.py  Reusable italic Latin-to-Hangul guard logic
scripts/finalize_snu_edge.py  Production kerning and italic guard finalizer
scripts/verify_snu_edge.py  Complete production family verifier
scripts/audit_h_stroke_weights.py  Raster H crossbar weight audit generator
scripts/audit_montserrat_spacing.py  Full pair-spacing audit generator
tests/                         Unit tests for pure helper logic
proof/montserrat-proof.typ     Typst source for Montserrat comparison proof
instance_otf/                  Generated OTF output
dist/                          Generated ZIP package
vendor/                        Downloaded and extracted source fonts
```

`instance_otf/`, `dist/`, `vendor/`, and generated proof artifacts are
intentionally ignored by Git.

## License

SNU Edge is a Modified Version derived from NanumSquare font software from
NAVER Corporation and Montserrat font software from the Montserrat Project
Authors. The generated fonts are distributed under the SIL Open Font License,
Version 1.1. See `LICENSE`.

The upstream `NaverNanumSquare.zip` archive downloaded by this project does not
currently include a standalone license file. The license notice in this
repository follows NAVER's Nanum font license page:

```text
https://help.naver.com/service/30016/contents/18088?osType=PC
```
