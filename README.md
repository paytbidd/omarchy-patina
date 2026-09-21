# Omarchy Patina

Reusable window chrome for any [Omarchy](https://omarchy.org/) theme: slight rounding, a 2px border, tight even gaps around the screen and between tiles, a mixed unfocused border, and a **soft hue-matched glow**.

Toggle it from **Super+Space → Style → Patina**. Turning it off restores the stock theme look. Removing the plugin takes the Style row with it.

Gap spacing is **Super+Space → Style → Gaps**:

| Preset | Between tiles | To the screen edge |
| --- | --- | --- |
| Tight | 2px | 2px |
| Default | 5px (Omarchy) | 10px (Omarchy) |
| Loose | 10px | 20px |

## Install

One shot:

```bash
curl -fsSL https://raw.githubusercontent.com/paytbidd/omarchy-patina/main/install | bash
```

Or the Omarchy form, then apply:

```bash
omarchy plugin add https://github.com/paytbidd/omarchy-patina.git --yes --enable
~/.config/omarchy/plugins/payton.patina/scripts/omarchy-patina apply
```

That will:

1. Enable the plugin
2. Drop `~/.config/hypr/patina.lua` and load it from `hyprland.lua` (a marked block only; the rest of `hyprland.lua` is left alone)
3. Write `~/.config/omarchy/patina.toml` if you do not already have one
4. Add **Style → Patina** without rewriting your other menu rows
5. Re-apply chrome after `omarchy theme set` via a `theme-set` hook

Install does **not** replace `looknfeel.lua`, `shell.toml`, or an existing `patina.toml`. If you already set rounding, gaps, borders, or glow in your Hyprland Lua, Patina leaves those keys alone and only adds what you have not set (usually the hue-matched glow).

Numbers live in `~/.config/omarchy/patina.toml`. Glow alphas default to 60% of the earlier Smart Tweaks recipe. Set `manage_rounding` / `manage_gaps` / `manage_borders` / `manage_glow` to `false` to keep your own values.

## Toggle

Super+Space → Style → Patina, or:

```bash
omarchy-patina toggle
omarchy-patina on
omarchy-patina off
omarchy-patina --enabled
omarchy-patina gaps tight
omarchy-patina gaps default
omarchy-patina gaps loose
```

## Unapply

Chrome off, keep the plugin:

```bash
~/.config/omarchy/plugins/payton.patina/scripts/omarchy-patina off
```

Tweaks off and remove Patina itself:

```bash
curl -fsSL https://raw.githubusercontent.com/paytbidd/omarchy-patina/main/uninstall | bash
```

or:

```bash
~/.config/omarchy/plugins/payton.patina/scripts/omarchy-patina unapply --purge
```

Your `patina.toml` is left in place so a reinstall keeps your numbers.

## Update

```bash
omarchy plugin update payton.patina
~/.config/omarchy/plugins/payton.patina/scripts/omarchy-patina apply
```

## Status

```bash
~/.config/omarchy/plugins/payton.patina/scripts/omarchy-patina status
```
