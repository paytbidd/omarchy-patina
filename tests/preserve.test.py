#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import lib  # noqa: E402


STOCK_LOOKNFEEL = """-- Change the default Omarchy look'n'feel.

-- hl.config({
--   decoration = {
--     rounding = 8,
--     dim_inactive = true,
--   },
-- })
"""

CUSTOM_ROUNDING = """-- Change the default Omarchy look'n'feel.

hl.config({
  decoration = {
    rounding = 12,
    dim_inactive = true,
  },
})
"""


class DetectTests(unittest.TestCase):
    def test_stock_looknfeel_is_not_user_chrome(self):
        with tempfile.TemporaryDirectory() as tmp:
            hypr = Path(tmp)
            (hypr / "looknfeel.lua").write_text(STOCK_LOOKNFEEL)
            flags = lib.manage_flags(hypr)
        self.assertEqual(
            flags,
            {
                "manage_rounding": True,
                "manage_gaps": True,
                "manage_borders": True,
                "manage_glow": True,
            },
        )

    def test_uncommented_rounding_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            hypr = Path(tmp)
            (hypr / "looknfeel.lua").write_text(CUSTOM_ROUNDING)
            flags = lib.manage_flags(hypr)
        self.assertFalse(flags["manage_rounding"])
        self.assertTrue(flags["manage_gaps"])
        self.assertTrue(flags["manage_glow"])

    def test_skips_patina_snippet(self):
        with tempfile.TemporaryDirectory() as tmp:
            hypr = Path(tmp)
            (hypr / "looknfeel.lua").write_text(STOCK_LOOKNFEEL)
            (hypr / "patina.lua").write_text("rounding = 6\nshadow = {}\n")
            flags = lib.manage_flags(hypr)
        self.assertTrue(flags["manage_rounding"])
        self.assertTrue(flags["manage_glow"])


class MenuTests(unittest.TestCase):
    def test_upsert_keeps_other_rows_and_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "omarchy-menu.jsonc"
            path.write_text(
                "{\n"
                "  // keep this comment\n"
                '  "setup.input": {"icon": "x", "label": "Input"},\n'
                '  "style.theme": {"action": "omarchy-theme-tweaks apply --quiet"}\n'
                "}\n"
            )
            lib.upsert_menu(path, "/tmp/omarchy-patina")
            text = path.read_text()
            self.assertIn("keep this comment", text)
            self.assertIn('"setup.input"', text)
            self.assertIn('"label": "Patina"', text)
            self.assertNotIn("omarchy-theme-tweaks", text)

    def test_keeps_custom_theme_row_with_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "omarchy-menu.jsonc"
            path.write_text(
                "{\n"
                '  "style.theme": {"icon": "t", "label": "Theme", "action": "omarchy-theme-set custom"}\n'
                "}\n"
            )
            lib.upsert_menu(path, "/tmp/omarchy-patina")
            data = lib.parse_menu(path)
            self.assertEqual(data["style.theme"]["label"], "Theme")
            self.assertEqual(data["style.theme"]["action"], "omarchy-theme-set custom")
            self.assertEqual(data["style.patina"]["label"], "Patina")

    def test_unapply_does_not_drop_theme_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "omarchy-menu.jsonc"
            path.write_text(
                "{\n"
                '  "style.theme": {"icon": "t", "label": "Theme", "action": "omarchy-theme-set x"},\n'
                '  "style.patina": {"label": "Patina", "action": "x"}\n'
                "}\n"
            )
            lib.remove_menu_patina(path)
            data = lib.parse_menu(path)
            self.assertIn("style.theme", data)
            self.assertNotIn("style.patina", data)


class TweaksTests(unittest.TestCase):
    def test_leaves_unrelated_toml_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "theme-tweaks.toml"
            original = "rounding = 99\nsome_user_key = true\n"
            path.write_text(original)
            lib.migrate_theme_tweaks(path)
            self.assertEqual(path.read_text(), original)

    def test_migrates_known_smart_tweaks_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "theme-tweaks.toml"
            path.write_text(
                "applied = true\nrounding = 6\nglow_alpha = 0.18\n\n[auto]\nenabled = true\n"
            )
            lib.migrate_theme_tweaks(path)
            text = path.read_text()
            self.assertIn("[auto]", text)
            self.assertNotIn("glow_alpha", text)
            self.assertIn("patina.toml", text)


class FlagWriteTests(unittest.TestCase):
    def test_appends_manage_flags_without_dropping_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "patina.toml"
            path.write_text("applied = true\nrounding = 6\n")
            lib.upsert_toml_flags(path, {"manage_rounding": False, "manage_glow": True})
            text = path.read_text()
            self.assertIn("rounding = 6", text)
            self.assertIn("manage_rounding = false", text)
            self.assertIn("manage_glow = true", text)


if __name__ == "__main__":
    unittest.main()
