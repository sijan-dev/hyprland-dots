-- ███╗   ███╗███████╗██████╗ ██╗ █████╗ 
-- ████╗ ████║██╔════╝██╔══██╗██║██╔══██╗
-- ██╔████╔██║█████╗  ██║  ██║██║███████║
-- ██║╚██╔╝██║██╔══╝  ██║  ██║██║██╔══██║
-- ██║ ╚═╝ ██║███████╗██████╔╝██║██║  ██║
-- ╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝╚═╝  ╚═╝
                                      
-- Laptop multimedia keys for volume and LCD brightness (with OSD)
hl.bind("XF86AudioRaiseVolume", function()
  local monitor = hl.get_active_monitor()
  hl.exec_cmd("swayosd-client --monitor " .. monitor.name .. " --output-volume raise") end,
  { repeating = true, locked = true, description = "Raise volume"} )

hl.bind("ALT + XF86AudioRaiseVolume", function()
  local monitor = hl.get_active_monitor()
  hl.exec_cmd("swayosd-client --monitor " .. monitor.name .. " --output-volume +1") end,
  { repeating = true, locked = true, description = "Raise volume (precise)"} )

hl.bind("XF86AudioLowerVolume", function()
  local monitor = hl.get_active_monitor()
  hl.exec_cmd("swayosd-client --monitor " .. monitor.name .. " --output-volume lower") end,
  { repeating = true, locked = true, description = "Lower volume"} )

hl.bind("ALT + XF86AudioLowerVolume", function()
  local monitor = hl.get_active_monitor()
  hl.exec_cmd("swayosd-client --monitor " .. monitor.name .. " --output-volume -1") end,
  { repeating = true, locked = true, description = "Lower volume (precise)"} )

hl.bind("XF86AudioMute", function()
  local monitor = hl.get_active_monitor()
  hl.exec_cmd("swayosd-client --monitor " .. monitor.name .. " --output-volume mute-toggle") end,
  { repeating = true, locked = true, description = "Mute audio"} )

hl.bind("XF86AudioMicMute", function()
  local monitor = hl.get_active_monitor()
  hl.exec_cmd("swayosd-client --monitor " .. monitor.name .. " --input-volume mute-toggle") end,
  { repeating = true, locked = true, description = "Mute microphone"} )

hl.bind("XF86MonBrightnessUp", function()
  local monitor = hl.get_active_monitor()
  hl.exec_cmd("swayosd-client --monitor " .. monitor.name .. " --brightness raise") end,
  { repeating = true, locked = true, description = "Raise brightness"} )

hl.bind("ALT + XF86MonBrightnessUp", function()
  local monitor = hl.get_active_monitor()
  hl.exec_cmd("swayosd-client --monitor " .. monitor.name .. " --brightness +1") end,
  { repeating = true, locked = true, description = "Raise brightness (precise)"} )

hl.bind("XF86MonBrightnessDown", function()
  local monitor = hl.get_active_monitor()
  hl.exec_cmd("swayosd-client --monitor " .. monitor.name .. " --brightness lower") end,
  { repeating = true, locked = true, description = "Lower brightness"} )

hl.bind("ALT + XF86MonBrightnessDown", function()
  local monitor = hl.get_active_monitor()
  hl.exec_cmd("swayosd-client --monitor " .. monitor.name .. " --brightness -1") end,
  { repeating = true, locked = true, description = "Lower brightness (precise)"} )

hl.bind("ALT + period", hl.dsp.exec_cmd("playerctl next"), { description = "Next track" })
hl.bind("ALT + comma", hl.dsp.exec_cmd("playerctl prev"), { description = "Previous track" })



-- mpc
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("mpc next"), {  locked = true, description = "Next track"} )
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("mpc toggle"), {  locked = true, description = "Play/Pause music"} )
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("mpc toggle"), {  locked = true, description = "Play/Pause music"} )
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("mpc prev"), {  locked = true, description = "Previous track"} )


