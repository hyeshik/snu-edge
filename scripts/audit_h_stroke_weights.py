#!/usr/bin/env python3
"""Match Montserrat weights to SNU Edge using the H crossbar thickness."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import freetype
import numpy as np
from PIL import Image, ImageDraw


STYLES = (
    ("Thin", 100, 285),
    ("Light", 300, 367),
    ("Regular", 400, 434),
    ("Medium", 500, 495),
    ("SemiBold", 600, 545),
    ("Bold", 700, 603),
    ("ExtraBold", 800, 652),
    ("Black", 900, 711),
)
WIDTH_SCALE = 0.86
CHARACTER = "H"


@dataclass(frozen=True)
class StrokeMeasurement:
    crossbar: float
    crossbar_span: float
    vertical_stem: float


def bitmap_array(slot: freetype.GlyphSlot) -> np.ndarray:
    """Return a FreeType grayscale bitmap without pitch padding."""

    bitmap = slot.bitmap
    if bitmap.width == 0 or bitmap.rows == 0:
        return np.zeros((0, 0), dtype=np.float64)
    pixels = np.frombuffer(bytes(bitmap.buffer), dtype=np.uint8)
    pixels = pixels.reshape(bitmap.rows, abs(bitmap.pitch))[:, : bitmap.width]
    if bitmap.pitch < 0:
        pixels = pixels[::-1]
    return pixels.astype(np.float64) / 255


def render_character(face: freetype.Face, ppem: int) -> tuple[np.ndarray, int]:
    face.set_pixel_sizes(0, ppem)
    flags = (
        freetype.FT_LOAD_RENDER
        | freetype.FT_LOAD_NO_HINTING
        | freetype.FT_LOAD_NO_BITMAP
    )
    face.load_char(CHARACTER, flags)
    return bitmap_array(face.glyph), face.glyph.bitmap_top


def measure_h(alpha: np.ndarray) -> StrokeMeasurement:
    """Measure H in pixels from alpha coverage.

    The center fifth of H contains ink only in the crossbar. Summed alpha gives
    a subpixel-equivalent vertical thickness. A row halfway between the cap top
    and crossbar measures the left vertical stem independently.
    """

    if alpha.size == 0:
        raise ValueError("cannot measure an empty glyph bitmap")

    occupied = np.argwhere(alpha > 0)
    top, left = occupied.min(axis=0)
    bottom, right = occupied.max(axis=0)
    glyph = alpha[top : bottom + 1, left : right + 1]
    width = glyph.shape[1]
    band_left = round(width * 0.4)
    band_right = max(band_left + 1, round(width * 0.6))
    crossbar_profile = glyph[:, band_left:band_right].mean(axis=1)
    crossbar = float(crossbar_profile.sum())
    crossbar_rows = np.flatnonzero(crossbar_profile >= 0.5)
    if crossbar_rows.size == 0:
        raise ValueError("could not locate the H crossbar")
    crossbar_span = float(crossbar_rows[-1] - crossbar_rows[0] + 1)

    upper_counter_row = max(0, int(crossbar_rows[0] // 2))
    left_half = glyph[upper_counter_row, : width // 2]
    vertical_stem = float(left_half.sum())
    return StrokeMeasurement(crossbar, crossbar_span, vertical_stem)


def measure_face(face: freetype.Face, ppem: int) -> StrokeMeasurement:
    alpha, _ = render_character(face, ppem)
    measured = measure_h(alpha)
    scale = 1000 / ppem
    return StrokeMeasurement(
        crossbar=measured.crossbar * scale,
        crossbar_span=measured.crossbar_span * scale,
        vertical_stem=measured.vertical_stem * scale,
    )


def variable_measurement(
    face: freetype.Face,
    weight: int,
    ppem: int,
) -> StrokeMeasurement:
    face.set_var_design_coords([weight])
    return measure_face(face, ppem)


def closest_weight(
    measurements: dict[int, StrokeMeasurement],
    target: float,
) -> int:
    return min(
        measurements,
        key=lambda weight: (abs(measurements[weight].crossbar - target), weight),
    )


def find_matching_weight(
    measurement_at,
    target: float,
    *,
    minimum: int = 100,
    maximum: int = 900,
) -> int:
    """Find the nearest integer weight for a monotonic crossbar measurement."""

    low = minimum
    high = maximum
    while low + 1 < high:
        middle = (low + high) // 2
        if measurement_at(middle).crossbar < target:
            low = middle
        else:
            high = middle
    candidates = {
        weight: measurement_at(weight)
        for weight in range(max(minimum, low - 2), min(maximum, high + 2) + 1)
    }
    return closest_weight(candidates, target)


def resized_width(alpha: np.ndarray, width_scale: float) -> np.ndarray:
    image = Image.fromarray(np.rint(alpha * 255).astype(np.uint8), mode="L")
    width = max(1, round(image.width * width_scale))
    return np.asarray(image.resize((width, image.height), Image.Resampling.LANCZOS))


def glyph_for_panel(
    face: freetype.Face,
    ppem: int,
    *,
    width_scale: float = 1,
) -> tuple[np.ndarray, int, StrokeMeasurement]:
    alpha, bitmap_top = render_character(face, ppem)
    measurement = measure_h(alpha)
    pixels = np.rint(alpha * 255).astype(np.uint8)
    if width_scale != 1:
        pixels = resized_width(alpha, width_scale)
    return pixels, bitmap_top, measurement


def paste_glyph(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    alpha: np.ndarray,
    bitmap_top: int,
    box: tuple[int, int, int, int],
) -> None:
    x0, y0, x1, y1 = box
    baseline = y1 - 24
    x = round((x0 + x1 - alpha.shape[1]) / 2)
    y = baseline - bitmap_top
    ink = Image.new("RGB", (alpha.shape[1], alpha.shape[0]), "#181a1f")
    mask = Image.fromarray(alpha, mode="L")
    canvas.paste(ink, (x, y), mask)

    occupied = np.argwhere(alpha > 0)
    trim_top = int(occupied[:, 0].min())
    glyph = alpha[trim_top : int(occupied[:, 0].max()) + 1]
    width = glyph.shape[1]
    band = glyph[:, round(width * 0.4) : max(round(width * 0.4) + 1, round(width * 0.6))]
    rows = np.flatnonzero(band.mean(axis=1) >= 127.5)
    bar_top = y + trim_top + int(rows[0])
    bar_bottom = y + trim_top + int(rows[-1])
    bracket_x = min(x1 - 14, x + alpha.shape[1] + 18)
    draw.line((bracket_x, bar_top, bracket_x, bar_bottom), fill="#e04b3f", width=3)
    draw.line((bracket_x - 8, bar_top, bracket_x + 8, bar_top), fill="#e04b3f", width=3)
    draw.line((bracket_x - 8, bar_bottom, bracket_x + 8, bar_bottom), fill="#e04b3f", width=3)


def draw_style_strip(
    destination: Path,
    record: dict,
    edge_dir: Path,
    montserrat_path: Path,
    *,
    italic: bool,
) -> None:
    canvas = Image.new("RGB", (1800, 760), "white")
    draw = ImageDraw.Draw(canvas)
    draw.line((0, 724, 1800, 724), fill="#d9dce1", width=2)
    draw.line((600, 0, 600, 760), fill="#eef0f3", width=2)
    draw.line((1200, 0, 1200, 760), fill="#eef0f3", width=2)

    edge_suffix = "Italic" if italic else ""
    edge_face = freetype.Face(
        str(edge_dir / f"SNUEdge-{record['style']}{edge_suffix}.otf")
    )
    montserrat_face = freetype.Face(str(montserrat_path))
    columns = (
        (edge_face, None, 1.0),
        (montserrat_face, record["current"]["weight"], WIDTH_SCALE),
        (montserrat_face, record["match"]["weight"], WIDTH_SCALE),
    )
    for column_index, (face, weight, scale) in enumerate(columns):
        if weight is not None:
            face.set_var_design_coords([weight])
        alpha, bitmap_top, _ = glyph_for_panel(face, 650, width_scale=scale)
        paste_glyph(
            canvas,
            draw,
            alpha,
            bitmap_top,
            (column_index * 600, 0, (column_index + 1) * 600, 724),
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, optimize=True)


def build_posture_report(
    edge_dir: Path,
    montserrat_path: Path,
    *,
    ppem: int,
    italic: bool,
) -> list[dict]:
    montserrat_face = freetype.Face(str(montserrat_path))
    montserrat_measurements: dict[int, StrokeMeasurement] = {}

    def measurement_at(weight: int) -> StrokeMeasurement:
        measured = montserrat_measurements.get(weight)
        if measured is None:
            measured = variable_measurement(montserrat_face, weight, ppem)
            montserrat_measurements[weight] = measured
        return measured

    styles = []
    for style, edge_weight, current_weight in STYLES:
        edge_suffix = "Italic" if italic else ""
        posture = "italic" if italic else "upright"
        edge_path = edge_dir / f"SNUEdge-{style}{edge_suffix}.otf"
        edge_measurement = measure_face(freetype.Face(str(edge_path)), ppem)
        match_weight = find_matching_weight(measurement_at, edge_measurement.crossbar)
        current = measurement_at(current_weight)
        match = measurement_at(match_weight)
        styles.append(
            {
                "style": style,
                "edge_weight": edge_weight,
                "posture": posture,
                "image": (
                    f"generated/h-stroke-weight-audit-"
                    f"{style.lower()}-{posture}.png"
                ),
                "edge": asdict(edge_measurement),
                "current": {
                    "weight": current_weight,
                    **asdict(current),
                    "crossbar_error": current.crossbar - edge_measurement.crossbar,
                    "vertical_stem_at_86": current.vertical_stem * WIDTH_SCALE,
                    "vertical_stem_error": current.vertical_stem * WIDTH_SCALE
                    - edge_measurement.vertical_stem,
                },
                "match": {
                    "weight": match_weight,
                    **asdict(match),
                    "crossbar_error": match.crossbar - edge_measurement.crossbar,
                    "vertical_stem_at_86": match.vertical_stem * WIDTH_SCALE,
                    "vertical_stem_error": match.vertical_stem * WIDTH_SCALE
                    - edge_measurement.vertical_stem,
                    "vertical_match_width_scale": (
                        edge_measurement.vertical_stem / match.vertical_stem
                    ),
                },
            }
        )
    return styles


def build_report(
    edge_dir: Path,
    montserrat_path: Path,
    montserrat_italic_path: Path,
    *,
    ppem: int,
) -> dict:
    upright = build_posture_report(
        edge_dir,
        montserrat_path,
        ppem=ppem,
        italic=False,
    )
    italic = build_posture_report(
        edge_dir,
        montserrat_italic_path,
        ppem=ppem,
        italic=True,
    )
    styles = [
        {**upright_record, "italic": italic_record}
        for upright_record, italic_record in zip(upright, italic, strict=True)
    ]
    return {
        "settings": {
            "character": CHARACTER,
            "measurement_ppem": ppem,
            "hinting": False,
            "montserrat_width_scale": WIDTH_SCALE,
            "criterion": "vertical thickness of the center H crossbar",
            "secondary_metric": "vertical stem thickness after 86% horizontal scaling",
        },
        "styles": styles,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edge-dir", default="instance_otf")
    parser.add_argument(
        "--montserrat",
        default="vendor/montserrat/Montserrat-VariableFont_wght.ttf",
    )
    parser.add_argument(
        "--montserrat-italic",
        default="vendor/montserrat/Montserrat-Italic-VariableFont_wght.ttf",
    )
    parser.add_argument(
        "--output",
        default="proof/generated/h-stroke-weight-audit.json",
    )
    parser.add_argument(
        "--image-prefix",
        default="proof/generated/h-stroke-weight-audit",
    )
    parser.add_argument("--ppem", type=int, default=2000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    edge_dir = Path(args.edge_dir)
    montserrat_path = Path(args.montserrat)
    montserrat_italic_path = Path(args.montserrat_italic)
    report = build_report(
        edge_dir,
        montserrat_path,
        montserrat_italic_path,
        ppem=args.ppem,
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    prefix = Path(args.image_prefix)
    for record in report["styles"]:
        draw_style_strip(
            prefix.with_name(
                prefix.name + f"-{record['style'].lower()}-upright.png"
            ),
            record,
            edge_dir,
            montserrat_path,
            italic=False,
        )
        draw_style_strip(
            prefix.with_name(
                prefix.name + f"-{record['style'].lower()}-italic.png"
            ),
            record["italic"],
            edge_dir,
            montserrat_italic_path,
            italic=True,
        )


if __name__ == "__main__":
    main()
