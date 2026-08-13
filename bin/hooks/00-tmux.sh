#!/bin/bash
# Generate tmux theme colors from current kitty colors

THEME_DIR="${CURRENT_LINK:-$HOME/.config/matugen/generated}"
KITTY_COLORS="$THEME_DIR/kitty/colors.conf"
TMUX_COLORS="$THEME_DIR/tmux/tmux-colors.conf"

[[ -f "$KITTY_COLORS" ]] || exit 0

mkdir -p "$(dirname "$TMUX_COLORS")"

while IFS=' ' read -r key value; do
    [[ "$key" == \#* ]] && continue
    [[ -z "$key" ]] && continue
    declare "$key=$value"
done < "$KITTY_COLORS"

: "${background:=#1a1a1a}"
: "${foreground:=#ffffff}"
: "${color6:=#00ffff}"

cat > "$TMUX_COLORS" <<TMUXEOF
# ╭─ ♪ Sizon ─╮
# │  tmux theme   │
# ╰──────────────╯
# Generated from kitty colors

set -g message-style "fg=$foreground,bg=$color8"
set -g message-command-style "fg=$foreground,bg=$color8"
set -g pane-border-style "fg=$color8"
set -g pane-active-border-style "fg=$color6"
set -g status-style "fg=$foreground,bg=$background"
set -g status-bg "$background"
set -g status-left "#[fg=$background,bg=$color6,bold] #S #[fg=$color6,bg=$background]"
set -g status-right "#[fg=$color8]%H:%M"
setw -g window-status-activity-style "underscore,fg=$color6,bg=$background"
setw -g window-status-separator ""
setw -g window-status-style "NONE,fg=$color8,bg=$background"
setw -g window-status-format "#[fg=$color8] #I #[fg=$color8]#W "
setw -g window-status-current-format "#[fg=$background,bg=$color6] #I #[fg=$background,bg=$color6]#W "
set -g mode-style "fg=$background,bg=$color6"
TMUXEOF

# Reload tmux if inside a session
tmux source-file "$TMUX_COLORS" 2>/dev/null || true
