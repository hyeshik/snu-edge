#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont

from add_italic_cjk_guard import GuardStats, append_guard_lookup


DEFAULT_KERN_SCALE = 0.86 * 0.90
HORIZONTAL_VALUE_FIELDS = ("XPlacement", "XAdvance")


def scale_value_record(value, factor: float) -> int:
    if value is None:
        return 0

    changed = 0
    for field in HORIZONTAL_VALUE_FIELDS:
        amount = getattr(value, field, None)
        if amount is None:
            continue
        scaled = round(amount * factor)
        if scaled != amount:
            setattr(value, field, scaled)
            changed += 1
    return changed


def pair_position_subtables(lookup):
    if lookup.LookupType == 2:
        yield from lookup.SubTable
        return
    if lookup.LookupType != 9:
        return
    for extension in lookup.SubTable:
        if extension.ExtensionLookupType == 2:
            yield extension.ExtSubTable


def scale_pair_position_subtable(subtable, factor: float) -> int:
    changed = 0
    if subtable.Format == 1:
        for pair_set in subtable.PairSet:
            for pair in pair_set.PairValueRecord:
                changed += scale_value_record(pair.Value1, factor)
                changed += scale_value_record(pair.Value2, factor)
        return changed

    if subtable.Format == 2:
        for class1 in subtable.Class1Record:
            for class2 in class1.Class2Record:
                changed += scale_value_record(class2.Value1, factor)
                changed += scale_value_record(class2.Value2, factor)
        return changed

    raise ValueError(f"Unsupported PairPos format: {subtable.Format}")


def kern_lookup_indices(font: TTFont) -> set[int]:
    if "GPOS" not in font:
        return set()
    feature_list = font["GPOS"].table.FeatureList
    if feature_list is None:
        return set()
    return {
        lookup_index
        for record in feature_list.FeatureRecord
        if record.FeatureTag == "kern"
        for lookup_index in record.Feature.LookupListIndex
    }


def scale_gpos_kerning(font: TTFont, factor: float) -> tuple[int, int]:
    indices = kern_lookup_indices(font)
    if not indices:
        raise ValueError("The merged font has no GPOS kern feature.")

    changed = 0
    lookups = font["GPOS"].table.LookupList.Lookup
    for lookup_index in sorted(indices):
        for subtable in pair_position_subtables(lookups[lookup_index]):
            changed += scale_pair_position_subtable(subtable, factor)
    return len(indices), changed


def scale_legacy_kerning(font: TTFont, factor: float) -> int:
    if "kern" not in font:
        return 0

    changed = 0
    for subtable in font["kern"].kernTables:
        pairs = getattr(subtable, "kernTable", None)
        if pairs is None:
            continue
        for pair, amount in list(pairs.items()):
            scaled = round(amount * factor)
            if scaled != amount:
                pairs[pair] = scaled
                changed += 1
    return changed


def finalize_font(
    input_path: Path,
    output_path: Path,
    *,
    italic: bool,
    kern_scale: float = DEFAULT_KERN_SCALE,
) -> tuple[int, int, int, GuardStats | None]:
    font = TTFont(input_path)
    lookup_count, gpos_values = scale_gpos_kerning(font, kern_scale)
    legacy_pairs = scale_legacy_kerning(font, kern_scale)
    guard_stats = append_guard_lookup(font) if italic else None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    font.save(output_path)
    font.close()
    return lookup_count, gpos_values, legacy_pairs, guard_stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scale Montserrat kerning and add the SNU Edge italic CJK guard."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--italic", action="store_true")
    parser.add_argument("--kern-scale", type=float, default=DEFAULT_KERN_SCALE)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    lookup_count, gpos_values, legacy_pairs, guard_stats = finalize_font(
        args.input,
        args.output,
        italic=args.italic,
        kern_scale=args.kern_scale,
    )
    guard_summary = "none"
    if guard_stats is not None:
        guard_summary = f"{guard_stats.guard_min}..{guard_stats.guard_max}"
    print(
        f"{args.output}: kern_lookups={lookup_count}, "
        f"gpos_values_scaled={gpos_values}, legacy_pairs_scaled={legacy_pairs}, "
        f"italic_guard={guard_summary}"
    )


if __name__ == "__main__":
    main()
