#!/bin/bash
# startpage - generate themed colors for the Chromium startpage
#
# Reads the current theme's GTK colors (universal across dynamic + static
# themes) and writes CSS custom properties directly into startpage.html.
# Inlining (instead of an external colors.css) avoids both CSS cascade
# overrides and Chromium caching stale colors across theme switches.

src="$CURRENT_LINK/gtk-3.0/colors.css"
[[ -f "$src" ]] || exit 0

OUT_DIR="$HOME/.local/share/sizon/chromium"
mkdir -p "$OUT_DIR"
PAGE="$OUT_DIR/startpage.html"
[[ -f "$PAGE" ]] || exit 0

# get <define-color name> -> hex value (or empty)
get() {
	sed -n "s/^@define-color[[:space:]]\+$1[[:space:]]\+\(#*[0-9a-fA-F]*\).*/\1/p" "$src" | head -1
}

bg=$(get background)
fg=$(get foreground)
accent=$(get accent_color)
[[ -z "$accent" ]] && accent=$(get accent_bg_color)
surface=$(get card_bg_color)
[[ -z "$surface" ]] && surface=$(get popover_bg_color)
[[ -z "$surface" ]] && surface="$bg"

# Build the :root block with per-theme colors
block=":root {"
[[ -n "$bg" ]] && block="$block"$'\n'"  --bg: $bg;"
[[ -n "$fg" ]] && block="$block"$'\n'"  --fg: $fg;"
[[ -n "$accent" ]] && block="$block"$'\n'"  --accent: $accent;"
[[ -n "$surface" ]] && block="$block"$'\n'"  --surface: $surface;"
block="$block"$'\n'"  --muted: color-mix(in srgb, var(--fg, $fg) 55%, transparent);"
block="$block"$'\n'"  --border: color-mix(in srgb, var(--fg, $fg) 12%, transparent);"
block="$block"$'\n'"}"
block=$(printf '%s' "$block" | sed 's/^/  /')

# Replace content between the markers (perl: safe against / and #)
tmp=$(mktemp)
trap "rm -f '$tmp'" RETURN
perl -e '
	my ($page, $block) = @ARGV;
	open my $fh, "<", $page or die "open $page: $!";
	local $/; my $content = <$fh>; close $fh;
	$content =~ s{/\*__SIZON_COLORS_START__\*/.*?/\*__SIZON_COLORS_END__\*/}{/*__SIZON_COLORS_START__*/\n$block\n/*__SIZON_COLORS_END__*/}s;
	open my $out, ">", $page or die "write $page: $!";
	print $out $content; close $out;
' "$PAGE" "$block"

exit 0
