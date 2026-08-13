#!/bin/bash
# chromium/brave - apply theme background as BrowserThemeColor managed policy
#
# Reads the current theme's RGB background from chromium.theme and pushes it to
# Chromium & Brave via their managed policy dirs, then refreshes running
# browsers with --refresh-platform-policy (no restart required).
# Mirrors Omarchy's omarchy-theme-set-browser.

theme_file="$CURRENT_LINK/chromium.theme"

# Fall back to the GTK background color if the theme has no chromium.theme
if [[ ! -f "$theme_file" ]]; then
	gtk_colors="$CURRENT_LINK/gtk-3.0/colors.css"
	[[ -f "$gtk_colors" ]] || exit 0
	bg_hex=$(grep -m1 "@define-color background" "$gtk_colors" | sed -E 's/.*#([0-9a-fA-F]{6}).*/\1/')
	[[ "$bg_hex" =~ ^[0-9a-fA-F]{6}$ ]] || exit 0
	theme_file=""
else
	rgb=$(<"$theme_file")
	[[ "$rgb" =~ ^[0-9]+,[0-9]+,[0-9]+$ ]] || exit 0
	hex=$(printf '#%02x%02x%02x' ${rgb//,/ })
fi

if [[ -z "$theme_file" ]]; then
	hex="#$bg_hex"
fi

apply_browser() {
	local binary="$1"
	local policy_dir="$2"
	[[ -d "$policy_dir" ]] || return 0
	echo "{\"BrowserThemeColor\": \"$hex\", \"BrowserColorScheme\": \"device\"}" > "$policy_dir/color.json"
	if command -v "$binary" &>/dev/null && pgrep -x "$binary" >/dev/null; then
		"$binary" --refresh-platform-policy --no-startup-window &>/dev/null
	fi
}

apply_browser chromium /etc/chromium/policies/managed
apply_browser google-chrome-stable /etc/opt/chrome/policies/managed
exit 0
