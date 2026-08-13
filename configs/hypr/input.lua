-- ██╗███╗   ██╗██████╗ ██╗   ██╗████████╗    ██████╗ ███████╗██╗   ██╗██╗ ██████╗███████╗███████╗
-- ██║████╗  ██║██╔══██╗██║   ██║╚══██╔══╝    ██╔══██╗██╔════╝██║   ██║██║██╔════╝██╔════╝██╔════╝
-- ██║██╔██╗ ██║██████╔╝██║   ██║   ██║       ██║  ██║█████╗  ██║   ██║██║██║     █████╗  ███████╗
-- ██║██║╚██╗██║██╔═══╝ ██║   ██║   ██║       ██║  ██║██╔══╝  ╚██╗ ██╔╝██║██║     ██╔══╝  ╚════██║
-- ██║██║ ╚████║██║     ╚██████╔╝   ██║       ██████╔╝███████╗ ╚████╔╝ ██║╚██████╗███████╗███████║
-- ╚═╝╚═╝  ╚═══╝╚═╝      ╚═════╝    ╚═╝       ╚═════╝ ╚══════╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝╚══════╝

-- See https://wiki.hypr.land/Configuring/Variables/--input

-- hide cursor after n sec
hl.config({
	cursor = {
		inactive_timeout = 1,
	},
	animations = {
		enabled = true,
	},

	input = {
		-- Change speed of keyboard repeat
		repeat_rate = 35,
		repeat_delay = 300,

		follow_mouse = 1,
		numlock_by_default = true,

		-- Increase sensitity for mouse/trackpack (default: 0)
		sensitivity = 0.40, --0.35

		touchpad = {
			-- Use natural (inverse) scrolling
			natural_scroll = true, --false

			-- Use two-finger clicks for right-click instead of lower-right corner
			-- clickfinger_behavior = true

			-- Control the speed of your scrolling
			scroll_factor = 0.4,
		},
	},
	misc = {
		key_press_enables_dpms = true, -- key press will trigger wake
		mouse_move_enables_dpms = true, -- mouse move will trigger wake
	},
})

hl.gesture({
	fingers = 3,
	direction = "horizontal",
	action = "workspace",
})

hl.gesture({
	fingers = 3,
	direction = "up",
	action = function()
		hl.exec_cmd("vicinae toggle")
	end,
})

hl.gesture({
	fingers = 3,
	direction = "down",
	action = function()
		hl.exec_cmd("swaync-client -t -sw")
	end,
})

hl.gesture({
	fingers = 4,
	direction = "right",
	action = function()
		local monitor = hl.get_active_monitor()
		hl.exec_cmd("swayosd-client --monitor " .. monitor.name .. " --output-volume raise")
	end,
})

hl.gesture({
	fingers = 4,
	direction = "left",
	action = function()
		local monitor = hl.get_active_monitor()
		hl.exec_cmd("swayosd-client --monitor " .. monitor.name .. " --output-volume lower")
	end,
})

hl.gesture({
	fingers = 3,
	direction = "pinchin",
	action = function()
		hl.exec_cmd("~/.local/bin/wallpaper")
	end,
})

-- Scroll nicely in the terminal
hl.window_rule({
	match = {
		class = "(kitty)",
	},
	scroll_touchpad = 1.5,
})
