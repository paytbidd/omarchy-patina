# Omarchy Polish

Reusable window chrome for any [Omarchy](https://omarchy.org/) theme: slight rounding, a 2px border, tight gaps under the top bar, a mixed unfocused border, and a **soft hue-matched glow**.

Toggle it from **Super+Space → Style → Polish**. Turning it off restores the stock theme look. Removing the plugin takes the Style row with it.

## Install

One shot:

```bash
curl -fsSL https://raw.githubusercontent.com/paytbidd/omarchy-polish/main/install | bash
```

Or the Omarchy form, then apply:

```bash
omarchy plugin add https://github.com/paytbidd/omarchy-polish.git --yes --enable
~/.config/omarchy/plugins/payton.polish/scripts/omarchy-polish apply
```

That will:

1. Enable the plugin
2. Drop `~/.config/hypr/polish.lua` and load it from `hyprland.lua`
3. Write `~/.config/omarchy/polish.toml` if you do not already have one
4. Add **Style → Polish** (and restore the stock **Theme** row if a previous override hid the label)
5. Re-apply chrome after `omarchy theme set` via a `theme-set` hook

Numbers live in `~/.config/omarchy/polish.toml`. Glow alphas default to 60% of the earlier Smart Tweaks recipe.

## Toggle

Super+Space → Style → Polish, or:

```bash
omarchy-polish toggle
omarchy-polish on
omarchy-polish off
omarchy-polish --enabled
```

## Unapply

Chrome off, keep the plugin:

```bash
~/.config/omarchy/plugins/payton.polish/scripts/omarchy-polish off
```

Tweaks off and remove Polish itself:

```bash
curl -fsSL https://raw.githubusercontent.com/paytbidd/omarchy-polish/main/uninstall | bash
```

or:

```bash
~/.config/omarchy/plugins/payton.polish/scripts/omarchy-polish unapply --purge
```

Your `polish.toml` is left in place so a reinstall keeps your numbers.

## Update

```bash
omarchy plugin update payton.polish
~/.config/omarchy/plugins/payton.polish/scripts/omarchy-polish apply
```

## Status

```bash
~/.config/omarchy/plugins/payton.polish/scripts/omarchy-polish status
```
