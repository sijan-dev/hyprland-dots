#!/bin/bash
# Reload colorscheme in running nvim instances

CURRENT_LINK="${CURRENT_LINK:-$HOME/.config/matugen/generated}"
THEME_FILE="$CURRENT_LINK/nvim/theme.lua"

[[ -f "$THEME_FILE" ]] || exit 0
touch "$THEME_FILE"

# Try sending a remote command to a running nvim instance
# (requires nvim started with --listen)
for socket in /tmp/nvim*; do
  [[ -S "$socket" ]] || continue
  nvim --server "$socket" --remote-send '<Esc>:lua pcall(vim.cmd.colorscheme, vim.g.colors_name or "default")<CR>' 2>/dev/null
done

# Fallback for nvim instances without --listen:
# also try via tmux if inside one
if tmux list-panes -F '#{pane_current_command}' 2>/dev/null | grep -q nvim; then
  tmux send-keys -t "$(tmux list-panes -F '#{pane_id}:#{pane_current_command}' | grep nvim | head -1 | cut -d: -f1)" Escape ':lua pcall(vim.cmd.colorscheme, vim.g.colors_name or "default")' Enter
fi
