#!/usr/bin/env python3
"""Audit Montserrat pair spacing after the SNU Edge affine transform."""

from __future__ import annotations

import argparse
import json
import unicodedata
from collections import Counter
from pathlib import Path

import freetype
import numpy as np
import uharfbuzz as hb
from fontTools.ttLib import TTFont


STYLES = (
    ("Thin", 285),
    ("Light", 367),
    ("Regular", 434),
    ("Medium", 495),
    ("SemiBold", 545),
    ("Bold", 603),
    ("ExtraBold", 652),
    ("Black", 711),
)

LOWER = "abcdefghijklmnopqrstuvwxyz"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
FIGURES = "0123456789"
PUNCTUATION = ".,:;!?\"'‘’“”-/–—()[]{}@#%&+*=<>_₩$€£¥"
LAYOUT_CHARACTERS = LOWER + UPPER + FIGURES + ".,:;!?-/()%"
COMMON_PAIRS = tuple(
    "th he in er an re on at en nd ti es or te of ed is it al ar st to nt ng "
    "se ha as ou io le ve co me de hi ri ro ic ne ea ra ce li ch ll be ma si "
    "om ur gh hr tr ai ni sc du pu ut tp ph et ug".split()
)
LIGATURE_PROBES = ("ff", "fi", "fl", "ffi", "ffl")
PROOF_WORDS = (
    "asset dataset research service baseline",
    "through throughput three chrome shrink",
    "high light right weight might",
    "language training inference minimum annual inline",
    "algorithm illustration variable waveform layout typography",
    "office affine profile difficult efficient",
    "GPU API HTTP SNU EDGE",
    "fY f¥ fV fT KY KA Kx £A kA Ax AX KV Qj XA VY YV",
)
PROOF_PAIRS = {
    word[index : index + 2]
    for line in PROOF_WORDS
    for word in line.split()
    for index in range(len(word) - 1)
}


def transformed_gap(native_gap: float, width: float, tracking: float) -> float:
    """Return the final horizontal gap in post-transform font units."""

    return width * native_gap + tracking


def proportionally_spaced_gap(
    native_gap: float,
    bbox_gap: float,
    width: float,
    spacing_scale: float,
) -> float:
    """Scale sidebearings and native kerning without scaling contour recessions."""

    contour_recession = native_gap - bbox_gap
    return width * (contour_recession + spacing_scale * bbox_gap)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    return float(np.quantile(np.asarray(values, dtype=float), fraction))


def kern_lookup_types(font: TTFont) -> list[int]:
    table = font["GPOS"].table
    lookup_indices: set[int] = set()
    for record in table.FeatureList.FeatureRecord:
        if record.FeatureTag == "kern":
            lookup_indices.update(record.Feature.LookupListIndex)

    types: set[int] = set()
    for index in lookup_indices:
        lookup = table.LookupList.Lookup[index]
        if lookup.LookupType == 9:
            types.update(subtable.ExtensionLookupType for subtable in lookup.SubTable)
        else:
            types.add(lookup.LookupType)
    return sorted(types)


class FontAudit:
    def __init__(
        self,
        path: Path,
        weight: int,
        *,
        width: float,
        tracking: float,
        spacing_scale: float,
        ppem: int,
    ) -> None:
        self.path = path
        self.weight = weight
        self.width = width
        self.tracking = tracking
        self.spacing_scale = spacing_scale
        self.tracking_before_scale = tracking / width
        self.ppem = ppem

        self.face = freetype.Face(str(path))
        self.face.set_var_design_coords([weight])
        self.face.set_pixel_sizes(0, ppem)

        data = path.read_bytes()
        self.hb_face = hb.Face(hb.Blob(data))
        self.hb_font = hb.Font(self.hb_face)
        self.hb_font.scale = (ppem, ppem)
        self.hb_font.set_variations({"wght": weight})
        self.glyph_order = TTFont(path).getGlyphOrder()
        self.profiles: dict[int, dict[int, tuple[int, int]]] = {}
        self.advances: dict[str, int] = {}

    def shape(self, text: str, *, kern: bool, liga: bool) -> tuple[list, list]:
        buffer = hb.Buffer()
        buffer.add_str(text)
        buffer.guess_segment_properties()
        hb.shape(self.hb_font, buffer, {"kern": kern, "liga": liga})
        return buffer.glyph_infos, buffer.glyph_positions

    def profile(self, glyph_id: int) -> dict[int, tuple[int, int]]:
        cached = self.profiles.get(glyph_id)
        if cached is not None:
            return cached

        flags = (
            freetype.FT_LOAD_RENDER
            | freetype.FT_LOAD_NO_HINTING
            | freetype.FT_LOAD_NO_BITMAP
        )
        self.face.load_glyph(glyph_id, flags)
        bitmap = self.face.glyph.bitmap
        if bitmap.width == 0 or bitmap.rows == 0:
            self.profiles[glyph_id] = {}
            return {}

        pixels = np.frombuffer(bytes(bitmap.buffer), dtype=np.uint8)
        pixels = pixels.reshape(bitmap.rows, bitmap.pitch)[:, : bitmap.width]
        ink = pixels >= 128
        rows: dict[int, tuple[int, int]] = {}
        for bitmap_y in range(bitmap.rows):
            xs = np.flatnonzero(ink[bitmap_y])
            if xs.size:
                y = bitmap_y - self.face.glyph.bitmap_top
                rows[y] = (
                    int(xs[0] + self.face.glyph.bitmap_left),
                    int(xs[-1] + self.face.glyph.bitmap_left),
                )
        self.profiles[glyph_id] = rows
        return rows

    def advance(self, character: str) -> int:
        cached = self.advances.get(character)
        if cached is not None:
            return cached
        infos, positions = self.shape(character, kern=False, liga=False)
        if len(infos) != 1:
            raise ValueError(f"expected one glyph for {character!r}")
        self.advances[character] = positions[0].x_advance
        return positions[0].x_advance

    def pair(self, text: str) -> dict | None:
        infos, positions = self.shape(text, kern=True, liga=False)
        if len(infos) != 2:
            return None

        left_profile = self.profile(infos[0].codepoint)
        right_profile = self.profile(infos[1].codepoint)
        shared_rows = sorted(left_profile.keys() & right_profile.keys())
        if not shared_rows:
            return None

        second_origin = positions[0].x_advance + positions[1].x_offset
        raw_second_origin = self.advance(text[0])
        left_ink_right = max(right for _, right in left_profile.values())
        right_ink_left = min(left for left, _ in right_profile.values())
        bbox_gap_pixels = second_origin + right_ink_left - left_ink_right
        native_pixels = np.fromiter(
            (
                second_origin + right_profile[y][0] - left_profile[y][1]
                for y in shared_rows
            ),
            dtype=np.float64,
            count=len(shared_rows),
        )
        q25_index = (len(native_pixels) - 1) // 4
        median_index = (len(native_pixels) - 1) // 2
        partitioned = np.partition(native_pixels, (q25_index, median_index))
        unit_scale = 1000 / self.ppem
        native = {
            "minimum": float(native_pixels.min() * unit_scale),
            "q25": float(partitioned[q25_index] * unit_scale),
            "median": float(partitioned[median_index] * unit_scale),
        }
        bbox_gap = float(bbox_gap_pixels * unit_scale)
        additive = {
            key: transformed_gap(value, self.width, self.tracking)
            for key, value in native.items()
        }
        proportional = {
            key: proportionally_spaced_gap(
                value,
                bbox_gap,
                self.width,
                self.spacing_scale,
            )
            for key, value in native.items()
        }
        return {
            "pair": text,
            "glyphs": [
                self.glyph_order[infos[0].codepoint],
                self.glyph_order[infos[1].codepoint],
            ],
            "kern": (second_origin - raw_second_origin) * unit_scale,
            "bbox_gap": bbox_gap,
            "native": native,
            "additive": additive,
            "proportional": proportional,
        }

    def ligatures(self) -> list[dict]:
        results = []
        for probe in LIGATURE_PROBES:
            infos, _ = self.shape(probe, kern=True, liga=True)
            results.append(
                {
                    "text": probe,
                    "glyphs": [self.glyph_order[info.codepoint] for info in infos],
                    "substituted": len(infos) < len(probe),
                }
            )
        return results


def category_name(character: str) -> str:
    if character in LOWER:
        return "lower"
    if character in UPPER:
        return "upper"
    if character in FIGURES:
        return "figure"
    return "punctuation"


def summarize_pairs(pairs: list[dict], limit: int) -> dict:
    additive_ordered = sorted(pairs, key=lambda pair: pair["additive"]["q25"])
    proportional_ordered = sorted(
        pairs,
        key=lambda pair: pair["proportional"]["q25"],
    )
    return {
        "count": len(pairs),
        "additive_q25_distribution": {
            "minimum": additive_ordered[0]["additive"]["q25"],
            "p05": percentile(
                [pair["additive"]["q25"] for pair in pairs],
                0.05,
            ),
            "median": percentile(
                [pair["additive"]["q25"] for pair in pairs],
                0.5,
            ),
            "p95": percentile(
                [pair["additive"]["q25"] for pair in pairs],
                0.95,
            ),
            "maximum": additive_ordered[-1]["additive"]["q25"],
        },
        "proportional_q25_distribution": {
            "minimum": proportional_ordered[0]["proportional"]["q25"],
            "p05": percentile(
                [pair["proportional"]["q25"] for pair in pairs],
                0.05,
            ),
            "median": percentile(
                [pair["proportional"]["q25"] for pair in pairs],
                0.5,
            ),
            "p95": percentile(
                [pair["proportional"]["q25"] for pair in pairs],
                0.95,
            ),
            "maximum": proportional_ordered[-1]["proportional"]["q25"],
        },
        "additive_tightest": additive_ordered[:limit],
        "additive_loosest": list(reversed(additive_ordered[-limit:])),
        "proportional_tightest": proportional_ordered[:limit],
        "proportional_loosest": list(reversed(proportional_ordered[-limit:])),
    }


def cmap_coverage(font: TTFont, audited_characters: set[str]) -> dict:
    cmap = font.getBestCmap()
    category_counts = Counter(unicodedata.category(chr(codepoint)) for codepoint in cmap)
    spacing_characters = {
        chr(codepoint)
        for codepoint in cmap
        if unicodedata.category(chr(codepoint))[0] in {"L", "N", "P", "S"}
    }
    decomposition_roots = {
        next(
            (
                item
                for item in unicodedata.normalize("NFD", character)
                if unicodedata.category(item)[0] != "M"
            ),
            character,
        )
        for character in spacing_characters
    }
    return {
        "cmap_characters": len(cmap),
        "spacing_characters": len(spacing_characters),
        "decomposition_roots": len(decomposition_roots),
        "audited_characters": len(audited_characters),
        "category_counts": dict(sorted(category_counts.items())),
        "unaudited_spacing_characters": len(spacing_characters - audited_characters),
    }


def audit_style(
    font_path: Path,
    style_name: str,
    weight: int,
    posture: str,
    characters: str,
    *,
    width: float,
    tracking: float,
    spacing_scale: float,
    ppem: int,
    limit: int,
) -> dict:
    audit = FontAudit(
        font_path,
        weight,
        width=width,
        tracking=tracking,
        spacing_scale=spacing_scale,
        ppem=ppem,
    )
    pairs = []
    by_category: dict[str, list[dict]] = {}
    pair_map: dict[str, dict] = {}
    for left in characters:
        for right in characters:
            pair = audit.pair(left + right)
            if pair is None:
                continue
            pairs.append(pair)
            pair_map[left + right] = pair
            category = category_name(left) + "-" + category_name(right)
            by_category.setdefault(category, []).append(pair)

    additive_clearance = sorted(pairs, key=lambda pair: pair["additive"]["minimum"])
    proportional_clearance = sorted(
        pairs,
        key=lambda pair: pair["proportional"]["minimum"],
    )

    return {
        "style": style_name,
        "weight": weight,
        "posture": posture,
        "pairs_screened": len(pairs),
        "ligatures": audit.ligatures(),
        "common_pairs": [pair_map[pair] for pair in COMMON_PAIRS if pair in pair_map],
        "proof_pairs": [pair_map[pair] for pair in sorted(PROOF_PAIRS) if pair in pair_map],
        "layout_pairs": {
            pair: {
                "kern": pair_map[pair]["kern"],
                "bbox_gap": pair_map[pair]["bbox_gap"],
            }
            for pair in sorted(pair_map)
            if pair[0] in LAYOUT_CHARACTERS and pair[1] in LAYOUT_CHARACTERS
        },
        "matrix_pairs": (
            [
                pair_map[pair]
                for pair in sorted(pair_map)
                if (pair[0] in LOWER and pair[1] in LOWER)
                or (pair[0] in UPPER and pair[1] in UPPER)
            ]
            if style_name == "Regular"
            else []
        ),
        "horizontal_profile_clearance": {
            "additive_tightest": additive_clearance[:limit],
            "proportional_tightest": proportional_clearance[:limit],
        },
        "categories": {
            category: summarize_pairs(category_pairs, limit)
            for category, category_pairs in sorted(by_category.items())
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--font-dir", type=Path, default=Path("vendor/montserrat")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("proof/generated/montserrat-spacing-audit.json"),
    )
    parser.add_argument("--width", type=float, default=0.86)
    parser.add_argument("--tracking", type=float, default=-5.0)
    parser.add_argument("--spacing-scale", type=float, default=0.90)
    parser.add_argument("--ppem", type=int, default=500)
    parser.add_argument("--extreme-limit", type=int, default=12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    upright = args.font_dir / "Montserrat-VariableFont_wght.ttf"
    italic = args.font_dir / "Montserrat-Italic-VariableFont_wght.ttf"
    for path in (upright, italic):
        if not path.is_file():
            raise SystemExit(f"missing font: {path}")

    source_font = TTFont(upright)
    characters = "".join(dict.fromkeys(LOWER + UPPER + FIGURES + PUNCTUATION))
    available = source_font.getBestCmap()
    characters = "".join(character for character in characters if ord(character) in available)
    lookup_types = kern_lookup_types(source_font)

    styles = []
    for style_name, weight in STYLES:
        styles.append(
            audit_style(
                upright,
                style_name,
                weight,
                "upright",
                characters,
                width=args.width,
                tracking=args.tracking,
                spacing_scale=args.spacing_scale,
                ppem=args.ppem,
                limit=args.extreme_limit,
            )
        )
        styles.append(
            audit_style(
                italic,
                style_name,
                weight,
                "italic",
                characters,
                width=args.width,
                tracking=args.tracking,
                spacing_scale=args.spacing_scale,
                ppem=args.ppem,
                limit=args.extreme_limit,
            )
        )

    report = {
        "schema": 1,
        "settings": {
            "width": args.width,
            "tracking": args.tracking,
            "spacing_scale": args.spacing_scale,
            "ppem": args.ppem,
            "audited_characters": characters,
            "additive_rule": "additive_gap = width * native_gap + tracking",
            "proportional_rule": (
                "proportional_gap = width * "
                "(contour_recession + spacing_scale * bbox_gap)"
            ),
        },
        "layout": {
            "kern_lookup_types": lookup_types,
            "pair_positioning_only": lookup_types == [2],
            "context_note": (
                "Default kern positioning is pair-local. GSUB ligatures and mark positioning "
                "remain separate context-sensitive cases."
            ),
        },
        "coverage": cmap_coverage(source_font, set(characters)),
        "styles": styles,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        f"wrote {args.output}: {len(styles)} style/posture runs, "
        f"{sum(style['pairs_screened'] for style in styles)} pairs"
    )


if __name__ == "__main__":
    main()
