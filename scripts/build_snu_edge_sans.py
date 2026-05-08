#!/usr/bin/env fontforge -lang=py -script
from __future__ import annotations

import argparse
import contextlib
import math
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable, Iterator, NamedTuple


FAMILY_NAME = "SNU Edge Sans"
POSTSCRIPT_FAMILY_NAME = "SNUEdgeSans"
VERSION = "001.000"
DEFAULT_SOURCE_ZIP_URL = (
    "https://campaign.naver.com/nanumsquare_neo/download/NaverNanumSquare.zip"
)
DEFAULT_DOWNLOAD_DIR = "vendor/downloads"
DEFAULT_SOURCE_DIR = "vendor/source"
DEFAULT_OUTPUT_DIR = "instance_otf"
DEFAULT_GLYPH_X_SCALE = 0.96
DEFAULT_SPACING_SCALE = 0.86
DEFAULT_ITALIC_ANGLE = 10.0
SYNTHETIC_WEIGHT_REFERENCE_CODEPOINT = 0x49
MASTER_LABELS = ("Light", "Regular", "Bold", "ExtraBold")
FONT_SUFFIXES = {".otf", ".ttf", ".ttc"}


class StyleSpec(NamedTuple):
    style: str
    weight: int
    source_label: str
    synthetic_weight_steps: int = 0


class AdjustedMetrics(NamedTuple):
    advance_width: int
    left_side_bearing: float
    right_side_bearing: float
    outline_width: float


STYLE_SPECS = (
    StyleSpec("Thin", 100, "Light"),
    StyleSpec("Light", 300, "Light", 1),
    StyleSpec("Regular", 400, "Regular"),
    StyleSpec("Medium", 500, "Regular", 1),
    StyleSpec("SemiBold", 600, "Bold"),
    StyleSpec("Bold", 700, "Bold", 1),
    StyleSpec("ExtraBlack", 800, "ExtraBold"),
    StyleSpec("Black", 900, "ExtraBold", 1),
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


def should_slant_codepoint(codepoint: int) -> bool:
    return codepoint >= 0 and not is_cjk_codepoint(codepoint)


def italic_slope(angle: float = DEFAULT_ITALIC_ANGLE) -> float:
    return math.tan(math.radians(angle))


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
    parser = argparse.ArgumentParser(description="Build SNU Edge Sans from NanumSquare.")
    parser.add_argument(
        "styles",
        nargs="*",
        help=(
            "Optional subset of styles: Thin Light Regular Medium SemiBold Bold "
            "ExtraBlack Black"
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
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument(
        "--glyph-x-scale",
        type=float,
        default=DEFAULT_GLYPH_X_SCALE,
        help="Horizontal outline scale for every encoded NanumSquare glyph.",
    )
    parser.add_argument(
        "--spacing-scale",
        type=float,
        default=DEFAULT_SPACING_SCALE,
        help="Sidebearing scale for every encoded NanumSquare glyph.",
    )
    parser.add_argument(
        "--italic-angle",
        type=float,
        default=DEFAULT_ITALIC_ANGLE,
        help="Synthetic slant angle for non-CJK glyphs in italic variants.",
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


def adjust_encoded_glyphs(font, x_scale: float, spacing_scale: float) -> int:
    changed = 0
    for glyph in list(font.glyphs()):
        if glyph.unicode >= 0 and adjust_glyph(glyph, x_scale, spacing_scale):
            changed += 1
    return changed


def apply_synthetic_weight(font, offset_width: int, quiet: bool) -> int:
    if not offset_width:
        return 0

    changed = 0
    with suppress_c_stderr(quiet):
        for glyph in list(font.glyphs()):
            if glyph.unicode >= 0:
                if glyph.references:
                    glyph.unlinkRef()
                glyph.changeWeight(offset_width, "auto", 0, 0, "auto")
                changed += 1
    return changed


def slant_non_cjk_glyphs(font, angle: float) -> tuple[int, int]:
    slope = italic_slope(angle)
    slanted = 0
    upright = 0
    for glyph in list(font.glyphs()):
        codepoint = glyph.unicode
        if not should_slant_codepoint(codepoint):
            upright += 1
            continue
        if glyph.references:
            glyph.unlinkRef()
        glyph.transform((1, 0, slope, 1, 0, 0))
        slanted += 1
    return slanted, upright


def remove_unencoded_glyphs(font) -> int:
    removed = 0
    for glyph in list(font.glyphs()):
        if glyph.unicode < 0 and glyph.glyphname != ".notdef":
            font.removeGlyph(glyph)
            removed += 1
    return removed


def rewrite_metadata(font, spec: StyleSpec, italic: bool, italic_angle: float) -> None:
    output_style = style_name(spec.style, italic)
    full_name = f"{FAMILY_NAME} {output_style}"
    ps_name = f"{POSTSCRIPT_FAMILY_NAME}-{postscript_style_name(spec.style, italic)}"

    font.familyname = FAMILY_NAME
    font.fullname = full_name
    font.fontname = ps_name
    font.weight = "Normal" if spec.style == "Regular" else spec.style
    font.version = VERSION
    font.copyright = "SNU Edge Sans is a derivative build from NanumSquare."
    font.italicangle = italic_angle if italic else 0
    font.os2_weight = spec.weight
    font.os2_width = 5
    font.os2_vendor = "SNUE"
    font.os2_stylemap = (1 if italic else 0) | (32 if spec.weight >= 700 else 0)
    if not italic and spec.weight == 400:
        font.os2_stylemap = 64

    font.sfnt_names = (
        (
            "English (US)",
            "Copyright",
            "SNU Edge Sans is a derivative build from NanumSquare.",
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
            "NanumSquare names belong to their respective owners.",
        ),
        (
            "English (US)",
            "Manufacturer",
            "Seoul National University Edge derivative build",
        ),
        ("English (US)", "Preferred Family", FAMILY_NAME),
        ("English (US)", "Preferred Styles", output_style),
        ("English (US)", "Compatible Full", full_name),
    )


def output_path_for(output_dir: Path, spec: StyleSpec, italic: bool) -> Path:
    return output_dir / (
        f"{POSTSCRIPT_FAMILY_NAME}-{postscript_style_name(spec.style, italic)}.otf"
    )


def build_variant(fontforge, args, masters: dict[str, Path], spec: StyleSpec, italic: bool) -> Path:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    quiet = not args.verbose_fontforge
    font = open_source_font(fontforge, masters[spec.source_label], quiet)

    try:
        flattened = flatten_cid_font(font, quiet)
        synthetic_offset_width = spec.synthetic_weight_steps * args.synthetic_weight_width
        synthetic_changed = apply_synthetic_weight(
            font,
            synthetic_offset_width,
            quiet,
        )
        adjusted = adjust_encoded_glyphs(
            font,
            x_scale=args.glyph_x_scale,
            spacing_scale=args.spacing_scale,
        )
        slanted, upright = slant_non_cjk_glyphs(font, args.italic_angle) if italic else (0, 0)
        removed_unencoded = remove_unencoded_glyphs(font)
        italic_angle = -args.italic_angle if italic else 0
        rewrite_metadata(font, spec, italic, italic_angle)

        output_path = output_path_for(output_dir, spec, italic)
        with suppress_c_stderr(quiet):
            validation_state = font.validate()
        with suppress_c_stderr(quiet):
            font.generate(str(output_path))
        print(
            f"{output_path}: glyphs_adjusted={adjusted}, "
            f"synthetic_weighted={synthetic_changed}, "
            f"synthetic_offset_width={synthetic_offset_width}, "
            f"unencoded_removed={removed_unencoded}, "
            f"italic_slanted={slanted}, italic_upright={upright}, "
            f"glyph_x_scale={args.glyph_x_scale:.4f}, "
            f"spacing_scale={args.spacing_scale:.4f}, "
            f"cid_flattened={flattened}, validate=0x{validation_state:x}"
        )
        return output_path
    finally:
        font.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        import fontforge
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Run this script with FontForge: "
            "fontforge -lang=py -script scripts/build_snu_edge_sans.py"
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
