#!/usr/bin/env python3
"""
lcd_theme_gen.py -- generate Marlin-ready PROGMEM bitmap headers for a
runtime-selectable LCD UI theme, from a small YAML config plus source images.

Standalone tool: this file has no dependency on any specific Marlin checkout
layout beyond the paths you give it in the config. Copy this whole directory
to any other Marlin/U8glib (DOGM, 128x64-class monochrome) project, point a
new YAML config at your own art and output location, and run it.

Usage:
    python3 lcd_theme_gen.py <config.yaml> [<config.yaml> ...]
    python3 lcd_theme_gen.py --dry-run <config.yaml>

Dependencies: Pillow, PyYAML (pip install pillow pyyaml)
"""

import argparse
import re
import sys
from pathlib import Path

from PIL import Image
import yaml

MARLIN_LICENSE_HEADER = """/**
 * Marlin 3D Printer Firmware
 * Copyright (c) 2021 MarlinFirmware [https://github.com/MarlinFirmware/Marlin]
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */
"""

BYTE_RE = re.compile(r"B([01]{8})")


class ThemeGenError(Exception):
    pass


def bytewidth(px_width: int) -> int:
    return (px_width + 7) // 8


def pack_bits_to_bytes(bits_row, width):
    """bits_row: list[int] of 0/1, length == width. Pads to a byte boundary with 0."""
    bw = bytewidth(width)
    padded = bits_row + [0] * (bw * 8 - width)
    out = []
    for i in range(bw):
        byte = 0
        for b in range(8):
            byte = (byte << 1) | padded[i * 8 + b]
        out.append(byte)
    return out


def image_to_bits(img: Image.Image, width, height, dither, threshold, invert_source):
    """Load + resize (if needed) + threshold/dither an image to a 2D 0/1 bit grid.
    Convention: dark/black source pixels -> bit=1 (drawn/"on"), light pixels -> bit=0
    ("off"/transparent), matching how u8g.drawBitmapP only paints "1" bits.
    Set invert_source: true if your source art uses the opposite convention.
    """
    if img.size != (width, height):
        print(f"  note: resizing source {img.size} -> ({width},{height})", file=sys.stderr)
        img = img.resize((width, height), Image.LANCZOS)

    gray = img.convert("L")

    if dither == "floyd_steinberg":
        bw_img = gray.convert("1")  # PIL's default convert("1") uses Floyd-Steinberg
    elif dither == "ordered":
        # simple 4x4 Bayer ordered dither
        bayer = [
            [0, 8, 2, 10],
            [12, 4, 14, 6],
            [3, 11, 1, 9],
            [15, 7, 13, 5],
        ]
        px = gray.load()
        bw_img = Image.new("1", (width, height))
        out = bw_img.load()
        for y in range(height):
            for x in range(width):
                t = (bayer[y % 4][x % 4] + 0.5) / 16.0 * 255
                out[x, y] = 255 if px[x, y] > t else 0
    else:  # threshold (default)
        bw_img = gray.point(lambda p: 255 if p > threshold else 0, mode="1")

    px = bw_img.load()
    rows = []
    for y in range(height):
        row = []
        for x in range(width):
            lit = px[x, y] == 0  # black pixel (0) => "ink"/foreground
            if invert_source:
                lit = not lit
            row.append(1 if lit else 0)
        rows.append(row)
    return rows


def rows_to_bytes(rows, width):
    out = []
    for row in rows:
        out.extend(pack_bits_to_bytes(row, width))
    return out


def format_progmem_array(var_name, byte_values, width):
    """Emit a Marlin-style `const unsigned char NAME[] PROGMEM = { B..., ... };` block,
    one source row (bytewidth(width) bytes) per line, matching the existing
    Marlin _Bootscreen.h / status/*.h formatting convention."""
    bw = bytewidth(width)
    lines = []
    for i in range(0, len(byte_values), bw):
        chunk = byte_values[i : i + bw]
        lines.append(",".join(f"B{v:08b}" for v in chunk))
    body = ",\n  ".join(lines)
    return f"const unsigned char {var_name}[] PROGMEM = {{\n  {body}\n}};\n"


def invert_bytes(byte_values):
    return [v ^ 0xFF for v in byte_values]


_IFDEF_INVERTED_RE = re.compile(
    r"#if\s+defined\(\w*_INVERTED\)[^\n]*\n(.*?)#else\n(.*?)#endif",
    re.S,
)


def _strip_inverted_branch(body: str) -> str:
    """Some Marlin bitmap arrays embed a preprocessor branch INSIDE the
    initializer list, e.g. hotend.h's status_hotend_a_bmp:
        #if defined(STATUS_HOTEND_INVERTED) && !defined(STATUS_HOTEND_ANIM)
          ...inverted rows...
        #else
          ...default rows...
        #endif
    A plain brace-matching regex can't tell which branch is "active" without
    a real C preprocessor. Since this tool only ever reads Stock's default
    (non-inverted) art as invert_only input, and Marlin's own convention is
    that the default/non-inverted bitmap rows live in the #else branch of an
    `#if defined(*_INVERTED)` guard, we deterministically keep the #else
    branch and drop the #if branch. This is a documented, Marlin-specific
    heuristic -- not a general C preprocessor."""
    return _IFDEF_INVERTED_RE.sub(lambda m: m.group(2), body)


def extract_existing_array(header_path: Path, array_name: str, occurrence: int = 0):
    """Regex-extract an existing `const unsigned char NAME[] PROGMEM = {...};`
    array's raw byte values out of a real Marlin header file (used for
    invert_only mode -- producing a Stock-inverted variant with no new art).

    Some Marlin status bitmap files (bed.h, fan.h) define the SAME array name
    more than once, under different `#if ENABLED(STATUS_ALT_*_BITMAP)`
    branches selecting between alternate bitmap styles -- this tool doesn't
    evaluate the C preprocessor, so when an array name is ambiguous, pass
    `occurrence` (0-based index into every match found in file order) to pick
    the right one. Figure out the right index once by grepping the header for
    the array name and counting which definition is under the branch your
    build actually compiles."""
    text = header_path.read_text()
    matches = list(re.finditer(re.escape(array_name) + r"\[\]\s*PROGMEM\s*=\s*\{(.*?)\};", text, re.S))
    if not matches:
        raise ThemeGenError(f"array '{array_name}' not found in {header_path}")
    if occurrence >= len(matches):
        raise ThemeGenError(
            f"array '{array_name}' in {header_path}: occurrence {occurrence} "
            f"requested but only {len(matches)} definition(s) found"
        )
    body = _strip_inverted_branch(matches[occurrence].group(1))
    return [int(b, 2) for b in BYTE_RE.findall(body)]


def validate_dims(key, decl_wh, ref_dims):
    if key not in ref_dims:
        raise ThemeGenError(
            f"asset key '{key}' has no entry in reference_dims -- add one so "
            f"its dimensions can be validated against Stock before generating"
        )
    ref_w, ref_h = ref_dims[key]
    if decl_wh is not None and tuple(decl_wh) != (ref_w, ref_h):
        raise ThemeGenError(
            f"asset '{key}': declared width/height {decl_wh} does not match "
            f"reference_dims {(ref_w, ref_h)} -- every themed variant of an "
            f"asset MUST share Stock's exact pixel dimensions (they feed "
            f"compile-time layout macros shared across all themes); a mismatch "
            f"here will silently corrupt the LCD framebuffer at runtime."
        )
    return ref_w, ref_h


def process_config(config_path: Path, dry_run: bool):
    cfg = yaml.safe_load(config_path.read_text())
    base = config_path.parent

    theme = cfg["theme"]
    ref_dims = {k: tuple(v) for k, v in cfg.get("reference_dims", {}).items()}
    out_cfg = cfg.get("output", {})
    out_dir = (base / out_cfg["dir"]).resolve()
    out_filename = out_cfg["filename"]
    license_header = MARLIN_LICENSE_HEADER if out_cfg.get("license_header") == "marlin" else ""

    print(f"== theme '{theme['name']}' ({config_path.name}) ==")

    generated_blocks = []

    for asset in cfg.get("assets", []):
        key = asset["key"]
        w, h = validate_dims(key, asset.get("width_height"), ref_dims)
        src_path = base / asset["source"]
        if not src_path.exists():
            raise ThemeGenError(f"source image not found: {src_path}")

        img = Image.open(src_path)
        rows = image_to_bits(
            img, w, h,
            dither=asset.get("dither", "threshold"),
            threshold=asset.get("threshold", 128),
            invert_source=asset.get("invert_source", False),
        )
        byte_values = rows_to_bytes(rows, w)

        var_name = asset["var_name"]
        print(f"  [{key}] {src_path.name} -> {var_name} ({w}x{h}, {len(byte_values)} bytes)")
        generated_blocks.append(format_progmem_array(var_name, byte_values, w))

        if asset.get("generate_inverted"):
            inv_name = asset.get("var_name_inverted", var_name + "_inv")
            inv_bytes = invert_bytes(byte_values)
            print(f"  [{key}] + inverted -> {inv_name}")
            generated_blocks.append(format_progmem_array(inv_name, inv_bytes, w))

    invert_only_blocks = []
    for item in cfg.get("invert_only", []):
        key = item["key"]
        w, h = validate_dims(key, item.get("width_height"), ref_dims)
        src_header = (base / item["source_header"]).resolve()
        raw_bytes = extract_existing_array(src_header, item["array_name"], item.get("occurrence", 0))
        expected = bytewidth(w) * h
        if len(raw_bytes) != expected:
            raise ThemeGenError(
                f"invert_only '{key}': {item['array_name']} in {src_header} has "
                f"{len(raw_bytes)} bytes, expected {expected} for {w}x{h} -- "
                f"reference_dims for this key is wrong, fix it before proceeding"
            )
        inv_bytes = invert_bytes(raw_bytes)
        var_name = item["var_name"]
        print(f"  [invert_only:{key}] {item['array_name']} @ {src_header.name} -> {var_name}")
        invert_only_blocks.append(format_progmem_array(var_name, inv_bytes, w))

    if dry_run:
        print("  (dry run -- nothing written)")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    if generated_blocks:
        out_path = out_dir / out_filename
        content = (
            license_header
            + f"\n// AUTO-GENERATED by tools/lcd_theme_gen/lcd_theme_gen.py from {config_path.name}\n"
            + "// Do not hand-edit -- re-run the generator instead.\n"
            + "#pragma once\n\n"
            + "\n".join(generated_blocks)
        )
        out_path.write_text(content)
        print(f"  -> wrote {out_path}")

    if invert_only_blocks:
        io_filename = cfg.get("invert_only_filename", "ui_theme_invert_only.h")
        io_path = out_dir / io_filename
        io_content = (
            license_header
            + f"\n// AUTO-GENERATED by tools/lcd_theme_gen/lcd_theme_gen.py from {config_path.name} (invert_only)\n"
            + "// Do not hand-edit -- re-run the generator instead.\n"
            + "#pragma once\n\n"
            + "\n".join(invert_only_blocks)
        )
        io_path.write_text(io_content)
        print(f"  -> wrote {io_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("configs", nargs="+", type=Path)
    ap.add_argument("--dry-run", action="store_true", help="validate + report, write nothing")
    args = ap.parse_args()

    had_error = False
    for cfg_path in args.configs:
        try:
            process_config(cfg_path, args.dry_run)
        except ThemeGenError as e:
            print(f"ERROR ({cfg_path}): {e}", file=sys.stderr)
            had_error = True
    sys.exit(1 if had_error else 0)


if __name__ == "__main__":
    main()
