-- Patina: window chrome that follows the current theme.
-- Numbers live in ~/.config/omarchy/patina.toml. This file is a no-op when
-- applied = false, so Style → Patina can restore the stock theme look.
-- manage_* = false skips keys the user already set in looknfeel.lua.

local home = os.getenv("HOME") or ""
local tweaks_path = home .. "/.config/omarchy/patina.toml"
local colors_path = home .. "/.local/state/omarchy/current/theme/colors.toml"

local function parse_simple_toml(path)
  local file = io.open(path, "r")
  if not file then
    return {}
  end

  local root = {}
  local section = root
  for raw_line in file:lines() do
    local line = raw_line:match("^%s*(.-)%s*$") or ""
    if line ~= "" and not line:find("^#") then
      local name = line:match("^%[([%w_-]+)%]$")
      if name then
        root[name] = root[name] or {}
        section = root[name]
      else
        local key, raw = line:match("^([%w_.-]+)%s*=%s*(.-)%s*$")
        if key then
          if not raw:match("^['\"]") then
            raw = raw:gsub("%s+#.*$", "")
          end
          raw = raw:match("^%s*(.-)%s*$") or raw
          local value
          if raw == "true" then
            value = true
          elseif raw == "false" then
            value = false
          elseif raw:match("^['\"].*['\"]$") then
            value = raw:sub(2, -2)
          else
            value = tonumber(raw)
            if value == nil then
              value = raw
            end
          end
          section[key] = value
        end
      end
    end
  end
  file:close()
  return root
end

local function parse_hex(value)
  if type(value) ~= "string" then
    return nil
  end
  local hex = value:gsub("^#", ""):gsub("^0x", "")
  if #hex == 8 then
    hex = hex:sub(1, 6)
  end
  if #hex == 3 then
    hex = hex:sub(1, 1):rep(2) .. hex:sub(2, 2):rep(2) .. hex:sub(3, 3):rep(2)
  end
  if #hex ~= 6 then
    return nil
  end
  local r = tonumber(hex:sub(1, 2), 16)
  local g = tonumber(hex:sub(3, 4), 16)
  local b = tonumber(hex:sub(5, 6), 16)
  if not r or not g or not b then
    return nil
  end
  return { r = r / 255, g = g / 255, b = b / 255 }
end

local function rgb_to_hls(r, g, b)
  local maxc = math.max(r, g, b)
  local minc = math.min(r, g, b)
  local l = (minc + maxc) / 2
  if minc == maxc then
    return 0, l, 0
  end
  local s
  if l <= 0.5 then
    s = (maxc - minc) / (maxc + minc)
  else
    s = (maxc - minc) / (2.0 - maxc - minc)
  end
  local rc = (maxc - r) / (maxc - minc)
  local gc = (maxc - g) / (maxc - minc)
  local bc = (maxc - b) / (maxc - minc)
  local h
  if r == maxc then
    h = bc - gc
  elseif g == maxc then
    h = 2.0 + rc - bc
  else
    h = 4.0 + gc - rc
  end
  h = (h / 6.0) % 1.0
  if h < 0 then
    h = h + 1
  end
  return h, l, s
end

local function _hls_v(m1, m2, hue)
  hue = hue % 1.0
  if hue < 0 then
    hue = hue + 1
  end
  if hue < 1 / 6 then
    return m1 + (m2 - m1) * hue * 6
  end
  if hue < 0.5 then
    return m2
  end
  if hue < 2 / 3 then
    return m1 + (m2 - m1) * (2 / 3 - hue) * 6
  end
  return m1
end

local function hls_to_rgb(h, l, s)
  if s == 0 then
    return l, l, l
  end
  local m2
  if l <= 0.5 then
    m2 = l * (1.0 + s)
  else
    m2 = l + s - (l * s)
  end
  local m1 = 2.0 * l - m2
  return _hls_v(m1, m2, h + 1 / 3), _hls_v(m1, m2, h), _hls_v(m1, m2, h - 1 / 3)
end

local function mix(a, b, t)
  return {
    r = a.r * (1 - t) + b.r * t,
    g = a.g * (1 - t) + b.g * t,
    b = a.b * (1 - t) + b.b * t,
  }
end

local function saturate(color)
  local h, l, s = rgb_to_hls(color.r, color.g, color.b)
  local r, g, b = hls_to_rgb(h, l, 1.0)
  return { r = r, g = g, b = b, _s = s }
end

local function to_byte(channel)
  return math.max(0, math.min(255, math.floor(channel * 255 + 0.5)))
end

local function rgb_string(color)
  return string.format("rgb(%02x%02x%02x)", to_byte(color.r), to_byte(color.g), to_byte(color.b))
end

local function rgba_string(color, alpha)
  local a = math.max(0, math.min(255, math.floor((alpha or 1) * 255 + 0.5)))
  return string.format("rgba(%02x%02x%02x%02x)", to_byte(color.r), to_byte(color.g), to_byte(color.b), a)
end

local tweaks = parse_simple_toml(tweaks_path)
local theme = parse_simple_toml(colors_path)
local applied = tweaks.applied
if applied == nil then
  applied = true
end

if not applied then
  return
end

local function preset_rounding()
  local name = tweaks.corners
  if name == "sharp" then
    return 0
  end
  if name == "round" then
    return 12
  end
  if name == "soft" then
    return 6
  end
  return 6
end

local rounding = tweaks.rounding or preset_rounding()
local border_size = tweaks.border_size or 2
if border_size < 1 then
  border_size = 1
end
if border_size > 16 then
  border_size = 16
end

local function preset_gap(kind)
  local name = tweaks.gaps
  if name == "default" then
    if kind == "in" then
      return 5
    end
    return 10
  end
  if name == "loose" then
    if kind == "in" then
      return 10
    end
    return 20
  end
  return 2
end

local gap_in = preset_gap("in")
local gap_out = preset_gap("out")
local gaps_out = {
  top = tweaks.gaps_out_top or gap_out,
  right = tweaks.gaps_out_right or gap_out,
  bottom = tweaks.gaps_out_bottom or gap_out,
  left = tweaks.gaps_out_left or gap_out,
}
local gaps_in = {
  top = tweaks.gaps_in_top or gap_in,
  right = tweaks.gaps_in_right or gap_in,
  bottom = tweaks.gaps_in_bottom or gap_in,
  left = tweaks.gaps_in_left or gap_in,
}
local inactive_mix = tweaks.inactive_mix or 0.15
local saturate_accent = tweaks.saturate_accent
if saturate_accent == nil then
  saturate_accent = true
end
local glow_enabled = tweaks.glow
if glow_enabled == nil then
  glow_enabled = true
end

local function managed(key)
  local value = tweaks[key]
  if value == nil then
    return true
  end
  return value
end

local manage_rounding = managed("manage_rounding")
local manage_gaps = managed("manage_gaps")
local manage_borders = managed("manage_borders")
local manage_glow = managed("manage_glow")

local background = parse_hex(theme.background) or { r = 1, g = 1, b = 1 }
local foreground = parse_hex(theme.foreground) or { r = 0, g = 0, b = 0 }
local accent = parse_hex(theme.accent) or parse_hex(theme.blue) or { r = 0, g = 0.36, b = 0.65 }

local active_color = saturate_accent and saturate(accent) or accent
local inactive_color = mix(background, foreground, inactive_mix)
local no_glow_color = "rgba(00000000)"
local active_border_color = rgb_string(active_color)
local inactive_border_color = rgb_string(inactive_color)
local active_glow_color = rgba_string(active_color, tweaks.glow_alpha or 0.18)
local inner_glow_color = rgba_string(active_color, tweaks.inner_glow_alpha or 0.12)

if manage_gaps or manage_borders then
  local general = {}
  local group = {}
  if manage_gaps then
    general.gaps_out = gaps_out
    general.gaps_in = gaps_in
  end
  if manage_borders then
    general.border_size = border_size
    general.col = {
      inactive_border = inactive_border_color,
      active_border = active_border_color,
    }
    group.col = {
      border_inactive = inactive_border_color,
      border_active = active_border_color,
    }
  end
  local block = { general = general }
  if manage_borders then
    block.group = group
  end
  hl.config(block)
end

if manage_rounding or manage_glow then
  local decoration = {}
  if manage_rounding then
    decoration.rounding = rounding
  end
  if manage_glow then
    decoration.shadow = {
      enabled = glow_enabled,
      range = tweaks.glow_range or 10,
      render_power = tweaks.glow_power or 4,
      offset = { 0, 0 },
      color = active_glow_color,
      color_inactive = no_glow_color,
    }
    decoration.glow = {
      enabled = glow_enabled,
      range = tweaks.inner_glow_range or 5,
      render_power = tweaks.glow_power or 4,
      color = inner_glow_color,
      color_inactive = no_glow_color,
    }
  end
  hl.config({ decoration = decoration })
end
