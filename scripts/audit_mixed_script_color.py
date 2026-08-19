#!/usr/bin/env python3
"""Compare Korean and Latin text color in SNU Edge and a control family.

The audit shapes the same labelled Korean/Latin runs with HarfBuzz and
rasterizes every resulting glyph with FreeType at high resolution without
hinting.  It keeps two deliberately separate measurements:

* ink density: integrated alpha coverage divided by advance width times one em
* horizontal whitespace: the share of advance columns outside glyph ink boxes

The first approximates the grey value of a long line.  The second isolates the
horizontal breathing room around glyph outlines, including real word spaces,
without treating counters inside a glyph as inter-glyph spacing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import freetype
import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
import uharfbuzz as hb


STYLES = (
    "Thin",
    "Light",
    "Regular",
    "Medium",
    "SemiBold",
    "Bold",
    "ExtraBold",
    "Black",
)
BODY_STYLES = ("Light", "Regular", "Medium")
PP_EM = 512
BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20260819

# This is the eight-paragraph mixed-script corpus from long-text-proof.typ.
# The proof adds periods during layout; they are omitted here so punctuation is
# not assigned arbitrarily to either Korean or Latin.
PARAGRAPHS = (
    (
        ("ko", "연구팀은 새로운"),
        ("latin", "language model"),
        ("ko", "을 실제 서비스에 배포하기 전에 다양한"),
        ("latin", "benchmark dataset"),
        ("ko", "으로 성능을 검증했다"),
        ("ko", "단일 점수만 비교하면 모델의 장단점을 놓치기 쉬우므로"),
        ("latin", "inference latency"),
        ("ko", "와"),
        ("latin", "token throughput"),
        ("ko", "뿐 아니라 메모리 사용량과 오류 유형도 함께 기록했다"),
    ),
    (
        ("ko", "평가 과정에서는 입력 길이와"),
        ("latin", "batch size"),
        ("ko", "를 단계적으로 바꾸면서 결과가 안정적으로 유지되는지 확인했다"),
        ("ko", "특히 긴 문서에서"),
        ("latin", "attention pattern"),
        ("ko", "이 달라지는 현상과 작은 표본에서"),
        ("latin", "error rate"),
        ("ko", "가 크게 흔들리는 현상을 분리해 분석했다"),
        ("ko", "모든 실험에는 동일한"),
        ("latin", "random seed"),
        ("ko", "와 환경 정보를 남겨 다른 연구자가 결과를 재현할 수 있도록 했다"),
    ),
    (
        ("ko", "데이터를 준비할 때에는 자동화된"),
        ("latin", "data pipeline"),
        ("ko", "만 신뢰하지 않고 원문 표본을 직접 읽었다"),
        ("ko", "정규화 단계에서 전문용어의 대소문자가 사라지거나"),
        ("latin", "version number"),
        ("ko", "가 날짜로 잘못 해석되는 사례가 있었기 때문이다"),
        ("ko", "수정된 규칙은"),
        ("latin", "unit test"),
        ("ko", "와"),
        ("latin", "regression test"),
        ("ko", "에 추가했으며 변경 전후의 통계량을 보고서에 함께 제시했다"),
    ),
    (
        ("ko", "실제 운영 환경에서는 평균 성능보다 실패가 발생하는 경계를 이해하는 일이 중요하다"),
        ("ko", "연구자는"),
        ("latin", "monitoring dashboard"),
        ("ko", "에서 지연 시간의 분포와 요청별"),
        ("latin", "GPU memory"),
        ("ko", "사용량을 관찰하고 경고 기준을 조정했다"),
        ("ko", "갑작스러운"),
        ("latin", "traffic spike"),
        ("ko", "가 발생했을 때에는 작은 모델로 요청을 전환하는"),
        ("latin", "fallback policy"),
        ("ko", "가 정상적으로 작동하는지도 점검했다"),
    ),
    (
        ("ko", "결과를 해석할 때에는 통계적으로 유의한 차이와 실제 사용자가 체감하는 차이를 구분했다"),
        ("latin", "confidence interval"),
        ("ko", "이 좁더라도 화면에서 문장이 끊기거나 응답 순서가 바뀌면 서비스 품질은 낮아질 수 있다"),
        ("ko", "따라서 정량 평가 뒤에는 연구자가 직접"),
        ("latin", "error analysis"),
        ("ko", "를 수행하고 대표 사례를 유형별로 정리했다"),
    ),
    (
        ("ko", "공동 연구를 진행할 때에는 코드와 데이터뿐 아니라 판단의 근거도 공유해야 한다"),
        ("ko", "각 실험의"),
        ("latin", "commit hash"),
        ("ko", "와 설정 파일을 기록하고 중요한 결정은 짧은"),
        ("latin", "design note"),
        ("ko", "로 남겼다"),
        ("ko", "회의에서는 최신 결과만 보여주지 않고 실패한"),
        ("latin", "baseline model"),
        ("ko", "과 중단한 접근법도 함께 검토해 같은 시행착오가 반복되지 않도록 했다"),
    ),
    (
        ("ko", "논문 초안을 작성하면서 연구팀은 그림과 표의 용어를 본문과 통일했다"),
        ("latin", "training schedule"),
        ("ko", "과"),
        ("latin", "evaluation protocol"),
        ("ko", "처럼 반복되는 표현은 처음 등장할 때 정의하고 이후에는 같은 표기를 유지했다"),
        ("ko", "독자가 결과를 빠르게 확인할 수 있도록 각 절의 첫 문장에는 핵심 주장과 적용 범위를 명확히 적었다"),
    ),
    (
        ("ko", "최종 검토에서는 작은 화면과 인쇄물에서 동일한 문단을 읽어 보았다"),
        ("ko", "화면에서는"),
        ("latin", "anti aliasing"),
        ("ko", "과 글자 간 리듬을 살피고 인쇄물에서는 획의 농도와 줄 사이의 균형을 확인했다"),
        ("ko", "한글과 영문이 연속해서 나타나는 문장에서도 어느 한쪽이 지나치게 튀지 않는지를 중심으로 판단했다"),
    ),
)


@dataclass(frozen=True)
class RunMeasurement:
    text: str
    advance_em: float
    ink_area_em2: float
    blank_width_em: float
    glyphs: int


@dataclass(frozen=True)
class GlyphRaster:
    alpha_area: float
    ink_left: float | None
    ink_right: float | None


def corpus_runs(script: str) -> list[str]:
    return [
        text
        for paragraph in PARAGRAPHS
        for run_script, text in paragraph
        if run_script == script
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bitmap_array(slot: freetype.GlyphSlot) -> np.ndarray:
    bitmap = slot.bitmap
    if bitmap.width == 0 or bitmap.rows == 0:
        return np.zeros((0, 0), dtype=np.float64)
    pixels = np.frombuffer(bytes(bitmap.buffer), dtype=np.uint8)
    pixels = pixels.reshape(bitmap.rows, abs(bitmap.pitch))[:, : bitmap.width]
    if bitmap.pitch < 0:
        pixels = pixels[::-1]
    return pixels.astype(np.float64) / 255


def union_length(intervals: list[tuple[float, float]]) -> float:
    if not intervals:
        return 0.0
    ordered = sorted(intervals)
    total = 0.0
    start, end = ordered[0]
    for next_start, next_end in ordered[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            total += end - start
            start, end = next_start, next_end
    return total + end - start


class TextMeasurer:
    def __init__(self, path: Path, ppem: int) -> None:
        self.path = path
        self.ppem = ppem
        self.ft_face = freetype.Face(str(path))
        self.ft_face.set_pixel_sizes(0, ppem)
        data = path.read_bytes()
        self.hb_face = hb.Face(hb.Blob(data))
        self.upem = self.hb_face.upem
        self.hb_font = hb.Font(self.hb_face)
        self.hb_font.scale = (self.upem, self.upem)
        self.pixel_scale = ppem / self.upem
        self.raster_cache: dict[int, GlyphRaster] = {}

    def raster(self, glyph_id: int) -> GlyphRaster:
        cached = self.raster_cache.get(glyph_id)
        if cached is not None:
            return cached
        flags = (
            freetype.FT_LOAD_RENDER
            | freetype.FT_LOAD_NO_HINTING
            | freetype.FT_LOAD_NO_BITMAP
        )
        self.ft_face.load_glyph(glyph_id, flags)
        alpha = bitmap_array(self.ft_face.glyph)
        occupied = np.argwhere(alpha >= 0.5)
        if occupied.size:
            left = float(self.ft_face.glyph.bitmap_left + occupied[:, 1].min())
            right = float(self.ft_face.glyph.bitmap_left + occupied[:, 1].max() + 1)
        else:
            left = None
            right = None
        raster = GlyphRaster(float(alpha.sum()), left, right)
        self.raster_cache[glyph_id] = raster
        return raster

    def measure(self, text: str) -> RunMeasurement:
        buffer = hb.Buffer()
        buffer.add_str(text)
        buffer.guess_segment_properties()
        hb.shape(self.hb_font, buffer, {"kern": True, "liga": True})

        cursor = 0.0
        alpha_area = 0.0
        intervals: list[tuple[float, float]] = []
        for info, position in zip(buffer.glyph_infos, buffer.glyph_positions):
            raster = self.raster(info.codepoint)
            alpha_area += raster.alpha_area
            if raster.ink_left is not None and raster.ink_right is not None:
                origin = (cursor + position.x_offset) * self.pixel_scale
                intervals.append(
                    (origin + raster.ink_left, origin + raster.ink_right)
                )
            cursor += position.x_advance

        advance_px = cursor * self.pixel_scale
        if advance_px <= 0:
            raise ValueError(f"non-positive advance for {text!r} in {self.path}")
        clipped = [
            (max(0.0, left), min(advance_px, right))
            for left, right in intervals
            if right > 0 and left < advance_px
        ]
        covered_width = union_length(clipped)
        return RunMeasurement(
            text=text,
            advance_em=cursor / self.upem,
            ink_area_em2=alpha_area / (self.ppem * self.ppem),
            blank_width_em=max(0.0, advance_px - covered_width) / self.ppem,
            glyphs=len(buffer.glyph_infos),
        )


def aggregate(runs: list[RunMeasurement]) -> dict[str, float | int]:
    advance = sum(run.advance_em for run in runs)
    ink_area = sum(run.ink_area_em2 for run in runs)
    blank_width = sum(run.blank_width_em for run in runs)
    return {
        "runs": len(runs),
        "glyphs": sum(run.glyphs for run in runs),
        "advance_em": advance,
        "ink_area_em2": ink_area,
        "ink_density": ink_area / advance,
        "horizontal_whitespace": blank_width / advance,
    }


def font_metadata(path: Path) -> dict[str, str | int]:
    font = TTFont(path, lazy=True)
    return {
        "path": str(path),
        "sha256": sha256(path),
        "units_per_em": font["head"].unitsPerEm,
    }


def analyze_font(path: Path, ppem: int) -> tuple[dict, dict[str, list[RunMeasurement]]]:
    measurer = TextMeasurer(path, ppem)
    measured_runs = {
        script: [measurer.measure(text) for text in corpus_runs(script)]
        for script in ("ko", "latin")
    }
    scripts = {script: aggregate(runs) for script, runs in measured_runs.items()}
    ko = scripts["ko"]
    latin = scripts["latin"]
    summary = {
        "scripts": scripts,
        "contrast": {
            "latin_vs_korean_density_percent": (
                (latin["ink_density"] / ko["ink_density"] - 1) * 100
            ),
            "latin_minus_korean_whitespace_points": (
                (latin["horizontal_whitespace"] - ko["horizontal_whitespace"])
                * 100
            ),
        },
    }
    return summary, measured_runs


def resampled_ratio(
    runs: list[RunMeasurement], indices: np.ndarray, attribute: str
) -> np.ndarray:
    numerator = np.asarray([getattr(run, attribute) for run in runs])
    advance = np.asarray([run.advance_em for run in runs])
    return numerator[indices].sum(axis=1) / advance[indices].sum(axis=1)


def bootstrap_comparison(
    edge_runs: dict[str, list[RunMeasurement]],
    control_runs: dict[str, list[RunMeasurement]],
    *,
    samples: int,
    seed: int,
) -> dict[str, dict[str, float]]:
    rng = np.random.default_rng(seed)
    sampled: dict[str, dict[str, np.ndarray]] = {}
    for script in ("ko", "latin"):
        count = len(edge_runs[script])
        indices = rng.integers(0, count, size=(samples, count))
        sampled[script] = {
            "edge_density": resampled_ratio(
                edge_runs[script], indices, "ink_area_em2"
            ),
            "control_density": resampled_ratio(
                control_runs[script], indices, "ink_area_em2"
            ),
            "edge_whitespace": resampled_ratio(
                edge_runs[script], indices, "blank_width_em"
            ),
            "control_whitespace": resampled_ratio(
                control_runs[script], indices, "blank_width_em"
            ),
        }

    edge_density = (
        sampled["latin"]["edge_density"] / sampled["ko"]["edge_density"] - 1
    ) * 100
    control_density = (
        sampled["latin"]["control_density"]
        / sampled["ko"]["control_density"]
        - 1
    ) * 100
    edge_whitespace = (
        sampled["latin"]["edge_whitespace"]
        - sampled["ko"]["edge_whitespace"]
    ) * 100
    control_whitespace = (
        sampled["latin"]["control_whitespace"]
        - sampled["ko"]["control_whitespace"]
    ) * 100

    def interval(values: np.ndarray) -> dict[str, float]:
        low, high = np.quantile(values, (0.025, 0.975))
        return {"low": float(low), "high": float(high)}

    return {
        "density_absolute_gap_change_percent": interval(
            np.abs(edge_density) - np.abs(control_density)
        ),
        "whitespace_absolute_gap_change_points": interval(
            np.abs(edge_whitespace) - np.abs(control_whitespace)
        ),
    }


def style_comparison(edge: dict, control: dict, bootstrap: dict) -> dict:
    edge_density = edge["contrast"]["latin_vs_korean_density_percent"]
    control_density = control["contrast"]["latin_vs_korean_density_percent"]
    edge_whitespace = edge["contrast"]["latin_minus_korean_whitespace_points"]
    control_whitespace = control["contrast"][
        "latin_minus_korean_whitespace_points"
    ]
    return {
        "edge_density_contrast_percent": edge_density,
        "control_density_contrast_percent": control_density,
        "density_absolute_gap_change_percent": abs(edge_density)
        - abs(control_density),
        "density_gap_magnification": abs(edge_density) / abs(control_density),
        "edge_whitespace_gap_points": edge_whitespace,
        "control_whitespace_gap_points": control_whitespace,
        "whitespace_absolute_gap_change_points": abs(edge_whitespace)
        - abs(control_whitespace),
        "bootstrap_95_percent_ci": bootstrap,
    }


def mean_comparison(comparisons: dict[str, dict], styles: tuple[str, ...]) -> dict:
    fields = (
        "edge_density_contrast_percent",
        "control_density_contrast_percent",
        "density_absolute_gap_change_percent",
        "edge_whitespace_gap_points",
        "control_whitespace_gap_points",
        "whitespace_absolute_gap_change_points",
    )
    result = {
        field: float(np.mean([comparisons[style][field] for style in styles]))
        for field in fields
    }
    result["density_gap_magnification"] = abs(
        result["edge_density_contrast_percent"]
    ) / abs(result["control_density_contrast_percent"])
    return result


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:+.{digits}f}"


def write_markdown(report: dict, path: Path) -> None:
    body = report["comparisons"]["body_style_mean"]
    regular = report["comparisons"]["styles"]["Regular"]
    edge_regular = report["families"]["SNU Edge"]["styles"]["Regular"]
    control_regular = report["families"]["SNU Appendard"]["styles"]["Regular"]
    lines = [
        "# SNU Edge 한·영 회색도 및 여백 감사",
        "",
        "## 결론",
        "",
        (
            "본문용 Light·Regular·Medium 평균에서 SNU Edge 영문은 한글보다 "
            f"잉크 밀도가 {abs(body['edge_density_contrast_percent']):.2f}% "
            f"{'높고' if body['edge_density_contrast_percent'] > 0 else '낮고'}, "
            f"SNU Appendard control의 차이는 "
            f"{abs(body['control_density_contrast_percent']):.2f}%이다. "
            "절대 격차는 control보다 "
            f"{abs(body['density_absolute_gap_change_percent']):.2f}%p "
            f"{'커졌다' if body['density_absolute_gap_change_percent'] > 0 else '작아졌다'}."
        ),
        "",
        (
            "수평 외곽 여백의 한·영 차이는 SNU Edge "
            f"{abs(body['edge_whitespace_gap_points']):.2f}%p, control "
            f"{abs(body['control_whitespace_gap_points']):.2f}%p로, 절대 격차가 "
            f"{abs(body['whitespace_absolute_gap_change_points']):.2f}%p "
            f"{'커졌다' if body['whitespace_absolute_gap_change_points'] > 0 else '작아졌다'}."
        ),
        "",
        "## Regular 상세",
        "",
        "| 패밀리 | 한글 잉크 밀도 | 영문 잉크 밀도 | 영문−한글 상대 밀도 | 한글 수평 여백 | 영문 수평 여백 | 여백 차이 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for family, values in (
        ("SNU Edge", edge_regular),
        ("SNU Appendard", control_regular),
    ):
        ko = values["scripts"]["ko"]
        latin = values["scripts"]["latin"]
        contrast = values["contrast"]
        lines.append(
            f"| {family} | {ko['ink_density'] * 100:.2f}% | "
            f"{latin['ink_density'] * 100:.2f}% | "
            f"{fmt(contrast['latin_vs_korean_density_percent'])}% | "
            f"{ko['horizontal_whitespace'] * 100:.2f}% | "
            f"{latin['horizontal_whitespace'] * 100:.2f}% | "
            f"{fmt(contrast['latin_minus_korean_whitespace_points'])}%p |"
        )

    lines += [
        "",
        "## 굵기별 control 비교",
        "",
        "밀도는 `영문/한글 − 1`, 여백은 `영문 − 한글`이다. "
        "`절대 격차 변화`가 양수면 SNU Edge에서 차이가 더 부각된 것이다.",
        "",
        "| 굵기 | Edge 밀도차 | Control 밀도차 | 절대 격차 변화 | Edge 여백차 | Control 여백차 | 절대 격차 변화 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for style in STYLES:
        comparison = report["comparisons"]["styles"][style]
        lines.append(
            f"| {style} | {fmt(comparison['edge_density_contrast_percent'])}% | "
            f"{fmt(comparison['control_density_contrast_percent'])}% | "
            f"{fmt(comparison['density_absolute_gap_change_percent'])}%p | "
            f"{fmt(comparison['edge_whitespace_gap_points'])}%p | "
            f"{fmt(comparison['control_whitespace_gap_points'])}%p | "
            f"{fmt(comparison['whitespace_absolute_gap_change_points'])}%p |"
        )

    density_ci = regular["bootstrap_95_percent_ci"][
        "density_absolute_gap_change_percent"
    ]
    whitespace_ci = regular["bootstrap_95_percent_ci"][
        "whitespace_absolute_gap_change_points"
    ]
    corpus = report["corpus"]
    lines += [
        "",
        "## 방법",
        "",
        (
            f"기존 장문 proof의 8개 문단, 한글 {corpus['ko']['characters_without_spaces']}자/"
            f"{corpus['ko']['runs']}구간과 영문 "
            f"{corpus['latin']['characters_without_spaces']}자/{corpus['latin']['runs']}구간을 "
            f"사용했다. FreeType {report['method']['ppem']} ppem에서 힌팅 없이 "
            "그레이스케일 rasterize하고 HarfBuzz의 기본 kerning과 ligature를 적용했다."
        ),
        "",
        "- 잉크 밀도: alpha coverage 총합 ÷ (조판 advance × 1 em). 실제 긴 줄의 회색도에 대응한다.",
        "- 수평 외곽 여백: 조판 advance 중 glyph ink bounding box가 차지하지 않는 열의 비율. 글자 내부 counter는 여백으로 세지 않으며 실제 띄어쓰기는 포함한다.",
        "- Bootstrap: 같은 구간을 두 폰트에 짝지어 10,000회 재표집했다. Regular의 control 대비 절대 밀도 격차 변화 95% 구간은 "
        f"[{density_ci['low']:+.2f}, {density_ci['high']:+.2f}]%p, 여백은 "
        f"[{whitespace_ci['low']:+.2f}, {whitespace_ci['high']:+.2f}]%p이다.",
        "- 이 값은 흰 배경·검정 글자의 기하학적 비교다. 브라우저/OS별 hinting과 gamma 차이는 별도의 화면 실험 대상이다.",
        "",
        "## 입력 파일",
        "",
    ]
    for family in ("SNU Edge", "SNU Appendard"):
        metadata = report["families"][family]["fonts"]["Regular"]
        lines.append(
            f"- {family}: `{metadata['path']}` (`sha256 {metadata['sha256']}`)"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


@dataclass(frozen=True)
class ScaledBitmapFont:
    font: ImageFont.ImageFont
    scale: int


def load_chart_font(
    size: int, bold: bool = False
) -> ImageFont.FreeTypeFont | ScaledBitmapFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates = (
        Path("/usr/share/fonts/truetype/dejavu") / name,
        Path("/usr/share/fonts/dejavu") / name,
    )
    for candidate in candidates:
        if candidate.is_file():
            try:
                return ImageFont.truetype(str(candidate), size)
            except ImportError:
                break
    # Some minimal Pillow builds omit _imagingft even though freetype-py is
    # installed for the audit.  Scale Pillow's embedded bitmap font so chart
    # generation remains an optional-dependency-free operation.
    return ScaledBitmapFont(ImageFont.load_default(), max(1, round(size / 10)))


def chart_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[float, float],
    text: str,
    *,
    fill: str,
    font: ImageFont.FreeTypeFont | ScaledBitmapFont,
    anchor: str | None = None,
) -> None:
    if not isinstance(font, ScaledBitmapFont):
        draw.text(position, text, fill=fill, font=font, anchor=anchor)
        return

    left, top, right, bottom = font.font.getbbox(text)
    width = max(1, right - left)
    height = max(1, bottom - top)
    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.text((-left, -top), text, fill=255, font=font.font)
    mask = mask.resize(
        (width * font.scale, height * font.scale), Image.Resampling.NEAREST
    )
    x, y = position
    if anchor and anchor[0] == "m":
        x -= mask.width / 2
    draw.bitmap((round(x), round(y)), mask, fill=fill)


def draw_grouped_bars(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    values: list[tuple[str, list[float], str]],
    styles: tuple[str, ...],
    suffix: str,
) -> None:
    x0, y0, x1, y1 = box
    title_font = load_chart_font(28, bold=True)
    label_font = load_chart_font(17)
    small_font = load_chart_font(14)
    chart_text(draw, (x0, y0), title, fill="#202124", font=title_font)
    plot_top = y0 + 54
    plot_bottom = y1 - 54
    plot_left = x0 + 58
    plot_right = x1 - 16
    flat = [value for _, series, _ in values for value in series]
    limit = max(1.0, max(abs(value) for value in flat) * 1.15)
    zero = (plot_top + plot_bottom) / 2

    draw.line((plot_left, zero, plot_right, zero), fill="#9aa0a6", width=2)
    chart_text(draw, (plot_left - 48, plot_top - 8), f"+{limit:.0f}{suffix}", fill="#6b7078", font=small_font)
    chart_text(draw, (plot_left - 43, zero - 8), "0", fill="#6b7078", font=small_font)
    chart_text(draw, (plot_left - 48, plot_bottom - 8), f"-{limit:.0f}{suffix}", fill="#6b7078", font=small_font)

    group_width = (plot_right - plot_left) / len(styles)
    bar_width = min(24, group_width * 0.26)
    scale = (plot_bottom - plot_top) / (2 * limit)
    for index, style in enumerate(styles):
        center = plot_left + group_width * (index + 0.5)
        for series_index, (_, series, color) in enumerate(values):
            value = series[index]
            left = center + (series_index - 1) * bar_width
            right = left + bar_width - 2
            end = zero - value * scale
            draw.rectangle((left, min(zero, end), right, max(zero, end)), fill=color)
        short = style.replace("Extra", "X").replace("Semi", "S")
        chart_text(
            draw,
            (center, plot_bottom + 12),
            short,
            fill="#4b5058",
            font=small_font,
            anchor="ma",
        )

    legend_x = plot_right - 250
    for index, (label, _, color) in enumerate(values):
        y = y0 + 7 + index * 24
        draw.rectangle((legend_x, y, legend_x + 16, y + 16), fill=color)
        chart_text(draw, (legend_x + 24, y - 3), label, fill="#4b5058", font=label_font)


def write_chart(report: dict, path: Path) -> None:
    image = Image.new("RGB", (1800, 1120), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_chart_font(44, bold=True)
    subtitle_font = load_chart_font(23)
    label_font = load_chart_font(22, bold=True)
    value_font = load_chart_font(26, bold=True)
    small_font = load_chart_font(18)
    chart_text(draw, (70, 50), "Mixed-script color audit", fill="#202124", font=title_font)
    chart_text(
        draw,
        (70, 112),
        "Same 8-paragraph Korean/Latin corpus · upright styles · high-resolution outline raster",
        fill="#62666d",
        font=subtitle_font,
    )

    comparisons = report["comparisons"]["styles"]
    edge_density = [comparisons[style]["edge_density_contrast_percent"] for style in STYLES]
    control_density = [comparisons[style]["control_density_contrast_percent"] for style in STYLES]
    edge_whitespace = [comparisons[style]["edge_whitespace_gap_points"] for style in STYLES]
    control_whitespace = [comparisons[style]["control_whitespace_gap_points"] for style in STYLES]
    draw_grouped_bars(
        draw,
        (70, 190, 875, 690),
        "Latin vs Korean ink density",
        [("SNU Edge", edge_density, "#2257c7"), ("Appendard", control_density, "#9aa0a6")],
        STYLES,
        "%",
    )
    draw_grouped_bars(
        draw,
        (925, 190, 1730, 690),
        "Latin minus Korean whitespace",
        [("SNU Edge", edge_whitespace, "#d35f32"), ("Appendard", control_whitespace, "#9aa0a6")],
        STYLES,
        "pp",
    )

    draw.rounded_rectangle((70, 750, 1730, 1040), radius=18, fill="#f7f8fa")
    chart_text(draw, (105, 785), "Regular - absolute script measurements", fill="#202124", font=label_font)
    entries = []
    for family, color in (("SNU Edge", "#2257c7"), ("SNU Appendard", "#6f747c")):
        style = report["families"][family]["styles"]["Regular"]["scripts"]
        entries.extend(
            (
                (f"{family} Korean density", style["ko"]["ink_density"] * 100, "%", color),
                (f"{family} Latin density", style["latin"]["ink_density"] * 100, "%", color),
                (f"{family} Korean space", style["ko"]["horizontal_whitespace"] * 100, "%", color),
                (f"{family} Latin space", style["latin"]["horizontal_whitespace"] * 100, "%", color),
            )
        )
    column_width = 390
    for index, (label, value, suffix, color) in enumerate(entries):
        row = index // 4
        column = index % 4
        x = 105 + column * column_width
        y = 850 + row * 90
        chart_text(draw, (x, y), label, fill="#62666d", font=small_font)
        chart_text(draw, (x, y + 30), f"{value:.2f}{suffix}", fill=color, font=value_font)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edge-dir", type=Path, default=Path("instance_otf"))
    parser.add_argument(
        "--control-dir", type=Path, default=Path("../snu-appendard/dist/otf")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--chart", type=Path)
    parser.add_argument("--ppem", type=int, default=PP_EM)
    parser.add_argument("--bootstrap-samples", type=int, default=BOOTSTRAP_SAMPLES)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    family_specs = {
        "SNU Edge": (args.edge_dir, "SNUEdge"),
        "SNU Appendard": (args.control_dir, "SNUAppendard"),
    }
    report: dict = {
        "method": {
            "ppem": args.ppem,
            "hinting": False,
            "kerning": True,
            "ligatures": True,
            "ink_density": "integrated alpha / (advance width * 1 em)",
            "horizontal_whitespace": "blank horizontal ink-bbox columns / advance width",
            "bootstrap_samples": args.bootstrap_samples,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "corpus": {},
        "families": {},
        "comparisons": {"styles": {}},
    }
    for script in ("ko", "latin"):
        runs = corpus_runs(script)
        report["corpus"][script] = {
            "paragraphs": len(PARAGRAPHS),
            "runs": len(runs),
            "characters_with_spaces": sum(len(text) for text in runs),
            "characters_without_spaces": sum(len(text.replace(" ", "")) for text in runs),
            "words": sum(len(text.split()) for text in runs),
        }

    all_runs: dict[str, dict[str, dict[str, list[RunMeasurement]]]] = {}
    for family, (directory, prefix) in family_specs.items():
        family_record = {"fonts": {}, "styles": {}}
        all_runs[family] = {}
        for style in STYLES:
            path = directory / f"{prefix}-{style}.otf"
            if not path.is_file():
                raise SystemExit(f"Missing font: {path}")
            family_record["fonts"][style] = font_metadata(path)
            summary, runs = analyze_font(path, args.ppem)
            family_record["styles"][style] = summary
            all_runs[family][style] = runs
        report["families"][family] = family_record

    for style_index, style in enumerate(STYLES):
        bootstrap = bootstrap_comparison(
            all_runs["SNU Edge"][style],
            all_runs["SNU Appendard"][style],
            samples=args.bootstrap_samples,
            seed=BOOTSTRAP_SEED + style_index,
        )
        report["comparisons"]["styles"][style] = style_comparison(
            report["families"]["SNU Edge"]["styles"][style],
            report["families"]["SNU Appendard"]["styles"][style],
            bootstrap,
        )
    report["comparisons"]["body_style_mean"] = mean_comparison(
        report["comparisons"]["styles"], BODY_STYLES
    )
    report["comparisons"]["family_mean"] = mean_comparison(
        report["comparisons"]["styles"], STYLES
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    if args.markdown:
        write_markdown(report, args.markdown)
    if args.chart:
        write_chart(report, args.chart)


if __name__ == "__main__":
    main()
