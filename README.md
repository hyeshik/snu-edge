# SNU Edge Sans

SNU Edge Sans is a NanumSquare-derived OpenType build. The build script downloads
the NanumSquare package from Naver, discovers the required masters, applies the
project width and spacing adjustments, and generates upright and italic OTF
instances.

The italic styles keep CJK glyphs upright and apply a synthetic 10 degree slant
to non-CJK glyphs. Intermediate and heavier weights are synthesized from the
NanumSquare masters using a SeedKRex-style outline offset step derived from the
source master widths.

## Requirements

- FontForge with Python scripting support
- Python 3.10 or newer
- `make` for the convenience commands

On macOS with Homebrew:

```sh
brew install fontforge
```

## Quick Start

Build the complete family:

```sh
make build
```

The first build downloads:

```text
https://campaign.naver.com/nanumsquare_neo/download/NaverNanumSquare.zip
```

The downloaded archive is stored under `vendor/downloads/`, extracted under
`vendor/source/`, and the generated OTF files are written to `instance_otf/`.

Run the tests:

```sh
make test
```

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

The default build creates upright and italic variants for these weights:

- Thin: NanumSquare Light
- Light: NanumSquare Light plus one synthetic weight step
- Regular: NanumSquare Regular
- Medium: NanumSquare Regular plus one synthetic weight step
- SemiBold: NanumSquare Bold
- Bold: NanumSquare Bold plus one synthetic weight step
- ExtraBlack: NanumSquare ExtraBold
- Black: NanumSquare ExtraBold plus one synthetic weight step

This produces 16 OTF files in total.

## Build Details

Default geometry settings:

- Horizontal glyph scale: `0.96`
- Sidebearing spacing scale: `0.86`
- Italic slant angle for non-CJK glyphs: `10deg`

The script accepts optional style names and build flags:

```sh
fontforge -lang=py -script scripts/build_snu_edge_sans.py Regular Bold
fontforge -lang=py -script scripts/build_snu_edge_sans.py --upright-only
fontforge -lang=py -script scripts/build_snu_edge_sans.py --italic-only
```

Use an existing local source directory without downloading:

```sh
fontforge -lang=py -script scripts/build_snu_edge_sans.py \
  --source-dir path/to/NanumSquare/fonts \
  --no-download
```

Override output and transformation settings:

```sh
fontforge -lang=py -script scripts/build_snu_edge_sans.py \
  --output-dir build/otf \
  --glyph-x-scale 0.96 \
  --spacing-scale 0.86 \
  --italic-angle 10
```

The same options can be passed through `make` variables:

```sh
make package SOURCE_DIR=path/to/NanumSquare/fonts BUILD_FLAGS=--no-download
```

## GitHub Actions

The repository includes a GitHub Actions workflow at
`.github/workflows/build-package.yml`. It runs on pushes, pull requests, tag
pushes matching `v*`, and manual dispatches. The workflow installs FontForge,
runs the unit tests, builds all 16 OTF files, creates `dist/SNUEdgeSans.zip`,
verifies the package, and uploads it as a workflow artifact.

## Repository Layout

```text
.github/workflows/build-package.yml  GitHub Actions package build
LICENSE                       License notice and SIL Open Font License text
scripts/build_snu_edge_sans.py  FontForge build script
tests/                         Unit tests for pure helper logic
instance_otf/                  Generated OTF output
dist/                          Generated ZIP package
vendor/                        Downloaded and extracted source fonts
```

`instance_otf/`, `dist/`, and `vendor/` are intentionally ignored by Git.

## License

SNU Edge Sans is a Modified Version derived from NanumSquare font software
from NAVER Corporation. The generated fonts are distributed under the SIL Open
Font License, Version 1.1. See `LICENSE`.

The upstream `NaverNanumSquare.zip` archive downloaded by this project does not
currently include a standalone license file. The license notice in this
repository follows NAVER's Nanum font license page:

```text
https://help.naver.com/service/30016/contents/18088?osType=PC
```
