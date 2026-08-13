-- Window & workspace navigation

-- Fullscreen
hl.bind("SUPER + F", hl.dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }), { description = "Fullscreen" })

hl.config({
	dwindle = {
		preserve_split = true,
	},
})

-- Move focus
hl.bind("SUPER + H", hl.dsp.focus({ direction = "left" }))
hl.bind("SUPER + L", hl.dsp.focus({ direction = "right" }))
hl.bind("SUPER + K", hl.dsp.focus({ direction = "up" }))
hl.bind("SUPER + J", hl.dsp.focus({ direction = "down" }))
hl.bind("SUPER + LEFT", hl.dsp.focus({ direction = "left" }))
hl.bind("SUPER + RIGHT", hl.dsp.focus({ direction = "right" }))
hl.bind("SUPER + UP", hl.dsp.focus({ direction = "up" }))
hl.bind("SUPER + DOWN", hl.dsp.focus({ direction = "down" }))

-- Move active window
hl.bind("SUPER + SHIFT + H", hl.dsp.window.move({ direction = "left" }))
hl.bind("SUPER + SHIFT + L", hl.dsp.window.move({ direction = "right" }))
hl.bind("SUPER + SHIFT + J", hl.dsp.window.move({ monitor = "+1" }), { description = "Move to Next Monitor" })
hl.bind("SUPER + SHIFT + K", hl.dsp.window.move({ monitor = "-1" }), { description = "Move to Previous Monitor" })

-- Switch workspace focus between monitors
hl.bind("SUPER + bracketleft", hl.dsp.focus({ monitor = "-1" }), { description = "Previous Monitor" })
hl.bind("SUPER + bracketright", hl.dsp.focus({ monitor = "+1" }), { description = "Next Monitor" })

-- Switch workspaces with SUPER + [0-9]
for i = 1, 10 do
	local numberkey = { 10, 11, 12, 13, 14, 15, 16, 17, 18, 19 }
	hl.bind("SUPER + code:" .. numberkey[i], hl.dsp.focus({ workspace = i }))
end

-- Move active window to a workspace with SUPER + SHIFT + [0-9]
for i = 1, 10 do
	local numberkey = { 10, 11, 12, 13, 14, 15, 16, 17, 18, 19 }
	hl.bind("SUPER + SHIFT + code:" .. numberkey[i], hl.dsp.window.move({ workspace = i }))
end

-- Cycle workspaces
hl.bind("SUPER + Tab", hl.dsp.focus({ workspace = "e+1" }), { description = "Next Workspace" })
hl.bind("SUPER + SHIFT + Tab", hl.dsp.focus({ workspace = "e-1" }), { description = "Previous Workspace" })
hl.bind("SUPER + CTRL + RIGHT", hl.dsp.focus({ workspace = "e+1" }), { description = "Next Workspace" })
hl.bind("SUPER + CTRL + LEFT", hl.dsp.focus({ workspace = "e-1" }), { description = "Previous Workspace" })
hl.bind("SUPER + mouse_down", hl.dsp.focus({ workspace = "e+1" }), { description = "Next Workspace" })
hl.bind("SUPER + mouse_up", hl.dsp.focus({ workspace = "e-1" }), { description = "Previous Workspace" })

-- Resize active window: floating grows/shrinks, tiled adjusts split ratio
local function grow_window(factor)
	return function()
		local win = hl.get_active_window()
		local mon = hl.get_active_monitor()
		if win and win.floating and mon then
			hl.dispatch(hl.dsp.window.resize({ x = factor * mon.width, y = factor * mon.height, relative = true }))
			return
		end
		hl.dispatch(hl.dsp.layout(factor < 0 and "splitratio -0.1" or "splitratio +0.1"))
	end
end
hl.bind("SUPER + code:20", grow_window(-0.05), { repeating = true, description = "Shrink Window" }) -- "-" key
hl.bind("SUPER + code:21", grow_window(0.05), { repeating = true, description = "Grow Window" }) -- "=" / "+" key

-- Move/resize windows with SUPER + LMB/RMB
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })
