#!/usr/bin/env fontforge -lang=py -script
from __future__ import annotations

import argparse
import contextlib
import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable, Iterator, NamedTuple

FAMILY_NAME = "SNU Edge"
POSTSCRIPT_FAMILY_NAME = "SNUEdge"
VERSION = "0.6.1"
DEFAULT_SOURCE_ZIP_URL = (
    "https://campaign.naver.com/nanumsquare_neo/download/NaverNanumSquare.zip"
)
DEFAULT_DOWNLOAD_DIR = "vendor/downloads"
DEFAULT_SOURCE_DIR = "vendor/source"
DEFAULT_MONTSERRAT_DIR = "vendor/montserrat"
DEFAULT_OUTPUT_DIR = "instance_otf"
DEFAULT_CJK_GLYPH_X_SCALE = 0.96
DEFAULT_CJK_SPACING_SCALE = 0.86
DEFAULT_HANGUL_Y_SCALE = 1.0
DEFAULT_HANGUL_Y_SHIFT = 19.38596491228069
DEFAULT_LATIN_GLYPH_X_SCALE = 0.92
DEFAULT_LATIN_SPACING_RATIO = 0.88
DEFAULT_LATIN_Y_SCALE = 1.028
DEFAULT_LATIN_Y_SHIFT = -26
MONTSERRAT_UPRIGHT_FILENAME = "Montserrat-VariableFont_wght.ttf"
MONTSERRAT_ITALIC_FILENAME = "Montserrat-Italic-VariableFont_wght.ttf"
SYNTHETIC_WEIGHT_REFERENCE_CODEPOINT = 0x49
MASTER_LABELS = ("Light", "Regular", "Bold", "ExtraBold")
FONT_SUFFIXES = {".otf", ".ttf", ".ttc"}
FIGURE_NAMES = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
)
TABULAR_FIGURE_NAMES = tuple(f"{name}.tf" for name in FIGURE_NAMES) + tuple(
    f"{name}.tosf" for name in FIGURE_NAMES
)
MODERN_HANGUL_RANGE = (0xAC00, 0xD7A3)

NANUM_RESERVED_FONT_NAMES = (
    "Nanum, Naver Nanum, NanumGothic, Naver NanumGothic, NanumMyeongjo, "
    "Naver NanumMyeongjo, NanumBrush, Naver NanumBrush, NanumPen, "
    "Naver NanumPen, NanumGothicEco, NanumGothicEco, "
    "Naver NanumMyeongjoEco, NanumMyeongjoEco, Naver NanumGothicLight, "
    "NanumGothicLight, NanumBarunGothic, Naver NanumBarunGothic, "
    "NanumSquareRound, NanumBarunPen, MaruBuri, NanumSquareNeo"
)
NANUM_COPYRIGHT_RFN = (
    "Copyright (c) 2010, NAVER Corporation (https://www.navercorp.com/) "
    f"with Reserved Font Name {NANUM_RESERVED_FONT_NAMES}."
)
MONTSERRAT_COPYRIGHT = (
    "Copyright 2024 The Montserrat.Git Project Authors "
    "(https://github.com/JulietaUla/Montserrat.git)."
)
DERIVATIVE_COPYRIGHT = "Copyright (c) 2026 Hyeshik Chang (modifications)."
COPYRIGHT_TEXT = " ".join(
    (NANUM_COPYRIGHT_RFN, MONTSERRAT_COPYRIGHT, DERIVATIVE_COPYRIGHT)
)
LICENSE_DESCRIPTION = (
    "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
    f"Reserved Font Names declared by NAVER: {NANUM_RESERVED_FONT_NAMES}."
)
LICENSE_URL = "https://openfontlicense.org"


def font_revision(version: str = VERSION) -> float:
    parts = version.split(".")
    if len(parts) not in (2, 3):
        raise ValueError(f"Expected a major.minor[.patch] version: {version}")
    major, minor = int(parts[0]), int(parts[1])
    patch = int(parts[2]) if len(parts) == 3 else 0
    if not 0 <= minor < 10 or not 0 <= patch < 100:
        raise ValueError(
            f"Version {version} cannot be mapped to a unique head.fontRevision; "
            "pick a wider encoding before releasing it."
        )
    return round(major + minor / 10 + patch / 1000, 6)

# These punctuation marks and symbols rely on roundness, equal dimensions, or
# rotational symmetry. Scale them isotropically with the selected vertical
# geometry instead of applying the condensed Latin-text width. Percent, per
# mille, and at signs intentionally remain part of the condensed text system.
ASPECT_PRESERVING_CODEPOINTS = frozenset(
    {
        0x002A,  # ASTERISK
        0x002B,  # PLUS SIGN
        0x002C,  # COMMA
        0x002E,  # FULL STOP
        0x003A,  # COLON
        0x003B,  # SEMICOLON
        0x003C,  # LESS-THAN SIGN
        0x003D,  # EQUALS SIGN
        0x003E,  # GREATER-THAN SIGN
        0x00A4,  # CURRENCY SIGN
        0x00A8,  # DIAERESIS
        0x00A9,  # COPYRIGHT SIGN
        0x00AE,  # REGISTERED SIGN
        0x00B0,  # DEGREE SIGN
        0x00B1,  # PLUS-MINUS SIGN
        0x00B7,  # MIDDLE DOT
        0x00D7,  # MULTIPLICATION SIGN
        0x00F7,  # DIVISION SIGN
        0x02D9,  # DOT ABOVE
        0x02DA,  # RING ABOVE
        0x2022,  # BULLET
        0x2026,  # HORIZONTAL ELLIPSIS
        0x212E,  # ESTIMATED SYMBOL
        0x2190,  # LEFTWARDS ARROW
        0x2191,  # UPWARDS ARROW
        0x2192,  # RIGHTWARDS ARROW
        0x2193,  # DOWNWARDS ARROW
        0x2194,  # LEFT RIGHT ARROW
        0x2195,  # UP DOWN ARROW
        0x2196,  # NORTH WEST ARROW
        0x2197,  # NORTH EAST ARROW
        0x2198,  # SOUTH EAST ARROW
        0x2199,  # SOUTH WEST ARROW
        0x2205,  # EMPTY SET
        0x2206,  # INCREMENT
        0x2219,  # BULLET OPERATOR
        0x221E,  # INFINITY
        0x2248,  # ALMOST EQUAL TO
        0x2260,  # NOT EQUAL TO
        0x2264,  # LESS-THAN OR EQUAL TO
        0x2265,  # GREATER-THAN OR EQUAL TO
        0x24B6,  # CIRCLED LATIN CAPITAL LETTER A
        0x24D0,  # CIRCLED LATIN SMALL LETTER A
        0x25A0,  # BLACK SQUARE
        0x25A1,  # WHITE SQUARE
        0x25B2,  # BLACK UP-POINTING TRIANGLE
        0x25B3,  # WHITE UP-POINTING TRIANGLE
        0x25B6,  # BLACK RIGHT-POINTING TRIANGLE
        0x25B7,  # WHITE RIGHT-POINTING TRIANGLE
        0x25BC,  # BLACK DOWN-POINTING TRIANGLE
        0x25BD,  # WHITE DOWN-POINTING TRIANGLE
        0x25C0,  # BLACK LEFT-POINTING TRIANGLE
        0x25C1,  # WHITE LEFT-POINTING TRIANGLE
        0x25C6,  # BLACK DIAMOND
        0x25C7,  # WHITE DIAMOND
        0x25CA,  # LOZENGE
        0x25CC,  # DOTTED CIRCLE
        0xA789,  # MODIFIER LETTER COLON
    }
)
ASPECT_PRESERVING_GLYPH_NAMES = frozenset(
    {
        "arrowdown.case",
        "arrowleft.case",
        "arrowright.case",
        "arrowup.case",
        "bullet.case",
        "period.sc",
        "periodcentered.case",
        "periodcentered.loclCAT",
        "periodcentered.loclCAT.case",
        "uni24B6.ss01",
        "uni24D0.ss01",
    }
)

class StyleSpec(NamedTuple):
    style: str
    weight: int
    source_label: str
    latin_weight: int
    synthetic_weight_steps: int = 0

class AdjustedMetrics(NamedTuple):
    advance_width: int
    left_side_bearing: float
    right_side_bearing: float
    outline_width: float

STYLE_SPECS = (
    StyleSpec("Thin", 100, "Light", 281),
    StyleSpec("Light", 300, "Light", 357, 1),
    StyleSpec("Regular", 400, "Regular", 419),
    StyleSpec("Medium", 500, "Regular", 475, 1),
    StyleSpec("SemiBold", 600, "Bold", 522),
    StyleSpec("Bold", 700, "Bold", 575, 1),
    StyleSpec("ExtraBold", 800, "ExtraBold", 620),
    StyleSpec("Black", 900, "ExtraBold", 675, 1),
)

CJK_CODEPOINT_RANGES = (
    (0x1100, 0x11FF),
    (0x2E80, 0x2EFF),
    (0x2F00, 0x2FDF),
    (0x3000, 0x303F),
    (0x3040, 0x309F),
    (0x30A0, 0x30FF),
    (0x3100, 0x312F),
    (0x3130, 0x318F),
    (0x31A0, 0x31BF),
    (0x31C0, 0x31EF),
    (0x31F0, 0x31FF),
    (0x3200, 0x32FF),
    (0x3300, 0x33FF),
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xA960, 0xA97F),
    (0xAC00, 0xD7AF),
    (0xD7B0, 0xD7FF),
    (0xF900, 0xFAFF),
    (0xFE30, 0xFE4F),
    (0xFF00, 0xFFEF),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F),
    (0x2B740, 0x2B81F),
    (0x2B820, 0x2CEAF),
    (0x2CEB0, 0x2EBEF),
    (0x30000, 0x3134F),
)

HANGUL_CODEPOINT_RANGES = (
    (0x1100, 0x11FF),
    (0x3130, 0x318F),
    (0xA960, 0xA97F),
    (0xAC00, 0xD7A3),
    (0xD7B0, 0xD7FF),
)

@contextlib.contextmanager
def suppress_c_stderr(enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return

    saved_stderr = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(saved_stderr, 2)
        os.close(saved_stderr)
        os.close(devnull)

def normalized_stem(path: Path) -> str:
    return (
        path.stem.lower()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace(".", "")
    )

def classify_master(path: Path) -> str | None:
    if path.suffix.lower() not in FONT_SUFFIXES:
        return None

    name = normalized_stem(path)
    if "heavy" in name or "ehv" in name:
        return None
    if "extrabold" in name or "extra" in name or "deb" in name or name.endswith("squareeb"):
        return "ExtraBold"
    if "bold" in name or "cbd" in name or name.endswith("bd") or name.endswith("b"):
        return "Bold"
    if "regular" in name or "brg" in name or name.endswith("rg") or name.endswith("r"):
        return "Regular"
    if "light" in name or "alt" in name or name.endswith("lt") or name.endswith("l"):
        return "Light"
    return None

def discover_font_files(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        return []
    return [
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in FONT_SUFFIXES
    ]

def discover_master_paths(paths: Iterable[Path]) -> dict[str, Path]:
    masters: dict[str, Path] = {}
    sorted_paths = sorted(
        paths,
        key=lambda path: (
            path.suffix.lower() != ".otf",
            "_ac" in path.stem.lower(),
            len(path.name),
            path.name,
        ),
    )
    for path in sorted_paths:
        label = classify_master(path)
        if label is not None and label not in masters:
            masters[label] = path

    missing = [label for label in MASTER_LABELS if label not in masters]
    if missing:
        raise SystemExit(
            "Missing required NanumSquare master(s): " + ", ".join(missing)
        )
    return masters

def download_zip(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination

    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, destination)
    return destination

def safe_extract_zip(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if not str(target).startswith(str(root)):
                raise SystemExit(f"Refusing unsafe zip member: {member.filename}")
        archive.extractall(destination)

def ensure_source_fonts(args: argparse.Namespace) -> dict[str, Path]:
    source_dir = Path(args.source_dir)
    source_files = discover_font_files(source_dir)
    if source_files:
        return discover_master_paths(source_files)

    if args.no_download:
        raise SystemExit(
            f"No source fonts found in {source_dir}; remove --no-download to fetch them."
        )

    archive_path = Path(args.download_dir) / "NaverNanumSquare.zip"
    download_zip(args.source_zip_url, archive_path)
    safe_extract_zip(archive_path, source_dir)
    return discover_master_paths(discover_font_files(source_dir))

def is_cjk_codepoint(codepoint: int) -> bool:
    return any(start <= codepoint <= end for start, end in CJK_CODEPOINT_RANGES)

def is_hangul_codepoint(codepoint: int) -> bool:
    return any(start <= codepoint <= end for start, end in HANGUL_CODEPOINT_RANGES)

def adjusted_glyph_metrics(
    *,
    xmin: float,
    xmax: float,
    left_side_bearing: float,
    right_side_bearing: float,
    x_scale: float,
    spacing_scale: float,
) -> AdjustedMetrics:
    outline_width = (xmax - xmin) * x_scale
    target_left = left_side_bearing * spacing_scale
    target_right = right_side_bearing * spacing_scale
    advance_width = round(outline_width + target_left + target_right)
    return AdjustedMetrics(advance_width, target_left, target_right, outline_width)

def derive_synthetic_weight_width(master_widths: list[float]) -> int:
    if len(master_widths) < 2:
        return 0
    deltas = [
        master_widths[index + 1] - master_widths[index]
        for index in range(len(master_widths) - 1)
    ]
    positive_deltas = [delta for delta in deltas if delta > 0]
    if not positive_deltas:
        return 0
    average_delta = sum(positive_deltas) / len(positive_deltas)
    return max(1, round(average_delta / 2))

def style_name(style: str, italic: bool) -> str:
    return f"{style} Italic" if italic else style

def postscript_style_name(style: str, italic: bool) -> str:
    return style_name(style, italic).replace(" ", "")

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build SNU Edge from NanumSquare CJK and Montserrat non-CJK glyphs."
    )
    parser.add_argument(
        "styles",
        nargs="*",
        help=(
            "Optional subset of styles: Thin Light Regular Medium SemiBold Bold "
            "ExtraBold Black"
        ),
    )
    italic_group = parser.add_mutually_exclusive_group()
    italic_group.add_argument(
        "--upright-only",
        action="store_true",
        help="Build only upright styles.",
    )
    italic_group.add_argument(
        "--italic-only",
        action="store_true",
        help="Build only italic styles.",
    )
    parser.add_argument(
        "--source-url",
        dest="source_zip_url",
        default=DEFAULT_SOURCE_ZIP_URL,
    )
    parser.add_argument("--download-dir", default=DEFAULT_DOWNLOAD_DIR)
    parser.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--montserrat-dir", default=DEFAULT_MONTSERRAT_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument(
        "--cjk-glyph-x-scale",
        type=float,
        default=DEFAULT_CJK_GLYPH_X_SCALE,
        help="Horizontal outline scale for NanumSquare CJK glyphs.",
    )
    parser.add_argument(
        "--cjk-spacing-scale",
        type=float,
        default=DEFAULT_CJK_SPACING_SCALE,
        help="Sidebearing scale for NanumSquare CJK glyphs.",
    )
    parser.add_argument(
        "--latin-glyph-x-scale",
        type=float,
        default=DEFAULT_LATIN_GLYPH_X_SCALE,
        help="Horizontal outline scale for Montserrat non-CJK glyphs.",
    )
    parser.add_argument(
        "--latin-spacing-ratio",
        type=float,
        default=DEFAULT_LATIN_SPACING_RATIO,
        help="Proportional multiplier for scaled Montserrat sidebearings and kerning.",
    )
    parser.add_argument(
        "--latin-y-scale",
        type=float,
        default=DEFAULT_LATIN_Y_SCALE,
        help="Vertical outline and anchor scale for Montserrat glyphs.",
    )
    parser.add_argument(
        "--latin-y-shift",
        type=float,
        default=DEFAULT_LATIN_Y_SHIFT,
        help="Vertical font-unit shift for Montserrat outlines and anchors.",
    )
    parser.add_argument(
        "--verbose-fontforge",
        action="store_true",
        help="Show FontForge warnings emitted while opening and generating.",
    )
    return parser

def selected_style_specs(style_names: list[str]) -> list[StyleSpec]:
    known = {spec.style: spec for spec in STYLE_SPECS}
    if not style_names:
        return list(STYLE_SPECS)

    unknown = sorted(set(style_names) - set(known))
    if unknown:
        raise SystemExit("Unknown styles: " + ", ".join(unknown))
    return [known[name] for name in style_names]

def open_source_font(fontforge, path: Path, quiet: bool):
    with suppress_c_stderr(quiet):
        return fontforge.open(str(path))

def flatten_cid_font(font, quiet: bool) -> bool:
    if not getattr(font, "cidfontname", None):
        return False
    with suppress_c_stderr(quiet):
        font.cidFlatten()
    return True

def glyph_outline_width(font, codepoint: int) -> float:
    for glyph in font.glyphs():
        if glyph.unicode == codepoint:
            xmin, _, xmax, _ = glyph.boundingBox()
            return xmax - xmin
    return 0

def derive_synthetic_weight_width_from_sources(
    fontforge, masters: dict[str, Path], quiet: bool
) -> int:
    widths = []
    for label in MASTER_LABELS:
        font = open_source_font(fontforge, masters[label], quiet)
        try:
            flatten_cid_font(font, quiet)
            widths.append(glyph_outline_width(font, SYNTHETIC_WEIGHT_REFERENCE_CODEPOINT))
        finally:
            font.close()
    return derive_synthetic_weight_width(widths)

def adjust_glyph(glyph, x_scale: float, spacing_scale: float) -> bool:
    xmin, _, xmax, _ = glyph.boundingBox()
    if xmax <= xmin:
        glyph.width = round(glyph.width * spacing_scale)
        return True

    metrics = adjusted_glyph_metrics(
        xmin=xmin,
        xmax=xmax,
        left_side_bearing=glyph.left_side_bearing,
        right_side_bearing=glyph.right_side_bearing,
        x_scale=x_scale,
        spacing_scale=spacing_scale,
    )

    if glyph.references:
        glyph.unlinkRef()
    glyph.transform((x_scale, 0, 0, 1, 0, 0))
    glyph.left_side_bearing = round(metrics.left_side_bearing)
    glyph.width = metrics.advance_width
    return True

def adjust_cjk_glyphs(font, x_scale: float, spacing_scale: float) -> int:
    changed = 0
    for glyph in list(font.glyphs()):
        if is_cjk_codepoint(glyph.unicode) and adjust_glyph(
            glyph, x_scale, spacing_scale
        ):
            changed += 1
    return changed

def adjust_hangul_vertical_geometry(font) -> int:
    changed = 0
    for glyph in list(font.glyphs()):
        if not is_hangul_codepoint(glyph.unicode):
            continue
        if glyph.references:
            glyph.unlinkRef()
        glyph.transform(
            (
                1,
                0,
                0,
                DEFAULT_HANGUL_Y_SCALE,
                0,
                DEFAULT_HANGUL_Y_SHIFT,
            )
        )
        changed += 1
    return changed

def apply_synthetic_weight(font, offset_width: int, quiet: bool) -> int:
    if not offset_width:
        return 0

    changed = 0
    with suppress_c_stderr(quiet):
        for glyph in list(font.glyphs()):
            if not is_cjk_codepoint(glyph.unicode):
                continue
            if glyph.references:
                glyph.unlinkRef()
            glyph.changeWeight(offset_width, "auto", 0, 0, "auto")
            changed += 1
    return changed

def remove_layout_lookups(font) -> int:
    lookup_names = list(font.gpos_lookups) + list(font.gsub_lookups)
    for lookup_name in lookup_names:
        font.removeLookup(lookup_name)
    return len(lookup_names)

def remove_non_cjk_glyphs(font) -> int:
    removed = 0
    for glyph in list(font.glyphs()):
        keep = glyph.glyphname == ".notdef" or is_cjk_codepoint(glyph.unicode)
        if not keep:
            font.removeGlyph(glyph)
            removed += 1
    return removed

def remove_empty_hangul_glyphs(font) -> int:
    removed = 0
    for glyph in list(font.glyphs()):
        if not MODERN_HANGUL_RANGE[0] <= glyph.unicode <= MODERN_HANGUL_RANGE[1]:
            continue
        if glyph.boundingBox() != (0.0, 0.0, 0.0, 0.0):
            continue
        font.removeGlyph(glyph)
        removed += 1
    return removed

def montserrat_source_path(montserrat_dir: Path, italic: bool) -> Path:
    filename = (
        MONTSERRAT_ITALIC_FILENAME if italic else MONTSERRAT_UPRIGHT_FILENAME
    )
    path = montserrat_dir / filename
    if not path.is_file():
        raise SystemExit(
            f"Missing Montserrat source: {path}; run make montserrat first."
        )
    return path

def instantiate_montserrat(source_path: Path, output_path: Path, weight: int) -> None:
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    font = TTFont(source_path)
    instantiateVariableFont(font, {"wght": weight}, inplace=True)
    font["OS/2"].usWeightClass = weight
    output_path.parent.mkdir(parents=True, exist_ok=True)
    font.save(output_path)
    font.close()

def remove_cjk_from_latin(font) -> int:
    removed = 0
    for glyph in list(font.glyphs()):
        if is_cjk_codepoint(glyph.unicode):
            font.removeGlyph(glyph)
            removed += 1
    return removed

def normalize_latin_outlines(font) -> int:
    glyphs = list(font.glyphs())

    # Decompose every composite before transforming any outline. Decomposing a
    # later composite after one of its components has already been transformed
    # would apply the affine transform to that component a second time.
    for glyph in glyphs:
        if glyph.references:
            glyph.unlinkRef()

    overlaps_removed = 0
    for glyph in glyphs:
        if not glyph.selfIntersects():
            continue
        glyph.removeOverlap()
        overlaps_removed += 1
    return overlaps_removed

def preserves_original_aspect(glyph) -> bool:
    return (
        glyph.unicode in ASPECT_PRESERVING_CODEPOINTS
        or glyph.glyphname in ASPECT_PRESERVING_GLYPH_NAMES
    )

def adjust_latin_glyph(
    glyph,
    *,
    x_scale: float,
    spacing_scale: float,
    y_scale: float,
    y_shift: float,
) -> None:
    original_width = glyph.width
    xmin, _, xmax, _ = glyph.boundingBox()
    left_side_bearing = glyph.left_side_bearing
    right_side_bearing = glyph.right_side_bearing

    glyph.transform((x_scale, 0, 0, y_scale, 0, y_shift))

    if original_width == 0:
        glyph.width = 0
        return
    if xmax <= xmin:
        glyph.width = round(original_width * spacing_scale)
        return

    metrics = adjusted_glyph_metrics(
        xmin=xmin,
        xmax=xmax,
        left_side_bearing=left_side_bearing,
        right_side_bearing=right_side_bearing,
        x_scale=x_scale,
        spacing_scale=spacing_scale,
    )
    glyph.left_side_bearing = round(metrics.left_side_bearing)
    glyph.width = metrics.advance_width

def transform_latin_font(
    font,
    *,
    x_scale: float,
    spacing_ratio: float,
    y_scale: float,
    y_shift: float,
) -> tuple[int, int, int]:
    font.reencode("unicode")
    removed_cjk = remove_cjk_from_latin(font)
    spacing_scale = x_scale * spacing_ratio
    overlaps_removed = normalize_latin_outlines(font)
    changed = 0
    for glyph in list(font.glyphs()):
        glyph_x_scale = y_scale if preserves_original_aspect(glyph) else x_scale
        adjust_latin_glyph(
            glyph,
            x_scale=glyph_x_scale,
            spacing_scale=spacing_scale,
            y_scale=y_scale,
            y_shift=y_shift,
        )
        changed += 1
    return changed, removed_cjk, overlaps_removed

def normalize_tabular_figure_widths(font) -> int:
    missing = [name for name in TABULAR_FIGURE_NAMES if name not in font]
    if missing:
        raise ValueError(
            "Montserrat input is missing tabular figures: " + ", ".join(missing)
        )

    target_width = max(round(font[name].width) for name in TABULAR_FIGURE_NAMES)
    for name in TABULAR_FIGURE_NAMES:
        glyph = font[name]
        extra_width = target_width - glyph.width
        glyph.left_side_bearing = round(glyph.left_side_bearing + extra_width / 2)
        glyph.width = target_width
    return target_width

def rewrite_metadata(font, spec: StyleSpec, italic: bool, italic_angle: float) -> None:
    output_style = style_name(spec.style, italic)
    full_name = f"{FAMILY_NAME} {output_style}"
    ps_name = f"{POSTSCRIPT_FAMILY_NAME}-{postscript_style_name(spec.style, italic)}"

    font.familyname = FAMILY_NAME
    font.fullname = full_name
    font.fontname = ps_name
    font.weight = "Normal" if spec.style == "Regular" else spec.style
    font.version = VERSION
    font.copyright = COPYRIGHT_TEXT
    font.italicangle = italic_angle if italic else 0
    font.os2_weight = spec.weight
    font.os2_width = 5
    font.os2_fstype = 0
    font.os2_vendor = "SNUE"
    font.os2_stylemap = (1 if italic else 0) | (32 if spec.weight >= 700 else 0)
    if not italic and spec.weight == 400:
        font.os2_stylemap = 64

    font.sfnt_names = (
        (
            "English (US)",
            "Copyright",
            COPYRIGHT_TEXT,
        ),
        ("English (US)", "Family", FAMILY_NAME),
        ("English (US)", "SubFamily", output_style),
        ("English (US)", "UniqueID", f"{VERSION};SNUE;{ps_name}"),
        ("English (US)", "Fullname", full_name),
        ("English (US)", "Version", f"Version {VERSION}"),
        ("English (US)", "PostScriptName", ps_name),
        (
            "English (US)",
            "Trademark",
            "NanumSquare and Montserrat names belong to their respective owners.",
        ),
        (
            "English (US)",
            "Manufacturer",
            "Seoul National University Edge derivative build",
        ),
        ("English (US)", "Preferred Family", FAMILY_NAME),
        ("English (US)", "Preferred Styles", output_style),
        ("English (US)", "Compatible Full", full_name),
        ("English (US)", "License", LICENSE_DESCRIPTION),
        ("English (US)", "License URL", LICENSE_URL),
    )

def output_path_for(output_dir: Path, spec: StyleSpec, italic: bool) -> Path:
    return output_dir / (
        f"{POSTSCRIPT_FAMILY_NAME}-{postscript_style_name(spec.style, italic)}.otf"
    )

def build_variant(
    fontforge,
    args,
    masters: dict[str, Path],
    spec: StyleSpec,
    italic: bool,
) -> Path:
    from finalize_snu_edge import finalize_font

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_path_for(output_dir, spec, italic)
    quiet = not args.verbose_fontforge

    with tempfile.TemporaryDirectory(prefix="snu-edge-build-") as temporary:
        temporary_dir = Path(temporary)
        instance_path = temporary_dir / "montserrat-instance.ttf"
        transformed_latin_path = temporary_dir / "montserrat-transformed.otf"
        raw_output_path = temporary_dir / output_path.name

        source_path = montserrat_source_path(Path(args.montserrat_dir), italic)
        instantiate_montserrat(source_path, instance_path, spec.latin_weight)
        latin = open_source_font(fontforge, instance_path, quiet)
        try:
            (
                latin_adjusted, latin_cjk_removed, latin_overlaps_removed
            ) = transform_latin_font(
                latin,
                x_scale=args.latin_glyph_x_scale,
                spacing_ratio=args.latin_spacing_ratio,
                y_scale=args.latin_y_scale,
                y_shift=args.latin_y_shift,
            )
            tabular_figure_width = normalize_tabular_figure_widths(latin)
            italic_angle = latin.italicangle if italic else 0
            with suppress_c_stderr(quiet):
                latin.generate(str(transformed_latin_path))
        finally:
            latin.close()

        font = open_source_font(fontforge, masters[spec.source_label], quiet)
        try:
            flattened = flatten_cid_font(font, quiet)
            font.reencode("unicode")
            empty_hangul_removed = remove_empty_hangul_glyphs(font)
            removed_lookups = remove_layout_lookups(font)
            synthetic_offset_width = (
                spec.synthetic_weight_steps * args.synthetic_weight_width
            )
            synthetic_changed = apply_synthetic_weight(
                font,
                synthetic_offset_width,
                quiet,
            )
            cjk_adjusted = adjust_cjk_glyphs(
                font,
                x_scale=args.cjk_glyph_x_scale,
                spacing_scale=args.cjk_spacing_scale,
            )
            hangul_adjusted = adjust_hangul_vertical_geometry(font)
            nanum_removed = remove_non_cjk_glyphs(font)
            with suppress_c_stderr(quiet):
                font.mergeFonts(str(transformed_latin_path))
            rewrite_metadata(font, spec, italic, italic_angle)

            with suppress_c_stderr(quiet):
                validation_state = font.validate()
            with suppress_c_stderr(quiet):
                font.generate(str(raw_output_path))
        finally:
            font.close()

        kern_scale = args.latin_glyph_x_scale * args.latin_spacing_ratio
        kern_lookups, kern_values, legacy_pairs, guard_stats = finalize_font(
            raw_output_path,
            output_path,
            italic=italic,
            kern_scale=kern_scale,
            revision=font_revision(),
        )

    guard_summary = "none"
    if guard_stats is not None:
        guard_summary = f"{guard_stats.guard_min}..{guard_stats.guard_max}"
    print(
        f"{output_path}: cjk_adjusted={cjk_adjusted}, "
        f"hangul_adjusted={hangul_adjusted}, "
        f"hangul_y_scale={DEFAULT_HANGUL_Y_SCALE:.4f}, "
        f"hangul_y_shift={DEFAULT_HANGUL_Y_SHIFT:.3f}, "
        f"synthetic_weighted={synthetic_changed}, "
        f"synthetic_offset_width={synthetic_offset_width}, "
        f"nanum_non_cjk_removed={nanum_removed}, "
        f"empty_hangul_removed={empty_hangul_removed}, "
        f"nanum_layout_lookups_removed={removed_lookups}, "
        f"latin_adjusted={latin_adjusted}, latin_cjk_removed={latin_cjk_removed}, "
        f"latin_overlaps_removed={latin_overlaps_removed}, "
        f"latin_weight={spec.latin_weight}, "
        f"latin_x_scale={args.latin_glyph_x_scale:.4f}, "
        f"latin_spacing_ratio={args.latin_spacing_ratio:.4f}, "
        f"latin_y_scale={args.latin_y_scale:.4f}, "
        f"latin_y_shift={args.latin_y_shift:.1f}, "
        f"tabular_figure_width={tabular_figure_width}, "
        f"kern_lookups={kern_lookups}, kern_values_scaled={kern_values}, "
        f"legacy_pairs_scaled={legacy_pairs}, italic_guard={guard_summary}, "
        f"cid_flattened={flattened}, validate=0x{validation_state:x}"
    )
    return output_path

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        import fontforge
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Run this script with FontForge: "
            "fontforge -lang=py -script scripts/build_snu_edge.py"
        ) from exc

    masters = ensure_source_fonts(args)
    specs = selected_style_specs(args.styles)
    build_upright = not args.italic_only
    build_italic = not args.upright_only
    args.synthetic_weight_width = derive_synthetic_weight_width_from_sources(
        fontforge,
        masters,
        not args.verbose_fontforge,
    )
    print(f"Derived synthetic weight offset width: {args.synthetic_weight_width}")

    built_paths = []
    for spec in specs:
        if build_upright:
            built_paths.append(build_variant(fontforge, args, masters, spec, italic=False))
        if build_italic:
            built_paths.append(build_variant(fontforge, args, masters, spec, italic=True))

    print(f"Built {len(built_paths)} font(s).")

if __name__ == "__main__":
    main()
