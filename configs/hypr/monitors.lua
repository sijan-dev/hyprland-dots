-- ███╗   ███╗ ██████╗ ███╗   ██╗██╗████████╗ ██████╗ ██████╗ ███████╗
-- ████╗ ████║██╔═══██╗████╗  ██║██║╚══██╔══╝██╔═══██╗██╔══██╗██╔════╝
-- ██╔████╔██║██║   ██║██╔██╗ ██║██║   ██║   ██║   ██║██████╔╝███████╗
-- ██║╚██╔╝██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║██╔══██╗╚════██║
-- ██║ ╚═╝ ██║╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝██║  ██║███████║
-- ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝

-- See https://wiki.hyprland.org/Configuring/Monitors/
-- List current monitors and resolutions possible: hyprctl monitors
-- Format:
--       hl.monitor({
--         output = "...",
--         mode = "...",
--         position = "...",
--         scale = ...,
--       })
-- You must relaunch Hyprland after changing any envs

-- Optimized for retina-class 2x displays, like 13" 2.8K, 27" 5K, 32" 6K.
-- hl.env("GDK_SCALE","2")
-- hl.monitor({
--   output = "",
--   mode = "preferred",
--   position = "auto",
--   scale = 1,
-- })

-- Good compromise for 27" or 32" 4K monitors (but fractional!)
-- hl.env("GDK_SCALE","1.75")
-- hl.monitor({
--   output = "",
--   mode = "preferred",
--   position = "auto",
--   scale = 1.666667,
-- })

-- Straight 1x setup for low-resolution displays like 1080p or 1440p
-- hl.env("GDK_SCALE", "1")
-- hl.monitor({
-- 	output = "HDMI-A-1",
-- 	mode = "1920x1080@100",
-- 	position = "auto",
-- 	scale = 1.2,
-- })

-- Example for Framework 13 w/ 6K XDR Apple display
-- hl.monitor({
--   output = "DP-5",
--   mode = "6016x3384@60",
--   position = "auto",
--   scale = 2,
-- })
-- hl.monitor({
--   output = "eDP-1",
--   mode = "2880x1920@120",
--   position = "auto",
--   scale = 2,
-- })

hl.monitor({
	output = "HDMI-A-1",
	mode = "1920x1080@100",
	position = "0x0",
	scale = 1.0,
})

hl.monitor({
	output = "eDP-1",
	mode = "1366x768@60",
	position = "1920x0",
	scale = 1,
})

--#####  --------------------------------  ######
--#####   WORKSPACE → MONITOR ASSIGNMENT   ######
--#####  --------------------------------  ######

hl.workspace_rule({ workspace = "1", monitor = "HDMI-A-1" })
hl.workspace_rule({ workspace = "2", monitor = "HDMI-A-1" })
hl.workspace_rule({ workspace = "3", monitor = "HDMI-A-1" })
hl.workspace_rule({ workspace = "4", monitor = "HDMI-A-1" })
hl.workspace_rule({ workspace = "5", monitor = "HDMI-A-1" })

hl.workspace_rule({ workspace = "6", monitor = "eDP-1" })
hl.workspace_rule({ workspace = "7", monitor = "eDP-1" })
hl.workspace_rule({ workspace = "8", monitor = "eDP-1" })
hl.workspace_rule({ workspace = "9", monitor = "eDP-1" })
hl.workspace_rule({ workspace = "10", monitor = "eDP-1" })
--

--#####  --------------------------------  ######
--#####      WORKSPACE → APP ASSIGNMENT    ######
--#####  --------------------------------  ######
-- hl.window_rule({
--   match = {
--     class = "(dev.zed.Zed)"
--   },
--   workspace = "2",
-- })
-- hl.window_rule({
--   match = {
--     class = "^(brave-perplexity.ai__-Default)$"
--   },
--   workspace = "3",
-- })
-- hl.window_rule({
--   match = {
--     class = "^(brave-web.whatsapp.com__-Default)$"
--   },
--   workspace = "6",
-- })
-- hl.window_rule({
--   match = {
--     class = "(org.telegram.desktop)"
--   },
--   workspace = "6",
-- })
-- hl.window_rule({
--   match = {
--     class = "^(brave-app.todoist.com__-Default)$"
--   },
--   workspace = "7",
-- })
-- hl.window_rule({
--   match = {
--     class = "(obsidian)"
--   },
--   workspace = "8",
-- })

--#####  --------------------------------  ######
