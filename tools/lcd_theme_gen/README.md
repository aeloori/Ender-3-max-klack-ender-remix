# lcd_theme_gen

Generates Marlin-ready `PROGMEM` bitmap headers for a runtime-selectable LCD
UI theme, from a small YAML config plus source images. Built for Marlin's
DOGM/U8glib graphical-LCD codepath (128x64-class monochrome displays like the
ST7920-based 12864 panels), but the tool itself is display-resolution-agnostic
-- the target width/height for every asset comes from your config, not from
anything hardcoded here.

This directory has no dependency on any specific Marlin checkout's file
layout beyond the paths *you* give it in a config file. Copy the whole
`tools/lcd_theme_gen/` directory to any other Marlin/U8glib project, write a
new YAML config pointing at your own art and output location, and run it.

## Install

```bash
pip install pillow pyyaml
```

## Usage

```bash
python3 lcd_theme_gen.py path/to/your_theme.yaml
python3 lcd_theme_gen.py --dry-run path/to/your_theme.yaml   # validate only, write nothing
python3 lcd_theme_gen.py theme_a.yaml theme_b.yaml            # generate several themes in one run
```

## Config format

One YAML file per theme. See `examples/ender3max_reskin.yaml` and
`examples/ender3max_layout2.yaml` for complete, working examples from a real
project (a 128x64 ST7920 Ender 3 Max build).

```yaml
theme:
  name: my_theme            # human-readable, only used in log output

output:
  dir: "../../Marlin/src/lcd/dogm/theme_assets"   # relative to this yaml file
  filename: "ui_theme_my_theme.h"
  license_header: marlin    # "marlin" emits Marlin's standard GPL header block, or "none"

# Every asset "key" you use below MUST have a matching entry here, with the
# EXACT pixel width/height that the corresponding Stock/default Marlin bitmap
# already uses. This is the single most important safety net the tool
# provides: Marlin computes bitmap layout (X/Y offsets, byte-width, row
# counts for some assets) from compile-time macros that are shared across
# every theme in one firmware build. If a themed bitmap's actual pixel
# dimensions don't match Stock's, the mismatch is NOT caught by the C++
# compiler (PROGMEM arrays are just untyped byte blobs) -- it silently
# corrupts the LCD framebuffer at runtime instead. Get these numbers by
# reading your project's existing _Bootscreen.h / _Statusscreen.h /
# src/lcd/dogm/status/*.h once, and they should almost never change afterward.
reference_dims:
  bootscreen: [81, 58]
  status_logo: [39, 7]
  hotend.off: [16, 12]
  hotend.on: [16, 12]
  bed.off: [21, 2]
  bed.on: [21, 12]
  fan.frame0: [20, 18]
  fan.frame1: [20, 18]

assets:
  - key: bootscreen                      # must exist in reference_dims
    source: art/my_theme_boot.png        # relative to this yaml file
    dither: threshold                    # threshold | floyd_steinberg | ordered
    threshold: 128                       # only used by "threshold" dither
    invert_source: false                 # true if your art uses white=ink, black=bg
    generate_inverted: true              # also emit a pre-inverted (dark-mode) variant
    var_name: theme_my_theme_bootscreen_bmp

  - key: hotend.off
    source: art/my_theme_hotend_off.png
    generate_inverted: true
    var_name: theme_my_theme_hotend_off_bmp

  # ... one entry per asset (status_logo, hotend.on, bed.off, bed.on, fan.frameN, ...)

# Optional: produce an inverted variant of an EXISTING bitmap already baked
# into your Marlin tree, without needing any new source art at all. This is
# how a "Stock, but dark" theme variant gets generated for free.
invert_only:
  - key: bootscreen
    source_header: "../../Marlin/_Bootscreen.h"
    array_name: custom_start_bmp
    var_name: theme_stock_bootscreen_bmp_inv
```

Source images: any format Pillow can open (PNG recommended). Convention is
**black pixels = "on"/ink, white pixels = "off"/background** -- this matches
how `u8g.drawBitmapP()` only paints bits that are `1`, and lets you author
icons the same way you'd draw a normal black-on-white glyph. Set
`invert_source: true` on an asset if your source art uses the opposite
convention. If your source image isn't already exactly the target pixel
size, it's resized with Lanczos resampling before thresholding/dithering --
for small icons (under ~30px) you'll generally get cleaner results authoring
pixel-exact source art up front rather than relying on the resize.

## Output

One header per theme (`output.filename`), plus one more
(`ui_theme_invert_only.h` by default, or `invert_only_filename` if set) if
the config has an `invert_only` section. Each file is plain, drop-in Marlin C:

```c
const unsigned char theme_my_theme_hotend_off_bmp[] PROGMEM = {
  B00011111,B11100000,
  ...
};
```

identical in format to Marlin's own `_Bootscreen.h` / `status/hotend.h`, so
it `#include`s with zero hand-editing. Generated files carry an
`// AUTO-GENERATED` comment -- re-run the script after changing art, don't
hand-edit the output.

## Regenerating this project's theme assets

From this directory:

```bash
python3 lcd_theme_gen.py examples/ender3max_reskin.yaml examples/ender3max_layout2.yaml
```

This regenerates the headers under `Marlin/src/lcd/dogm/theme_assets/`
consumed by `Marlin/src/lcd/dogm/ui_theme.cpp`.
