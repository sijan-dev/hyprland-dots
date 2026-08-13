-- Fix some dragging issues with XWayland
hl.window_rule({
	match = {
		class = "^$",
		title = "^$",
		xwayland = true,
		float = false,
		fullscreen = false,
		pin = false,
	},
	no_focus = true,
})

-- Force Polkit Auth to open on active workspace
hl.window_rule({
	match = {
		class = "polkit-gnome-authentication-agent-1",
	},
	workspace = "unset",
})

-- Prevent apps from auto-maximizing themselves
hl.window_rule({
	match = {
		class = ".*",
	},
	suppress_event = "maximize",
})

-- Opacity is controlled globally by ~/.local/bin/togpacity (SUPER+BACKSPACE):
-- toggles decoration opacity between 1.0 (opaque) and 0.9 (translucent).

hl.layer_rule({
	match = {
		namespace = "selection",
	},
	no_anim = true,
})

hl.layer_rule({
	match = { namespace = "vicinae" },
	name = "vicinae-blur",
	blur = true,
	ignore_alpha = 0,
})

hl.layer_rule({
	match = { namespace = "vicinae" },
	name = "vicinae-no-animation",
	no_anim = true,
})

-- =============================================================================
-- Floating Windows
-- =============================================================================

-- Apply float/center/size to anything tagged as a floating window
hl.window_rule({
	match = {
		tag = "floating-window",
	},
	float = true,
	center = true,
	size = "800 600",
})

-- Tag floating apps by class
hl.window_rule({
	match = {
		class = "(blueman-manager|xdg-desktop-portal-gtk|localsend|Wiremix|nmgui)",
	},
	tag = "+floating-window",
	workspace = "unset",
})

-- Tag floating apps by title
hl.window_rule({
	match = {
		title = "^(.*Network Manager.*)$",
	},
	tag = "+floating-window",
})
hl.window_rule({
	match = {
		title = "(share)",
	},
	tag = "+floating-window",
})

-- Easyeffects (music equalizer)
hl.window_rule({
	match = {
		class = "com.github.wmmm.easyeffects",
	},
	float = true,
	center = true,
	size = "950 850",
})

-- =============================================================================
-- Steam
-- =============================================================================

hl.window_rule({
	match = {
		class = "steam",
		title = "Steam",
	},
	float = true,
	center = true,
	size = "1100 700",
	opacity = "1 override 1 override",
	idle_inhibit = "fullscreen",
})

hl.window_rule({
	match = {
		class = "steam",
		title = "Friends List",
	},
	float = true,
	center = true,
	opacity = "1 override 1 override",
	size = "460 800",
})

-- =============================================================================
-- Miscellaneous
-- =============================================================================

-- Hide Bitwarden from screen share
hl.window_rule({
	match = {
		class = "^(Bitwarden)$",
	},
	no_screen_share = true,
})

-- feh (image viewer)
hl.window_rule({
	match = {
		class = "feh",
	},
	float = true,
	center = true,
	size = "1280 720",
	opacity = "1 override 1 override",
})

-- mpv (video player)
hl.window_rule({
	match = {
		class = "mpv",
	},
	float = true,
	center = true,
	size = "1280 720",
	opacity = "1 override 1 override",
})

-- =============================================================================
-- Browsers
-- =============================================================================

-- Tag browser types.
-- brave.* catches brave-browser and all webapps (brave-youtube.com__-Default etc.)
hl.window_rule({
	match = {
		class = "((google-)?[cC]hrom(e|ium)|brave.*|[mM]icrosoft-edge|Vivaldi-stable|helium)",
	},
	tag = "+chromium-based-browser",
})
hl.window_rule({
	match = {
		class = "([fF]irefox|zen|librewolf)",
	},
	tag = "+firefox-based-browser",
})

-- Force chromium-based browsers into a tile to deal with --app bug
hl.window_rule({
	match = {
		tag = "chromium-based-browser",
	},
	tile = true,
})

hl.window_rule({
	match = {
		tag = "firefox-based-browser",
	},
	opacity = "1 override 1 override",
})

-- Video sites get blur like other browser tabs

-- =============================================================================
-- Picture-in-Picture
-- =============================================================================

hl.window_rule({
	match = {
		title = "(Picture.?in.?[Pp]icture)",
	},
	tag = "+pip",
})
hl.window_rule({
	match = {
		tag = "pip",
	},
	float = true,
	pin = true,
	size = "600 338",
	keep_aspect_ratio = true,
	border_size = 0,
	opacity = "1 override 1 override",
})

-- =============================================================================
-- Special Workspaces
-- =============================================================================

hl.workspace_rule({ workspace = "special:scratchpad", on_created_empty = "kitty --title scratchpad" })
hl.window_rule({
	match = { title = "scratchpad" },
	float = true,
	center = true,
	size = "850 600",
})

hl.workspace_rule({ workspace = "special:sysmon", on_created_empty = "kitty --title sysmon -e btop" })
hl.window_rule({
	match = { title = "sysmon" },
	float = true,
	center = true,
	size = "850 600",
})

hl.workspace_rule({ workspace = "special:yazi", on_created_empty = "kitty --title yazi -e yazi" })
hl.window_rule({
	match = { title = "yazi" },
	float = true,
	center = true,
	size = "850 600",
})

hl.window_rule({
	match = { title = "wlctl" },
	float = true,
	center = true,
	size = "870 550",
})

hl.workspace_rule({ workspace = "special:bluetooth", on_created_empty = "kitty --title bluetooth -e bluetui" })
hl.window_rule({
	match = { title = "bluetooth" },
	float = true,
	center = true,
	size = "870 550",
})
