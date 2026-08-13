-- Keybinds
local terminal = "kitty"
local browser = "chromium"
local ScrDir = "~/.local/bin"

-- Launchers
hl.bind(
	"SUPER + Return",
	hl.dsp.exec_cmd("uwsm-app -- " .. terminal .. " --dir='$(cwd-terminal)'"),
	{ description = "Terminal" }
)
hl.bind("SUPER + B", hl.dsp.exec_cmd("uwsm-app -- " .. browser), { description = "Browser" })
hl.bind("SUPER + C", hl.dsp.exec_cmd("code-oss"), { description = "Code" })
hl.bind("SUPER + O", hl.dsp.exec_cmd("obsidian"), { description = "Obsidian" })
hl.bind("SUPER + N", hl.dsp.exec_cmd("uwsm-app -- kitty nvim"), { description = "Neovim" })
hl.bind("SUPER + M", hl.dsp.exec_cmd("kitty --title youtube-tui -e youtube-tui"), { description = "YouTube TUI" })
hl.bind("SUPER + E", hl.dsp.exec_cmd("nautilus"), { description = "Nautilus" })
hl.bind("SUPER + SPACE", hl.dsp.exec_cmd("vicinae toggle"), { description = "App launcher" })
hl.bind("SUPER + I", hl.dsp.workspace.toggle_special("yazi"), { description = "Yazi" })

-- Special workspaces
hl.bind("SUPER + S", hl.dsp.workspace.toggle_special("scratchpad"))
hl.bind(
	"SUPER + SHIFT + S",
	hl.dsp.window.move({ workspace = "special:scratchpad" }),
	{ description = "Move window to scratchpad" }
)
hl.bind("SUPER + W", hl.dsp.workspace.toggle_special("sysmon"))
hl.bind("ALT + 1", hl.dsp.workspace.toggle_special("bluetooth"), { description = "Bluetooth" })
hl.bind("ALT + 2", hl.dsp.exec_cmd(ScrDir .. "/wlctl-run"), { description = "Wi-Fi Setup (wlctl)" })

-- Window operations
hl.bind("SUPER + Q", hl.dsp.window.close())
hl.bind(
	"SUPER + D",
	hl.dsp.window.fullscreen({ mode = "maximized", action = "toggle" }),
	{ description = "Maximize Window" }
)
hl.bind("SUPER + SHIFT + Return", function()
	hl.dispatch(hl.dsp.window.float({ action = "toggle" }))
	local win = hl.get_active_window()
	local mon = hl.get_active_monitor()
	if win and win.floating and mon then
		hl.dispatch(hl.dsp.window.resize({ x = mon.width / 2, y = mon.height / 2 }))
		hl.dispatch(hl.dsp.window.center())
	end
end, { description = "Toggle Floating (50/50)" })
hl.bind("SUPER + ALT + K", hl.dsp.exec_cmd("hyprctl kill"), { description = "Kill Application" })

-- Utility launchers
hl.bind(
	"SUPER + V",
	hl.dsp.exec_cmd("vicinae vicinae://launch/clipboard/history"),
	{ description = "Clipboard history" }
)
hl.bind(
	"CTRL + ALT + SPACE",
	hl.dsp.exec_cmd("~/.local/bin/wallpaper --random"),
	{ description = "Random wallpaper + matugen" }
)
hl.bind("ALT + SPACE", hl.dsp.exec_cmd(ScrDir .. "/wallpaper"), { description = "Wallpaper picker" })
hl.bind("SUPER + ALT + RIGHT", hl.dsp.exec_cmd(ScrDir .. "/wallpaper --next"), { description = "Next wallpaper" })
hl.bind("SUPER + ALT + LEFT", hl.dsp.exec_cmd(ScrDir .. "/wallpaper --prev"), { description = "Previous wallpaper" })

-- System toggles
hl.bind("SUPER + SHIFT + W", hl.dsp.exec_cmd(ScrDir .. "/toggle-waybar"), { description = "Toggle Waybar" })
hl.bind("SUPER + SHIFT + A", hl.dsp.exec_cmd(ScrDir .. "/theme-switch toggle"), { description = "Toggle Matugen/Darky theme" })

hl.bind("SUPER + SHIFT + L", hl.dsp.exec_cmd(ScrDir .. "/toggle-light-dark"), { description = "Toggle Light/Dark theme" })
hl.bind("SUPER + CTRL + I", hl.dsp.exec_cmd(ScrDir .. "/toggle-idle"), { description = "Toggle Idle/Lock" })
hl.bind("SUPER + BACKSPACE", hl.dsp.exec_cmd(ScrDir .. "/togpacity"), { description = "Toggle Global Transparency" })
hl.bind("SUPER + semicolon", hl.dsp.exec_cmd(ScrDir .. "/adjust-blur up"), { description = "Increase Blur" })
hl.bind("SUPER + apostrophe", hl.dsp.exec_cmd(ScrDir .. "/adjust-blur down"), { description = "Decrease Blur" })
hl.bind("SUPER + SHIFT + BACKSPACE", hl.dsp.exec_cmd(ScrDir .. "/adjust-blur reset"), { description = "Reset Blur" })
hl.bind("ALT + N", hl.dsp.exec_cmd("swaync-client -t -sw"), { description = "Notification Centre" })

-- Power
-- hl.bind("ALT + L", hl.dsp.exec_cmd(ScrDir .. "/lock-screen"), { description = "Lock screen" })

-- Screenshots
hl.bind("PRINT", hl.dsp.exec_cmd(ScrDir .. "/screenshot smart clipboard"), { description = "Screenshot to clipboard" })
hl.bind(
	"SUPER + P",
	hl.dsp.exec_cmd(ScrDir .. "/screenshot smart clipboard"),
	{ description = "Screenshot to clipboard" }
)
hl.bind("SUPER + SHIFT + P", hl.dsp.exec_cmd(ScrDir .. "/screenshot"), { description = "Screenshot with editing" })
hl.bind(
	"SUPER + SHIFT + PRINT",
	hl.dsp.exec_cmd(ScrDir .. "/screenshot smart clipboard"),
	{ description = "Screenshot to clipboard" }
)
hl.bind("SUPER + ALT + P", hl.dsp.exec_cmd("pkill hyprpicker || hyprpicker -a"), { description = "Color Picker" })

-- Screen recording
hl.bind("SUPER + R", hl.dsp.exec_cmd(ScrDir .. "/screenrecord --with-desktop-audio"), { description = "Record Screen" })
hl.bind(
	"SUPER + SHIFT + R",
	hl.dsp.exec_cmd(ScrDir .. "/screenrecord --with-microphone-audio --with-webcam"),
	{ description = "Record + Mic + Webcam" }
)
