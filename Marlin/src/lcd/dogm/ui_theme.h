/**
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
#pragma once

/**
 * Runtime-selectable LCD UI theme system for the DOGM (U8glib, 128x64-class
 * monochrome graphic LCD) codepath. Assets are generated ahead of time by
 * tools/lcd_theme_gen/lcd_theme_gen.py into src/lcd/dogm/theme_assets/ and
 * consumed by ui_theme.cpp, which builds the actual per-asset lookup tables
 * declared here. Draw sites (marlinui_DOGM.cpp, status_screen_DOGM.cpp) only
 * ever see these tables -- never the generated headers directly.
 */

#include "../../inc/MarlinConfigPre.h"
#include <U8glib-HAL.h>

enum UIThemeID : uint8_t {
  UI_THEME_STOCK,
  UI_THEME_RESKIN,
  UI_THEME_LAYOUT2,
  UI_THEME_COUNT
};

#define UI_THEME_VARIANTS     2   // normal, inverted
#define UI_THEME_INDEX_COUNT  (UI_THEME_COUNT * UI_THEME_VARIANTS)

FORCE_INLINE uint8_t ui_theme_id(uint8_t index)       { return index / UI_THEME_VARIANTS; }
FORCE_INLINE bool    ui_theme_inverted(uint8_t index) { return index % UI_THEME_VARIANTS; }

// Human-readable names for the theme-picker menu, indexed by the same 0..5 value.
extern const char* const ui_theme_names[UI_THEME_INDEX_COUNT];

// Per-asset PROGMEM pointer tables, one entry per theme index (0..5).
// Built in ui_theme.cpp from the generated theme_assets/*.h headers plus
// Marlin's existing Stock bitmaps (Stock reuses those unchanged).
extern const u8g_pgm_uint8_t* const ui_theme_bootscreen_bmp[UI_THEME_INDEX_COUNT];
extern const u8g_pgm_uint8_t* const ui_theme_status_logo_bmp[UI_THEME_INDEX_COUNT];
extern const u8g_pgm_uint8_t* const ui_theme_hotend_off_bmp[UI_THEME_INDEX_COUNT];
extern const u8g_pgm_uint8_t* const ui_theme_hotend_on_bmp[UI_THEME_INDEX_COUNT];
extern const u8g_pgm_uint8_t* const ui_theme_bed_off_bmp[UI_THEME_INDEX_COUNT];
extern const u8g_pgm_uint8_t* const ui_theme_bed_on_bmp[UI_THEME_INDEX_COUNT];
extern const u8g_pgm_uint8_t* const ui_theme_fan0_bmp[UI_THEME_INDEX_COUNT];
extern const u8g_pgm_uint8_t* const ui_theme_fan1_bmp[UI_THEME_INDEX_COUNT];
