#!/usr/bin/env python3
"""Helpers for Patina apply: keep existing user chrome, surgical menu edits."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CHROME_GROUPS = {
    "rounding": (r"\brounding\b",),
    "gaps": (r"\bgaps_out\b", r"\bgaps_in\b"),
    "borders": (
        r"\bborder_size\b",
        r"\binactive_border\b",
        r"\bactive_border\b",
        r"\bborder_inactive\b",
        r"\bborder_active\b",
    ),
    "glow": (r"\bshadow\b", r"\bglow\b"),
}

SKIP_LUA_NAMES = {"patina.lua", "polish.lua"}
OURS_THEME_MARKERS = (
    "omarchy-theme-tweaks",
    "Smart Tweaks",
    "smart tweaks",
    "polish.toml",
    "patina.toml",
    "glow_alpha",
)


def is_comment_lua(line: str) -> bool:
    stripped = line.lstrip()
    return not stripped or stripped.startswith("--")


def scan_lua_chrome(text: str) -> set[str]:
    found: set[str] = set()
    for raw in text.splitlines():
        if is_comment_lua(raw):
            continue
        for group, patterns in CHROME_GROUPS.items():
            for pattern in patterns:
                if re.search(pattern, raw):
                    found.add(group)
                    break
    return found


def detect_user_chrome(hypr_dir: Path) -> set[str]:
    found: set[str] = set()
    if not hypr_dir.is_dir():
        return found
    for path in sorted(hypr_dir.glob("*.lua")):
        if path.name in SKIP_LUA_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        found |= scan_lua_chrome(text)
    return found


def manage_flags(hypr_dir: Path) -> dict[str, bool]:
    owned = detect_user_chrome(hypr_dir)
    return {
        "manage_rounding": "rounding" not in owned,
        "manage_gaps": "gaps" not in owned,
        "manage_borders": "borders" not in owned,
        "manage_glow": "glow" not in owned,
    }


def _toml_literal(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def upsert_toml_root(toml_path: Path, values: dict) -> None:
    text = toml_path.read_text(encoding="utf-8") if toml_path.exists() else ""
    lines = text.splitlines(keepends=True)
    remaining = dict(values)
    out: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and not stripped.startswith("[."):
            in_section = True
        key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
        if not in_section and key in remaining:
            prefix = line[: len(line) - len(line.lstrip())]
            newline = "\n" if line.endswith("\n") else ""
            out.append(f"{prefix}{key} = {_toml_literal(remaining.pop(key))}{newline}")
            continue
        out.append(line)
    if remaining:
        body = "".join(out)
        extra = []
        if body and not body.endswith("\n"):
            extra.append("\n")
        extra.append("\n")
        for key, value in remaining.items():
            extra.append(f"{key} = {_toml_literal(value)}\n")
        out.extend(extra)
    toml_path.write_text("".join(out), encoding="utf-8")


def upsert_toml_flags(toml_path: Path, flags: dict[str, bool]) -> None:
    upsert_toml_root(toml_path, flags)


GAP_PRESETS = {
    "tight": {"in": 2, "out": 2},
    "default": {"in": 5, "out": 10},
    "loose": {"in": 10, "out": 20},
}

GAP_SIDES = (
    ("gaps_in_top", "in"),
    ("gaps_in_right", "in"),
    ("gaps_in_bottom", "in"),
    ("gaps_in_left", "in"),
    ("gaps_out_top", "out"),
    ("gaps_out_right", "out"),
    ("gaps_out_bottom", "out"),
    ("gaps_out_left", "out"),
)


def gap_preset_values(name: str) -> dict:
    if name not in GAP_PRESETS:
        raise ValueError(f"unknown gap preset: {name}")
    sizes = GAP_PRESETS[name]
    values = {"gaps": name, "manage_gaps": True}
    for key, side in GAP_SIDES:
        values[key] = sizes[side]
    return values


def set_gap_preset(toml_path: Path, name: str) -> None:
    upsert_toml_root(toml_path, gap_preset_values(name))


def _root_toml_map(path: Path) -> dict:
    data = {}
    if not path.is_file():
        return data
    in_section = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            in_section = True
            continue
        if in_section or "=" not in line:
            continue
        key, raw_val = line.split("=", 1)
        key = key.strip()
        raw_val = raw_val.split("#", 1)[0].strip()
        if raw_val in ("true", "false"):
            data[key] = raw_val == "true"
        elif raw_val.startswith(("'", '"')) and len(raw_val) >= 2:
            data[key] = raw_val[1:-1]
        else:
            try:
                data[key] = int(raw_val)
            except ValueError:
                try:
                    data[key] = float(raw_val)
                except ValueError:
                    data[key] = raw_val
    return data


ROUNDING_PRESETS = {
    "sharp": 0,
    "soft": 6,
    "round": 12,
}


def rounding_preset_values(name: str) -> dict:
    if name not in ROUNDING_PRESETS:
        raise ValueError(f"unknown corner preset: {name}")
    return {
        "corners": name,
        "rounding": ROUNDING_PRESETS[name],
        "manage_rounding": True,
    }


def set_rounding_preset(toml_path: Path, name: str) -> None:
    upsert_toml_root(toml_path, rounding_preset_values(name))


def current_rounding_preset(toml_path: Path) -> str:
    data = _root_toml_map(toml_path)
    named = str(data.get("corners") or "").strip().lower()
    if named in ROUNDING_PRESETS:
        return named
    rounding = data.get("rounding")
    if rounding is None and not named:
        return "soft"
    for name, value in ROUNDING_PRESETS.items():
        if rounding == value:
            return name
    return "custom"


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "on", "yes"):
        return True
    if text in ("0", "false", "off", "no"):
        return False
    raise ValueError(f"not a boolean: {value}")


def read_state(toml_path: Path) -> dict:
    data = _root_toml_map(toml_path)
    applied = data.get("applied")
    if applied is None:
        applied = True
    glow = data.get("glow")
    if glow is None:
        glow = False
    try:
        rounding = int(data.get("rounding", 6))
    except (TypeError, ValueError):
        rounding = 6
    try:
        border = int(data.get("border_size", 2))
    except (TypeError, ValueError):
        border = 2
    border = max(1, min(16, border))
    return {
        "applied": bool(applied),
        "gaps": current_gap_preset(toml_path),
        "corners": current_rounding_preset(toml_path),
        "rounding": rounding,
        "border_size": border,
        "glow": bool(glow),
    }


def apply_updates(toml_path: Path, updates: dict) -> dict:
    values: dict = {}
    if "applied" in updates:
        values["applied"] = _as_bool(updates["applied"])
    if "glow" in updates:
        values["glow"] = _as_bool(updates["glow"])
        values["manage_glow"] = True
    if "border_size" in updates or "border-size" in updates:
        raw = updates.get("border_size", updates.get("border-size"))
        values["border_size"] = max(1, min(16, int(raw)))
        values["manage_borders"] = True
    if "gaps" in updates:
        values.update(gap_preset_values(str(updates["gaps"])))
    if "corners" in updates:
        values.update(rounding_preset_values(str(updates["corners"])))
    elif "rounding" in updates:
        rounding = max(0, min(24, int(updates["rounding"])))
        values["rounding"] = rounding
        values["manage_rounding"] = True
        for name, px in ROUNDING_PRESETS.items():
            if px == rounding:
                values["corners"] = name
                break
    if values:
        upsert_toml_root(toml_path, values)
    return read_state(toml_path)


def current_gap_preset(toml_path: Path) -> str:
    data = _root_toml_map(toml_path)
    named = str(data.get("gaps") or "").strip().lower()
    if named in GAP_PRESETS:
        return named
    inner = [data.get(key) for key, side in GAP_SIDES if side == "in"]
    outer = [data.get(key) for key, side in GAP_SIDES if side == "out"]
    if not named and all(v is None for v in inner + outer):
        return "default"
    for name, sizes in GAP_PRESETS.items():
        if inner and all(v == sizes["in"] for v in inner) and outer and all(
            v == sizes["out"] for v in outer
        ):
            return name
    return "custom"


def ours_theme_tweaks(text: str) -> bool:
    return any(marker in text for marker in OURS_THEME_MARKERS)


def migrate_theme_tweaks(path: Path) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    if not ours_theme_tweaks(text):
        return
    chrome_keys = {
        "rounding",
        "border_size",
        "gaps_out_top",
        "gaps_out_right",
        "gaps_out_bottom",
        "gaps_out_left",
        "gaps_in_top",
        "gaps_in_right",
        "gaps_in_bottom",
        "gaps_in_left",
        "inactive_mix",
        "saturate_accent",
        "glow",
        "glow_range",
        "glow_power",
        "glow_alpha",
        "inner_glow_range",
        "inner_glow_alpha",
    }
    kept: list[str] = []
    in_auto = False
    for raw in text.splitlines(keepends=True):
        stripped = raw.strip()
        if stripped.startswith("["):
            in_auto = stripped.strip("[]").strip() == "auto"
            kept.append(raw)
            continue
        key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
        if not in_auto and key in chrome_keys:
            continue
        if not in_auto and key == "applied":
            continue
        kept.append(raw)
    body = "".join(kept)
    body = body.replace("polish.toml", "patina.toml").replace(
        "Style → Polish", "Style → Patina"
    )
    if "patina.toml" not in body:
        header = (
            "# Auto light/dark theme swap at sunrise and sunset.\n"
            "# Window chrome lives in patina.toml (Style → Patina).\n"
        )
        body = header + "\n" + body.lstrip("\n")
    path.write_text(body, encoding="utf-8")


def strip_jsonc(raw: str) -> str:
    out = []
    for line in raw.splitlines():
        if line.lstrip().startswith("//"):
            continue
        out.append(line)
    return re.sub(r",(\s*[}\]])", r"\1", "\n".join(out))


def parse_menu(path: Path) -> dict:
    if not path.exists():
        return {}
    stripped = strip_jsonc(path.read_text(encoding="utf-8")).strip()
    if not stripped:
        return {}
    data = json.loads(stripped)
    return data if isinstance(data, dict) else {}


def _skip_ws_and_comments(text: str, i: int) -> int:
    n = len(text)
    while i < n:
        if text[i] in " \t\r\n":
            i += 1
            continue
        if text.startswith("//", i):
            nl = text.find("\n", i)
            i = n if nl < 0 else nl + 1
            continue
        break
    return i


def _match_string(text: str, i: int) -> int:
    quote = text[i]
    i += 1
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == quote:
            return i + 1
        i += 1
    return n


def find_json_object(text: str, key: str) -> tuple[int, int] | None:
    needle = f'"{key}"'
    start = 0
    n = len(text)
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            return None
        i = idx + len(needle)
        i = _skip_ws_and_comments(text, i)
        if i >= n or text[i] != ":":
            start = idx + 1
            continue
        i = _skip_ws_and_comments(text, i + 1)
        if i >= n or text[i] != "{":
            start = idx + 1
            continue
        depth = 0
        j = i
        while j < n:
            ch = text[j]
            if ch in "\"'":
                j = _match_string(text, j)
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j + 1
                    k = _skip_ws_and_comments(text, end)
                    if k < n and text[k] == ",":
                        end = k + 1
                    return idx, end
            j += 1
        return None


def remove_jsonc_key(text: str, key: str) -> str:
    span = find_json_object(text, key)
    if not span:
        return text
    start, end = span
    return text[:start] + text[end:]


def insert_jsonc_key(text: str, key: str, obj: dict) -> str:
    blob = f'  "{key}": ' + json.dumps(obj, indent=2, ensure_ascii=False).replace(
        "\n", "\n  "
    )
    blob = blob.rstrip() + ",\n"
    span = find_json_object(text, key)
    if span:
        start, end = span
        return text[:start] + blob + text[end:]
    stripped = text.rstrip()
    if not stripped:
        return "{\n" + blob + "}\n"
    if stripped.endswith("}"):
        head = stripped[:-1].rstrip()
        if head.endswith(","):
            head = head[:-1].rstrip()
        if head.endswith("{"):
            return head + "\n" + blob + "}\n"
        return head + ",\n" + blob + "}\n"
    return stripped + "\n" + blob


def is_ours_theme_override(entry: dict | None) -> bool:
    if not entry or not isinstance(entry, dict):
        return False
    label = str(entry.get("label") or "").strip()
    action = str(entry.get("action") or "")
    if not label:
        return True
    markers = (
        "omarchy-theme-tweaks",
        "omarchy-polish apply",
        "omarchy-patina apply --quiet",
    )
    return any(marker in action for marker in markers)


def upsert_menu(path: Path, action_bin: str) -> None:
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    data = parse_menu(path)
    text = original if original.strip() else "{\n}\n"

    if is_ours_theme_override(data.get("style.theme")):
        text = remove_jsonc_key(text, "style.theme")
    for stale in ("style.smart-tweaks", "style.polish"):
        text = remove_jsonc_key(text, stale)

    entry = {
        "icon": "󰃌",
        "label": "Patina",
        "description": "Gaps, corners, border, and glow",
        "aliases": [
            "patina",
            "polish",
            "smart tweaks",
            "window chrome",
            "theme polish",
        ],
        "action": f"{action_bin} panel",
        "checked": f"{action_bin} --enabled",
    }
    text = insert_jsonc_key(text, "style.patina", entry)
    text = insert_jsonc_key(
        text,
        "style.gaps",
        {
            "icon": "",
            "label": "Gaps",
            "description": "Space between tiles and the screen edge",
            "aliases": ["gaps", "window gaps", "padding", "tight gaps", "loose gaps"],
        },
    )
    text = insert_jsonc_key(
        text,
        "style.gaps.tight",
        {
            "icon": "",
            "label": "Tight",
            "description": "2px between tiles and around the screen",
            "action": f"{action_bin} gaps tight",
            "checked": f"{action_bin} gaps --is tight",
        },
    )
    text = insert_jsonc_key(
        text,
        "style.gaps.default",
        {
            "icon": "",
            "label": "Default",
            "description": "Omarchy default: 5px between tiles, 10px to the edge",
            "action": f"{action_bin} gaps default",
            "checked": f"{action_bin} gaps --is default",
        },
    )
    text = insert_jsonc_key(
        text,
        "style.gaps.loose",
        {
            "icon": "",
            "label": "Loose",
            "description": "10px between tiles, 20px to the edge",
            "action": f"{action_bin} gaps loose",
            "checked": f"{action_bin} gaps --is loose",
        },
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


def remove_menu_patina(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for key in (
        "style.gaps.tight",
        "style.gaps.default",
        "style.gaps.loose",
        "style.gaps",
        "style.patina",
        "style.polish",
        "style.smart-tweaks",
    ):
        text = remove_jsonc_key(text, key)
    path.write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("lib.py detect|write-flags|migrate-tweaks|menu-upsert|menu-remove ...", file=sys.stderr)
        return 2
    cmd = argv[1]
    if cmd == "detect":
        flags = manage_flags(Path(argv[2]))
        json.dump(flags, sys.stdout)
        sys.stdout.write("\n")
        return 0
    if cmd == "write-flags":
        toml_path = Path(argv[2])
        hypr_dir = Path(argv[3])
        upsert_toml_flags(toml_path, manage_flags(hypr_dir))
        return 0
    if cmd == "migrate-tweaks":
        migrate_theme_tweaks(Path(argv[2]))
        return 0
    if cmd == "menu-upsert":
        upsert_menu(Path(argv[2]), argv[3])
        return 0
    if cmd == "menu-remove":
        remove_menu_patina(Path(argv[2]))
        return 0
    if cmd == "gaps-set":
        set_gap_preset(Path(argv[2]), argv[3])
        return 0
    if cmd == "gaps-get":
        sys.stdout.write(current_gap_preset(Path(argv[2])) + "\n")
        return 0
    if cmd == "gaps-is":
        return 0 if current_gap_preset(Path(argv[2])) == argv[3] else 1
    if cmd == "corners-set":
        set_rounding_preset(Path(argv[2]), argv[3])
        return 0
    if cmd == "corners-get":
        sys.stdout.write(current_rounding_preset(Path(argv[2])) + "\n")
        return 0
    if cmd == "corners-is":
        return 0 if current_rounding_preset(Path(argv[2])) == argv[3] else 1
    if cmd == "state-get":
        json.dump(read_state(Path(argv[2])), sys.stdout)
        sys.stdout.write("\n")
        return 0
    if cmd == "state-set":
        updates = json.loads(argv[3]) if len(argv) > 3 else json.loads(sys.stdin.read() or "{}")
        if not isinstance(updates, dict):
            print("state-set expects a JSON object", file=sys.stderr)
            return 2
        json.dump(apply_updates(Path(argv[2]), updates), sys.stdout)
        sys.stdout.write("\n")
        return 0
    if cmd == "state-set-args":
        path = Path(argv[2])
        args = argv[3:]
        updates = {}
        i = 0
        while i < len(args):
            key = args[i].lstrip("-").replace("-", "_")
            if i + 1 >= len(args):
                print(f"missing value for {args[i]}", file=sys.stderr)
                return 2
            updates[key] = args[i + 1]
            i += 2
        json.dump(apply_updates(path, updates), sys.stdout)
        sys.stdout.write("\n")
        return 0
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
