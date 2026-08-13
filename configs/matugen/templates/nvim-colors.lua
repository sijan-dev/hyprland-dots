return {
	{
		"RRethy/base16-nvim",
		priority = 1000,
		config = function()
			local colors = {
				base00 = '{{ colors.background.default.hex }}',
				base01 = '{{ colors.surface_container_low.default.hex }}',
				base02 = '{{ colors.surface_container_high.default.hex }}',
				base03 = '{{ colors.outline_variant.default.hex }}',
				base04 = '{{ colors.surface_variant.default.hex }}',
				base05 = '{{ colors.on_background.default.hex }}',
				base06 = '{{ colors.on_surface_variant.default.hex }}',
				base07 = '{{ colors.on_surface.default.hex }}',
				base08 = '{{ colors.error.default.hex }}',
				base09 = '{{ colors.tertiary.default.hex }}',
				base0A = '{{ colors.tertiary_fixed.default.hex }}',
				base0B = '{{ colors.secondary.default.hex }}',
				base0C = '{{ colors.primary_fixed.default.hex }}',
				base0D = '{{ colors.primary.default.hex }}',
				base0E = '{{ colors.secondary_fixed.default.hex }}',
				base0F = '{{ colors.inverse_primary.default.hex }}',
			}

			local function apply_overrides()
				require('base16-colorscheme').setup(colors)

				vim.api.nvim_set_hl(0, 'Visual', {
					bg = colors.base02,
					fg = colors.base05,
					bold = true
				})
				vim.api.nvim_set_hl(0, 'Statusline', {
					bg = 'NONE',
					fg = colors.base05,
				})
				vim.api.nvim_set_hl(0, 'StatusLineNC', {
					bg = 'NONE',
					fg = colors.base03,
				})
				vim.api.nvim_set_hl(0, 'TabLine', { fg = colors.base03, bg = 'NONE' })
				vim.api.nvim_set_hl(0, 'TabLineFill', { fg = colors.base03, bg = 'NONE' })
				vim.api.nvim_set_hl(0, 'TabLineSel', { fg = colors.base0B, bg = 'NONE' })
				vim.api.nvim_set_hl(0, 'LineNr', { fg = colors.base03 })
				vim.api.nvim_set_hl(0, 'CursorLineNr', { fg = colors.base07, bold = true })

				vim.api.nvim_set_hl(0, 'Statement', {
					fg = colors.base07,
					bold = true
				})
				vim.api.nvim_set_hl(0, 'Keyword', { link = 'Statement' })
				vim.api.nvim_set_hl(0, 'Repeat', { link = 'Statement' })
				vim.api.nvim_set_hl(0, 'Conditional', { link = 'Statement' })

				vim.api.nvim_set_hl(0, 'Function', {
					fg = colors.base07,
					bold = true
				})
				vim.api.nvim_set_hl(0, 'Macro', {
					fg = colors.base07,
					italic = true
				})
				vim.api.nvim_set_hl(0, '@function.macro', { link = 'Macro' })

				vim.api.nvim_set_hl(0, 'Type', {
					fg = colors.base07,
					bold = true,
					italic = true
				})
				vim.api.nvim_set_hl(0, 'Structure', { link = 'Type' })

				vim.api.nvim_set_hl(0, 'String', {
					fg = colors.base0B,
					italic = true
				})

				vim.api.nvim_set_hl(0, 'Operator', { fg = colors.base04 })
				vim.api.nvim_set_hl(0, 'Delimiter', { fg = colors.base04 })
				vim.api.nvim_set_hl(0, '@punctuation.bracket', { link = 'Delimiter' })
				vim.api.nvim_set_hl(0, '@punctuation.delimiter', { link = 'Delimiter' })

				vim.api.nvim_set_hl(0, 'Comment', {
					fg = colors.base03,
					italic = true
				})
			end

			require('base16-colorscheme').setup(colors)
			apply_overrides()

			vim.api.nvim_create_autocmd("ColorScheme", {
				callback = function()
					if not vim.g._matugen_theme_applied then return end
					apply_overrides()
				end,
			})
			vim.g._matugen_theme_applied = true

			local current_file_path = vim.fn.stdpath("config") .. "/lua/plugins/colors.lua"
			if not _G._matugen_theme_watcher then
				local uv = vim.uv or vim.loop
				_G._matugen_theme_watcher = uv.new_fs_event()
				_G._matugen_theme_watcher:start(current_file_path, {}, vim.schedule_wrap(function()
					local ok, new_spec = pcall(dofile, current_file_path)
					if ok and new_spec and new_spec[1] and new_spec[1].config then
						new_spec[1].config()
						vim.api.nvim_exec_autocmds("ColorScheme", { modeline = false })
						pcall(require("astroui.status.heirline").refresh_colors)
						print("Theme reload")
					end
				end))
			end
		end
	}
}
