#!/usr/bin/env python3
"""
One-off helper that procedurally draws this project's example theme art
(no external image assets available in this environment) at high
supersampled resolution, then downsamples to the exact target pixel size
each icon needs. Output lands in examples/art/, consumed by
ender3max_reskin.yaml / ender3max_layout2.yaml.

This script is NOT part of the reusable lcd_theme_gen tool -- it's specific
to this project's placeholder art. A real project would instead hand its own
source images to lcd_theme_gen.py directly.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ART = Path(__file__).parent / "art"
ART.mkdir(exist_ok=True)
SS = 8  # supersample factor


def canvas(w, h):
    img = Image.new("L", (w * SS, h * SS), 255)
    return img, ImageDraw.Draw(img)


def save(img, w, h, name):
    out = img.resize((w, h), Image.LANCZOS)
    out.save(ART / name)
    print(f"wrote {name} ({w}x{h})")


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# ---------------------------------------------------------------- bootscreen
def text_block(text, target_w, target_h, font_size=60, bold=True):
    """Render text at a large native size (optionally thickened by drawing
    it several times with 1px offsets, since the PIL default bitmap font has
    no bold variant), crop to content, then scale to fit (target_w, target_h)
    preserving aspect ratio. Small pixel targets need much bolder strokes
    than a plain single-pass antialiased render survives once downscaled."""
    f = font(font_size)
    tmp = Image.new("L", (2000, 200), 255)
    td = ImageDraw.Draw(tmp)
    offsets = [(0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (0, 2)] if bold else [(0, 0)]
    for ox, oy in offsets:
        td.text((ox, oy), text, font=f, fill=0)
    bbox = ImageOps.invert(tmp).getbbox()  # invert: text(black=0)->white=non-zero, so getbbox finds the ink region
    tmp = tmp.crop(bbox)
    scale = min(target_w / tmp.width, target_h / tmp.height)
    return tmp.resize((max(1, int(tmp.width * scale)), max(1, int(tmp.height * scale))), Image.LANCZOS)


def bootscreen(name, style):
    w, h = 81, 58
    img, d = canvas(w, h)
    S = SS
    cx = w * S // 2

    # Stylized nozzle mark: an inverted triangle (nozzle cone) over a small
    # filament drop, in the top ~34px, wordmark filling the remaining ~24px.
    top_y = 2 * S
    tri_w = 26 * S
    tri_h = 16 * S
    if style == "outline":
        d.polygon(
            [(cx - tri_w // 2, top_y), (cx + tri_w // 2, top_y), (cx, top_y + tri_h)],
            outline=0, width=2 * S,
        )
        d.ellipse(
            [cx - 3 * S, top_y + tri_h + 2 * S, cx + 3 * S, top_y + tri_h + 8 * S],
            outline=0, width=2 * S,
        )
    else:  # filled/bold, for the layout2 variant
        d.polygon(
            [(cx - tri_w // 2, top_y), (cx + tri_w // 2, top_y), (cx, top_y + tri_h)],
            fill=0,
        )
        d.ellipse(
            [cx - 3 * S, top_y + tri_h + 1 * S, cx + 3 * S, top_y + tri_h + 7 * S],
            fill=0,
        )

    text_area_top = top_y + tri_h + 12 * S
    text_area_h = (h * S) - text_area_top - 2 * S
    txt = text_block("E3 MAX", int(w * S * 0.92), text_area_h, font_size=40)
    img.paste(txt, (cx - txt.width // 2, text_area_top + (text_area_h - txt.height) // 2))

    save(img, w, h, name)


bootscreen("reskin_boot.png", "outline")
bootscreen("layout2_boot.png", "filled")


# --------------------------------------------------------------- status_logo
def status_logo(name, style):
    # 7px tall is below the legibility floor for rendered text (even bold,
    # downscaled TTF glyphs wash out to noise at this size) -- use a small
    # geometric "flow" motif (three ascending bars) instead of a wordmark.
    w, h = 39, 7
    img, d = canvas(w, h)
    S = SS
    bar_w = 4 * S
    gap = 3 * S
    heights = [3 * S, 5 * S, 7 * S]
    x = 2 * S
    for bh in heights:
        y0 = h * S - bh
        if style == "outline":
            d.rectangle([x, y0, x + bar_w, h * S], outline=0, width=1 * S)
        else:
            d.rectangle([x, y0, x + bar_w, h * S], fill=0)
        x += bar_w + gap
    save(img, w, h, name)


status_logo("reskin_status_logo.png", "outline")
status_logo("layout2_status_logo.png", "filled")


# -------------------------------------------------------------------- hotend
def hotend(name, on, style):
    w, h = 16, 12
    img, d = canvas(w, h)
    S = SS
    cx = w * S // 2
    # nozzle: small triangle + shaft
    d.rectangle([cx - 3 * S, 0, cx + 3 * S, 5 * S], outline=0, width=1 * S if style == "outline" else None,
                fill=(None if style == "outline" else 0))
    d.polygon([(cx - 4 * S, 5 * S), (cx + 4 * S, 5 * S), (cx, 10 * S)],
              outline=0, width=1 * S if style == "outline" else None,
              fill=(None if style == "outline" else 0))
    if on:
        # heat lines radiating up
        for dx in (-5, 0, 5):
            d.line([(cx + dx * S, -1 * S), (cx + dx * S, -4 * S)], fill=0, width=1 * S)
    save(img, w, h, name)


hotend("reskin_hotend_off.png", False, "outline")
hotend("reskin_hotend_on.png", True, "outline")
hotend("layout2_hotend_off.png", False, "filled")
hotend("layout2_hotend_on.png", True, "filled")


# ----------------------------------------------------------------------- bed
def bed_off(name):
    w, h = 21, 2
    img, d = canvas(w, h)
    S = SS
    d.line([(0, 0), (w * S, 0)], fill=0, width=1 * S)
    save(img, w, h, name)


def bed_on(name, style):
    w, h = 21, 12
    img, d = canvas(w, h)
    S = SS
    # bed surface (bottom double line, matches Stock's baseline convention)
    d.line([(0, (h - 2) * S), (w * S, (h - 2) * S)], fill=0, width=1 * S)
    d.line([(0, (h - 1) * S), (w * S, (h - 1) * S)], fill=0, width=1 * S)
    # heat zigzag wave above
    pts = []
    n = 5
    for i in range(n * 2 + 1):
        x = i * (w * S) / (n * 2)
        y = (2 * S) if i % 2 == 0 else (7 * S)
        pts.append((x, y))
    d.line(pts, fill=0, width=(2 * S if style == "filled" else 1 * S))
    save(img, w, h, name)


bed_off("reskin_bed_off.png")
bed_on("reskin_bed_on.png", "outline")
bed_off("layout2_bed_off.png")
bed_on("layout2_bed_on.png", "filled")


# ----------------------------------------------------------------------- fan
def fan(name, angle_offset, style):
    w, h = 20, 18
    img, d = canvas(w, h)
    S = SS
    cx, cy = w * S // 2, h * S // 2
    r_outer = 8 * S
    r_hub = 2 * S
    d.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], outline=0, width=1 * S)
    import math
    blades = 4
    for i in range(blades):
        a = math.radians(angle_offset + i * (360 / blades))
        bx = cx + math.cos(a) * (r_outer - 1 * S)
        by = cy + math.sin(a) * (r_outer - 1 * S)
        perp = a + math.pi / 2
        px = math.cos(perp) * 1.6 * S
        py = math.sin(perp) * 1.6 * S
        if style == "outline":
            d.polygon([(cx, cy), (bx + px, by + py), (bx - px, by - py)], outline=0, width=1 * S)
        else:
            d.polygon([(cx, cy), (bx + px, by + py), (bx - px, by - py)], fill=0)
    d.ellipse([cx - r_hub, cy - r_hub, cx + r_hub, cy + r_hub],
              outline=0, width=1 * S, fill=(0 if style == "filled" else None))
    save(img, w, h, name)


fan("reskin_fan_frame0.png", 0, "outline")
fan("reskin_fan_frame1.png", 20, "outline")
fan("layout2_fan_frame0.png", 0, "filled")
fan("layout2_fan_frame1.png", 20, "filled")

print("done")
