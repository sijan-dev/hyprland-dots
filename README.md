# Sizon Dotfiles

> A curated [Hyprland](https://hyprland.org/) desktop configuration for Arch Linux, built around [matugen](https://github.com/InioX/matugen) dynamic theming and a pluggable wallpaper switcher.

[![Hyprland](https://img.shields.io/badge/desktop-Hyprland-0f766e?style=flat-square)](https://hyprland.org/)

## Screenshots

| | |
| --- | --- |
| ![Desktop](assets/setup.png) | ![App launcher](assets/launcher.png) |
| ![Wallpaper flipper](assets/wallflipper.png) | ![Themed apps](assets/chromium.png) |
| ![Desktop](assets/screenshot-desktop.png) | |

## Overview

Configurations live in `configs/` and are symlinked into `~/.config` by
`install.sh`. Theme colors are generated dynamically from the current wallpaper
via [matugen](https://github.com/InioX/matugen), keeping every application in a
consistent, unified palette.

```
configs/        per-app config, symlinked to ~/.config/<name>
bin/            theme scripts + helper utilities + hooks/
wallfliper/     wallpaper flipper app source (~/.local/share/wallfliper)
wallpapers/     curated default wallpaper set (6 images)
assets/         README screenshots
install.sh      one-shot installer / uninstaller
```

## Getting started

### Prerequisites

- Arch Linux (or an Arch-based distro using `pacman` / `paru`).

### Installation

```sh
# Backup originals and symlink configs
./install.sh

# Full install (also installs missing packages via paru)
./install.sh --install

# Pre-select the wallpaper switcher back-end (skips the interactive prompt)
./install.sh --wallpaper-switcher rofi
```

### Available flags

| Flag | Description |
| --- | --- |
| `--install`          | Backup + symlink, then install missing packages (`-y`) |
| `--wallpaper-switcher <wallfliper\|rofi>` | Choose the back-end without prompting |
| `--dry-run`          | Print what would happen without changing anything |
| `--uninstall`        | Remove symlinks and restore from `~/.config-backup` |

> Without `--wallpaper-switcher`, an interactive prompt asks which back-end you
> want. The choice is stored in `~/.current_wallpaper_switcher`, and the generic
> `bin/wallpaper` front-end (used by every keybind and autostart entry) dispatches
> to the correct one.

### Post-install

Run matugen once against a wallpaper to generate the theme:

```sh
matugen image ~/.config/matugen/generated/wallpaper   # or any wallpaper image
```

Symlinked configs are **live immediately** — edit inside
`~/Projects/dotfiles/configs/<name>` and commit the changes.

## Wallpaper switcher

Two interchangeable back-ends, both wired to the same bindings via
`bin/wallpaper`:

| Binding | Action |
| --- | --- |
| `ALT+SPACE`            | Open picker |
| `CTRL+ALT+SPACE`       | Apply random wallpaper |
| `SUPER+ALT+LEFT/RIGHT` | Cycle forward / backward |
| (autostart)            | Restore wallpaper on login |

### Back-ends

- **wallfliper** *(default)* — GUI flipper app with video wallpapers
  (mpvpaper), animated transitions, and thumbnail previews. Installed as a
  Python app to `~/.local/share/wallfliper` (vendored from upstream — see the
  [Wallfliper](#wallfliper) section).
- **rofi** — lightweight rofi menu over the wallpaper folder; applies via
  `sizon` (awww + matugen + hooks). No Python dependency. Supports
  `--restore / --random / --next / --prev`.

Switching back-ends later is a one-liner:

```sh
./install.sh --wallpaper-switcher <wallfliper|rofi>
```

## Dependencies

**Core** — `hyprland hypridle hyprlock hyprsunset waybar swaync swayosd kitty
matugen fish fastfetch starship tmux yazi btop cava gtk3 gtk4 adw-gtk3 rofi
awww ttf-space-grotesk`

**wallfliper mode** — `pyside6 layer-shell-qt mpvpaper ffmpeg`

**`bin/` helpers may need** — `wl-clip-persist cliphist polkit-gnome hyprpicker
grim slurp hyprlock playerctl pipewire-pulse bluez`

## Theming

Colors are derived from the active wallpaper with
[matugen](https://github.com/InioX/matugen).

- Templates: `configs/matugen/templates/`
- Output mapping: `configs/matugen/config.toml`
- Generated outputs (`matugen/generated/`, `hyprlock.conf`, `waybar/colors.css`,
  GTK colors, `yazi/theme.toml`, `btop` theme, `cava` config, `starship.toml`)
  are **not** committed — regenerate with `matugen image <wallpaper>`, or
  simply switch/randomize the wallpaper.

Utility scripts:

| Script | Purpose |
| --- | --- |
| `bin/theme-switch`            | Toggle matugen (dynamic) / darky (static) engines |
| `bin/toggle-light-dark`       | Toggle light and dark matugen palettes |
| `bin/sizon`                   | Apply a random wallpaper (awww + matugen + hooks) |
| `bin/wallpaper`               | Dispatcher front-end for the active switcher |
| `bin/wallpaper-rofi`          | Rofi picker / random / next / prev |
| `bin/hooks/`                  | Apply colors to apps after a theme change |

## Machine-specific configuration

The following are intentionally per-machine and should be reviewed after a
fresh install:

- `configs/fastfetch/config.jsonc` — logo path (`~/Pictures/Camera/cam.png`).
- `configs/hypr/monitors.lua` — display layout.
- `configs/hypr/hypridle.conf` — lock timeouts.
- **Wallpapers** — the repo ships a small default set in `wallpapers/`. Point
  wallfliper at your full collection in
  `~/.config/wallfliper/config.json` → `"wallpaper_dir": "~/Pictures/wallpapers"`.
- **Switcher choice** — `~/.current_wallpaper_switcher` is written by
  `install.sh`; the theme scripts create the remaining runtime state
  (`.current_theme_engine`, `.current_theme_mode`, `.current_wallpaper_index`)
  automatically on first use.
- **Home paths** — a few configs (`fish/fish_variables`, `btop.conf`,
  `gtk-3.0/bookmarks`, `swayosd/config.toml`, `swaync/style.css`) are authored
  for `/home/sijan`; `install.sh` rewrites them to `$HOME` when it differs
  (a no-op on the author's machine).

## Wallfliper

A vendored copy of the [wallfliper](https://github.com/Roberth-Souza/wallfliper)
app (excluding the optional `everforest` wallpaper pack, ~1.1 GB). Upstream is
vendored at commit `11d157d`; the live install lives at
`~/.local/share/wallfliper`. To update, copy newer upstream files over
`wallfliper/` and commit.

## Acknowledgments

- [JaKooLit/Hyprland-Dots](https://github.com/JaKooLit/Hyprland-Dots) — structure and inspiration
- [matugen](https://github.com/InioX/matugen) — dynamic theming engine
- [Roberth-Souza/wallfliper](https://github.com/Roberth-Souza/wallfliper) — wallpaper flipper app