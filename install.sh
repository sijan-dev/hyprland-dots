#!/usr/bin/env bash
#
# Sizon Dotfiles installer
#
#   ./install.sh              backup + symlink configs, copy scripts/wallfliper
#   ./install.sh --install    same, plus package install (Arch/paru, needs -y)
#   ./install.sh --dry-run    print actions without changing anything
#   ./install.sh --uninstall  remove symlinks, restore backups
#   ./install.sh --wallpaper-switcher <wallfliper|rofi>
#                             wallpaper front-end (prompts if omitted)
#
set -euo pipefail

# ── repo layout ────────────────────────────────────────────────────────────
DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIGS_DIR="$DOTFILES_DIR/configs"
BIN_DIR="$DOTFILES_DIR/bin"
WALLFLIPER_DIR="$DOTFILES_DIR/wallfliper"
WALLPAPERS_DIR="$DOTFILES_DIR/wallpapers"

HOME_DIR="${HOME:-$(eval echo ~)}"
CONFIG="$HOME_DIR/.config"
BACKUP="$HOME_DIR/.config-backup"
LOCAL_BIN="$HOME_DIR/.local/bin"
LOCAL_SHARE="$HOME_DIR/.local/share"
WALLFLIPER_TARGET="$LOCAL_SHARE/wallfliper"
WALLPAPER_TARGET="$LOCAL_SHARE/dotfiles/wallpapers"
GENERATED="$CONFIG/matugen/generated"

DO_INSTALL=false
DO_UNINSTALL=false
DO_DRY_RUN=false
ASSUME_YES=false
WALLPAPER_SWITCHER=""      # "wallfliper" | "rofi"; empty → auto-detect

# ── helpers ────────────────────────────────────────────────────────────────
RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; CYAN=$'\033[0;36m'; RESET=$'\033[0m'
ok()    { echo -e "${GREEN}[OK]${RESET} $1"; }
info()  { echo -e "${CYAN}[INFO]${RESET} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET} $1" >&2; }
err()   { echo -e "${RED}[ERROR]${RESET} $1" >&2; }

dry() { [[ "$DO_DRY_RUN" == true ]]; }

run() {
	if dry; then
		echo "    $*"
	else
		"$@"
	fi
}

# ── configs to symlink ─────────────────────────────────────────────────────
CONFIGS=(hypr waybar swaync kitty matugen fish fastfetch gtk-3.0 gtk-4.0 tmux yazi btop swayosd)

# runtime symlinks recreated after configs are linked
runtime_links=(
	"$CONFIG/waybar/colors.css|$GENERATED/waybar/colors.css"
	"$CONFIG/gtk-3.0/colors.css|$GENERATED/gtk-3.0/colors.css"
	"$CONFIG/gtk-4.0/colors.css|$GENERATED/gtk-4.0/colors.css"
	"$CONFIG/yazi/theme.toml|$GENERATED/yazi/theme.toml"
	"$CONFIG/btop/themes/current.theme|$GENERATED/btop/themes/current.theme"
	"$CONFIG/cava/config|$GENERATED/cava/config"
	"$CONFIG/starship.toml|$GENERATED/starship.toml"
)

# ── parse args ─────────────────────────────────────────────────────────────
# ── parse args ─────────────────────────────────────────────────────────────
args=("$@")
for ((i = 0; i < $#; i++)); do
	case "${args[$i]}" in
		--install|-i)                DO_INSTALL=true ;;
		--uninstall|-u)              DO_UNINSTALL=true ;;
		--dry-run|-n)                DO_DRY_RUN=true ;;
		-y|--yes)                    ASSUME_YES=true ;;
		--wallpaper-switcher|--wallpaper-backend)
			if [[ $((i + 1)) -ge $# ]]; then
				err "missing value for ${args[$i]} (wallfliper|rofi)"; exit 1
			fi
			WALLPAPER_SWITCHER="${args[$((i + 1))]}"
			i=$((i + 1))
			;;
		-h|--help) sed -n '2,12p' "$0"; exit 0 ;;
		*) err "unknown argument: ${args[$i]} (see --help)"; exit 1 ;;
	esac
done
case "$WALLPAPER_SWITCHER" in
	"") : ;;
	wallfliper|rofi) : ;;
	*) err "invalid --wallpaper-switcher '$WALLPAPER_SWITCHER' (choose wallfliper or rofi)"; exit 1 ;;
esac

if [[ ! -d "$CONFIGS_DIR" ]]; then
	err "repo layout missing: $CONFIGS_DIR"
	exit 1
fi

# ── wallpaper switcher choice ──────────────────────────────────────────────
if [[ -z "$WALLPAPER_SWITCHER" ]]; then
	if [[ "$DO_DRY_RUN" == true ]]; then
		WALLPAPER_SWITCHER="wallfliper"  # arbitrary for the dry-run listing
	elif [[ -t 0 ]] && [[ -t 1 ]]; then
		info "Choose the wallpaper switcher:"
		echo "    1) wallfliper  — GUI app with mpvpaper video support (heavier)"
		echo "    2) rofi        — lightweight rofi menu picker (no python app)"
		printf "  [1/2] (default: 1) "
		read -r choice || true
		case "$choice" in
			2|rofi) WALLPAPER_SWITCHER="rofi" ;;
			*)      WALLPAPER_SWITCHER="wallfliper" ;;
		esac
	else
		WALLPAPER_SWITCHER="wallfliper"
	fi
fi
info "Wallpaper switcher: $WALLPAPER_SWITCHER"

# ── uninstall ──────────────────────────────────────────────────────────────
if [[ "$DO_UNINSTALL" == true ]]; then
	info "Uninstalling config symlinks…"
	for name in "${CONFIGS[@]}"; do
		link="$CONFIG/$name"
		if [[ -L "$link" ]] && [[ "$(readlink -f "$link")" == "$CONFIGS_DIR/$name" ]]; then
			run rm "$link"
			ok "removed $link"
		fi
	done
	if [[ -d "$BACKUP" ]]; then
		for name in "${CONFIGS[@]}"; do
			[[ -e "$BACKUP/$name" ]] && run mv "$BACKUP/$name" "$CONFIG/$name" && ok "restored $name from backup"
		done
	else
		info "no backup dir found at $BACKUP"
	fi
	info "Uninstall complete."
	exit 0
fi

# ── backup ─────────────────────────────────────────────────────────────────
backup_config() {
	local name="$1" src="$CONFIG/$name" dst="$BACKUP/$name"
	[[ -e "$src" ]] || return 0
	if [[ -L "$src" ]] && [[ "$(readlink -f "$src")" == "$CONFIGS_DIR/$name" ]]; then
		return 0  # already linked to this repo
	fi
	info "backing up $src → $dst"
	run mkdir -p "$BACKUP"
	run rm -rf "$dst"
	run mv "$src" "$dst"
}

# ── config symlinks ────────────────────────────────────────────────────────
info "Linking configs…"
run mkdir -p "$CONFIG"
for name in "${CONFIGS[@]}"; do
	backup_config "$name"
	link="$CONFIG/$name"
	if [[ -L "$link" ]] && [[ "$(readlink -f "$link")" == "$CONFIGS_DIR/$name" ]]; then
		ok "$name already linked"
	else
		run ln -s "$CONFIGS_DIR/$name" "$link"
		ok "linked $name"
	fi
done

# ── bin scripts + hooks ────────────────────────────────────────────────────
# In rofi mode the wallfliper wrapper is skipped — wallpaper-rofi handles it.
info "Installing bin scripts…"
run mkdir -p "$LOCAL_BIN"
for script in "$BIN_DIR"/*; do
	[[ -f "$script" ]] || continue
	name="$(basename "$script")"
	if [[ "$WALLPAPER_SWITCHER" == "rofi" ]] && [[ "$name" == "wallfliper" ]]; then
		[[ -e "$LOCAL_BIN/$name" ]] && run rm -f "$LOCAL_BIN/$name"
		continue
	fi
	if [[ -e "$LOCAL_BIN/$name" ]] && ! dry; then
		run mkdir -p "$BACKUP/local-bin"
		run rm -rf "$BACKUP/local-bin/$name"
		run mv "$LOCAL_BIN/$name" "$BACKUP/local-bin/$name"
	fi
	run cp "$script" "$LOCAL_BIN/$name"
	run chmod +x "$LOCAL_BIN/$name"
done
if [[ -d "$BIN_DIR/hooks" ]]; then
	run mkdir -p "$LOCAL_BIN/hooks"
	run cp -r "$BIN_DIR/hooks/." "$LOCAL_BIN/hooks/"
fi
ok "scripts + hooks installed"

# ── wallfliper app (wallfliper mode only) ──────────────────────────────────
if [[ "$WALLPAPER_SWITCHER" == "wallfliper" ]]; then
	info "Installing wallfliper app…"
	run mkdir -p "$LOCAL_SHARE"
	if [[ -d "$WALLFLIPER_TARGET" ]] && [[ -e "$WALLFLIPER_TARGET/core" ]]; then
		info "wallfliper already present — merging app files (keeps any extra assets)"
		run cp -r "$WALLFLIPER_DIR/." "$WALLFLIPER_TARGET/"
	else
		run cp -r "$WALLFLIPER_DIR" "$WALLFLIPER_TARGET"
	fi
	ok "wallfliper app installed"
else
	info "rofi mode — wallfliper app not installed (bin/wallpaper-rofi is used)"
fi

# ── curated wallpapers (defaults) ──────────────────────────────────────────
info "Installing default wallpapers…"
run mkdir -p "$WALLPAPER_TARGET"
run cp -rn "$WALLPAPERS_DIR/." "$WALLPAPER_TARGET/" 2>/dev/null || true
ok "wallpapers copied to $WALLPAPER_TARGET"

# ── wallpaper switcher choice ──────────────────────────────────────────────
# State files (theme engine/mode/wallpaper index) are runtime state — the theme
# scripts create and manage them with sensible defaults, so nothing to install.
run printf '%s\n' "$WALLPAPER_SWITCHER" > "$HOME_DIR/.current_wallpaper_switcher"
ok "wrote .current_wallpaper_switcher=$WALLPAPER_SWITCHER"

# ── GTK system theme symlinks (adw-gtk3-dark) ─────────────────────────────
ADW="/usr/share/themes/adw-gtk3-dark/gtk-4.0"
if [[ -d "$ADW" ]]; then
	for item in assets gtk.css gtk-dark.css; do
		run ln -sfn "$ADW/$item" "$CONFIG/gtk-4.0/$item"
	done
	ok "GTK theme symlinks applied"
else
	warn "adw-gtk3-dark not found — skipping GTK theme symlinks (install it for full theming)"
fi

# ── runtime matugen symlinks ───────────────────────────────────────────────
info "Recreating runtime theme links…"
run mkdir -p "$CONFIG/btop/themes" "$CONFIG/cava"
for entry in "${runtime_links[@]}"; do
	link="${entry%%|*}"; target="${entry##*|}"
	run ln -sfn "$target" "$link"
done

# ── portability: rewrite source-home paths to this machine ─────────────────
# Configs were authored with home /home/sijan. If this machine's HOME differs,
# point those paths at it. No-op when HOME == /home/sijan (keeps repo pristine).
OLD_HOME="/home/sijan"
if [[ "$HOME" != "$OLD_HOME" ]] && ! dry; then
	info "HOME differs from $OLD_HOME — rewriting absolute paths in live configs"
	for file in \
		"$CONFIG/fish/fish_variables" \
		"$CONFIG/btop/btop.conf" \
		"$CONFIG/gtk-3.0/bookmarks" \
		"$CONFIG/swayosd/config.toml" \
		"$CONFIG/swaync/style.css"; do
		if [[ -f "$file" ]] && grep -q "$OLD_HOME" "$file"; then
			sed -i "s|$OLD_HOME|$HOME|g" "$file"
			warn "updated $file (git will show this change — commit or 'git checkout' it)"
		fi
	done
fi

# ── regenerate theme from current wallpaper ────────────────────────────────
if dry; then
	info "(dry-run: skipping matugen regeneration)"
elif command -v matugen >/dev/null 2>&1; then
	if [[ -L "$GENERATED/wallpaper" ]]; then
		wp="$(readlink -f "$GENERATED/wallpaper")"
		info "generating theme from $wp"
		matugen image "$wp" || warn "matugen failed — run it manually: matugen image <wallpaper>"
	else
		warn "no current wallpaper link at $GENERATED/wallpaper — run: wallfliper --restore or matugen image <wallpaper>"
	fi
else
	warn "matugen not installed — colors won't generate until it is (then: matugen image <wallpaper>)"
fi

# ── optional package install ───────────────────────────────────────────────
if [[ "$DO_INSTALL" == true ]]; then
	info "Package install requested."
	if ! command -v pacman >/dev/null 2>&1; then
		err "--install supports Arch Linux only (pacman not found)"
		exit 1
	fi
	PACKAGES=(hyprland hypridle hyprlock hyprsunset waybar swaync swayosd kitty \
		matugen fish fastfetch starship tmux yazi btop cava gtk3 gtk4 adw-gtk3 \
		rofi awww wl-clip-persist cliphist polkit-gnome hyprpicker grim slurp playerctl \
		pipewire-pulse bluez ttf-space-grotesk)
	if [[ "$WALLPAPER_SWITCHER" == "wallfliper" ]]; then
		PACKAGES+=(pyside6 layer-shell-qt mpvpaper ffmpeg)
	fi
	if [[ "$ASSUME_YES" == false ]]; then
		echo -e "${YELLOW}This will install ${#PACKAGES[@]} packages. Continue? [y/N]${RESET} "
		read -r ans || true
		[[ "$ans" =~ ^[Yy]$ ]] || { info "aborted"; exit 0; }
	fi
	if command -v paru >/dev/null 2>&1; then
		run paru -S --needed "${PACKAGES[@]}"
	else
		run sudo pacman -S --needed --noconfirm "${PACKAGES[@]}"
	fi
	ok "packages installed"
fi

info "Done. Wallpapers at $WALLPAPER_TARGET — point the switcher at your collection if you prefer:"
info "    ~/.config/wallfliper/config.json  →  \"wallpaper_dir\": \"~/Pictures/wallpapers\""
info "Current wallpaper switcher: $WALLPAPER_SWITCHER (bin/wallpaper dispatches; change with --wallpaper-switcher)"
