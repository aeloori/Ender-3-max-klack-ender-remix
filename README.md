# Ender 3 Max — Marlin 2.1.2.8

Custom Marlin 2.1.2.8 firmware configuration for the **Creality Ender 3 Max**.

Based on [MarlinFirmware/Marlin](https://github.com/MarlinFirmware/Marlin) (2.1.2.8, `bugfix-2.1.x` lineage). See [marlinfw.org](https://marlinfw.org/) for full upstream documentation, configuration reference, and troubleshooting guides.

## Hardware

- **Printer:** Creality Ender 3 Max
- **Mainboard:** Creality V4.x silent board — `BOARD_CREALITY_V4`
- **MCU:** STM32F103RE (512KB flash)
- Configuration: [`Marlin/Configuration.h`](Marlin/Configuration.h), [`Marlin/Configuration_adv.h`](Marlin/Configuration_adv.h)

## Building

This repo builds with **PlatformIO**. The system Python is externally managed (PEP 668), so PlatformIO is installed in a dedicated virtual environment rather than system-wide:

```bash
# One-time setup
python3 -m venv ~/.platformio-venv
~/.platformio-venv/bin/pip install -U pip platformio

# Build
cd "Marlin-2.1.2.8"
~/.platformio-venv/bin/pio run
```

The default build environment (`default_envs` in [`platformio.ini`](platformio.ini)) is set to:

```
STM32F103RE_creality
```

The compiled firmware is output to:

```
.pio/build/STM32F103RE_creality/firmware.bin
```

### Flashing

1. Copy `firmware.bin` to a freshly formatted micro SD card (FAT32, root directory).
2. Insert the SD card into the mainboard and power-cycle the printer.
3. The board will flash automatically; wait for the screen to boot back to the main menu.
4. Power off, remove the SD card.

## Alternative build tools

- [VS Code + PlatformIO IDE extension](https://marlinfw.org/docs/basics/auto_build_marlin.html)
- [Arduino IDE](https://marlinfw.org/docs/basics/install_arduino.html)
- [VS Code devcontainer](https://marlinfw.org/docs/basics/install_devcontainer_vscode.html)

## License

Marlin is published under the [GPL license](/LICENSE). This fork inherits that license — any redistributed binary must be accompanied by this corresponding source.
