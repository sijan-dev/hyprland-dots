#!/bin/bash
# vscode - deploy Sizon as a VS Code theme extension
#
# 1. Generates the current theme's colors as a VS Code theme extension
#    at ~/.vscode-oss/extensions/ so it shows up in the theme picker.
# 2. Injects colors into settings.json under [Sizon Dark] scope
#    for live update without reload.

theme_src="$CURRENT_LINK/vscode/themes/sizon-color-theme.json"

# Auto-generate from colors.toml if not already present
if [[ ! -f "$theme_src" ]]; then
  colors_toml="$CURRENT_LINK/colors.toml"
  if [[ -f "$colors_toml" ]]; then
    bash "$HOME/.local/bin/sizon-set-templates" "$CURRENT_LINK" 2>/dev/null
  fi
fi

[[ -f "$theme_src" ]] || exit 0

# ── 1. Update extension theme file ──────────────────────────────────
ext_dir="$HOME/.vscode-oss/extensions/sizon.sizon-theme-1.0.0"
themes_dir="$ext_dir/themes"
mkdir -p "$themes_dir"

# Deploy static extension manifest (only once)
pkg="$HOME/.local/share/sizon/vscode-theme/package.json"
[[ -f "$ext_dir/package.json" ]] || cp "$pkg" "$ext_dir/package.json"

cp "$theme_src" "$themes_dir/sizon-color-theme.json"

# ── 2. Live-inject into settings.json under [Sizon Dark] scope ──
settings="$HOME/.config/Code - OSS/User/settings.json"
if [[ -f "$settings" ]]; then
  tmp=$(mktemp)
  clean=$(mktemp)
  trap "rm -f '$tmp' '$clean'" RETURN
  sed -e 's|^[[:space:]]*//.*$||' -e 's|^[[:space:]]*/\*.*\*/[[:space:]]*$||' "$settings" > "$clean"
  jq --slurpfile colors "$theme_src" \
    '."[Sizon Dark]" = { "workbench.colorCustomizations": $colors[0].colors, "editor.tokenColorCustomizations": { "textMateRules": $colors[0].tokenColors } }' \
    "$clean" > "$tmp" && mv "$tmp" "$settings"
fi
