-- ██╗      ██████╗  ██████╗ ██╗  ██╗       ██╗       ███████╗███████╗███████╗██╗
-- ██║     ██╔═══██╗██╔═══██╗██║ ██╔╝       ██║       ██╔════╝██╔════╝██╔════╝██║
-- ██║     ██║   ██║██║   ██║█████╔╝     ████████╗    █████╗  █████╗  █████╗  ██║
-- ██║     ██║   ██║██║   ██║██╔═██╗     ██╔═██╔═╝    ██╔══╝  ██╔══╝  ██╔══╝  ██║
-- ███████╗╚██████╔╝╚██████╔╝██║  ██╗    ██████║      ██║     ███████╗███████╗███████╗
-- ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝    ╚═════╝      ╚═╝     ╚══════╝╚══════╝╚══════╝

-- Colors from matugen
package.path = package.path .. ";" .. os.getenv("HOME") .. "/.config/matugen/generated/hypr/theme/?.lua"
require("colors")

-- Opacity toggle state from ~/.local/bin/togpacity (defaults to opaque)
local opacity = 1.0
local opacity_state = io.open(os.getenv("HOME") .. "/.config/hypr/opacity.state", "r")
if opacity_state then
	opacity = tonumber(opacity_state:read("*a")) or 1.0
	opacity_state:close()
end

-- https://wiki.hyprland.org/Configuring/Variables/#general
hl.config({
	general = {
		-- gaps_in = 3,
		-- gaps_out = 6,
		-- border_size = 2,
		gaps_in = 1,
		gaps_out = 1,
		border_size = 1,
		col = {
			active_border = secondary,
			inactive_border = outline_variant,
		},
		resize_on_border = true,

		-- Change to niri-like side-scrolling layout
		-- layout = scrolling
	},

	-- https://wiki.hyprland.org/Configuring/Variables/#decoration
	decoration = {
		rounding = 3,
		active_opacity = opacity,
		inactive_opacity = opacity,

		blur = {
			enabled = true,
			size = 2,
			passes = 5,
			ignore_opacity = true,
			noise = 0.0817,
			contrast = 0.8916,
			brightness = 1.172,
			xray = false,
			popups = true,
		},
	},
	misc = {
		disable_hyprland_logo = true,
		-- force_default_wallpaper = 0,  # Disables anime mascot wallpapers
		disable_splash_rendering = true,
		focus_on_activate = true,
		anr_missed_pings = 3,
		on_focus_under_fullscreen = 1,
	},
})
-- App launcher
hl.layer_rule({
	match = {
		namespace = "rofi",
	},
	blur = true,
	ignore_alpha = 0,
	animation = "slide bottom",
})

hl.layer_rule({
	match = {
		namespace = "waybar",
	},
	blur = true,
	ignore_alpha = 0,
})

hl.layer_rule({
	match = {
		namespace = "swayosd",
	},
	blur = true,
	ignore_alpha = 0,
})

hl.layer_rule({
	match = {
		namespace = "swaync-control-center",
	},
	blur = false,
	ignore_alpha = 0,
	animation = "slide right",
})

hl.layer_rule({
	match = {
		namespace = "swaync-notification-window",
	},
	blur = false,
	ignore_alpha = 0,
})

-- Style Gum confirm to match terminal theme
hl.env("GUM_CONFIRM_PROMPT_FOREGROUND", "6") -- Cyan
hl.env("GUM_CONFIRM_SELECTED_FOREGROUND", "0") -- Black
hl.env("GUM_CONFIRM_SELECTED_BACKGROUND", "2") -- Green
hl.env("GUM_CONFIRM_UNSELECTED_FOREGROUND", "0") -- Black
hl.env("GUM_CONFIRM_UNSELECTED_BACKGROUND", "8") -- Dark Grey
