"""Self-check for smlcore / smlp. Run: python -m unittest discover -s tests  (from the repo root)."""
import pathlib
import sys
import tempfile
import unittest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import smlcore  # noqa: E402
import smlp     # noqa: E402

DECK = """# Deck

### Slide 1 — Title page

- 【Greeting】
- 【Title】：
  注意機構に基づく

---

### Slide 2 — Outline

- 【Overview】

---

### Slide 3

---
"""


class ParseDeck(unittest.TestCase):
    def test_sections(self):
        s = smlcore.parse_deck(DECK)
        self.assertEqual([n for n, _, _ in s], [1, 2, 3])
        self.assertEqual(s[0][1], "Title page")
        self.assertEqual(s[0][2], "- 【Greeting】\n- 【Title】：\n  注意機構に基づく")
        self.assertEqual(s[1][2], "- 【Overview】")
        self.assertEqual((s[2][1], s[2][2]), ("", ""))   # empty page: heading kept, body empty

    def test_numbering_gap_is_fatal(self):
        with self.assertRaises(SystemExit):
            smlcore.parse_deck(DECK.replace("### Slide 3", "### Slide 4"))

    def test_no_heading_is_fatal(self):
        with self.assertRaises(SystemExit):
            smlcore.parse_deck("no headings here")

    def test_page_count(self):
        s = smlcore.parse_deck(DECK)
        smlcore.check_page_count(s, "x.pdf", 3)
        with self.assertRaises(SystemExit):
            smlcore.check_page_count(s, "x.pdf", 4)


class Config(unittest.TestCase):
    def test_as_list(self):
        self.assertEqual(smlcore.as_list("xelatex, biber ,xelatex"), ["xelatex", "biber", "xelatex"])
        self.assertEqual(smlcore.as_list("[a, b]"), ["a", "b"])
        self.assertEqual(smlcore.as_list(["a", " b "]), ["a", "b"])
        self.assertEqual(smlcore.as_list(None), [])

    def test_legacy_pdfmake(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / ".pdfmake").write_text(
                "# comment\nmain=main.tex\nout=main.tex\ntool_chain = xelatex, xelatex\n", encoding="utf-8")
            cfg = smlcore.load_config(d)
            sec = smlcore.smlmk_section(cfg)
            self.assertEqual(sec["main"], ["main.tex"])
            self.assertEqual(sec["out"], ["main.tex"])
            self.assertEqual(sec["tool_chain"], ["xelatex", "xelatex"])
            self.assertNotIn("smlpdtp", cfg)

    def test_smlconfig_yaml_wins_over_pdfmake(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / ".pdfmake").write_text("main=old.tex\n", encoding="utf-8")
            (p / ".smlconfig").write_text(
                "smlmk:\n  main: main.tex\n  tool_chain: [xelatex, xelatex]\n"
                "smlpdtp:\n  deck: script/deck.md\n  note_font_size: 18\n"
                "smlptk:\n  width: 1600\n", encoding="utf-8")
            cfg = smlcore.load_config(p)
            self.assertEqual(smlcore.smlmk_section(cfg)["main"], ["main.tex"])
            self.assertEqual(smlcore.smlmk_section(cfg)["tool_chain"], ["xelatex", "xelatex"])
            self.assertEqual(cfg["smlpdtp"]["deck"], "script/deck.md")
            self.assertEqual(cfg["smlptk"]["width"], 1600)

    def test_smlconfig_empty_section_and_string_chain(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / ".smlconfig").write_text("smlmk:\n  tool_chain: xelatex, biber, xelatex\nsmlpdtp:\n", encoding="utf-8")
            cfg = smlcore.load_config(p)
            self.assertEqual(smlcore.smlmk_section(cfg)["tool_chain"], ["xelatex", "biber", "xelatex"])
            self.assertEqual(cfg["smlpdtp"], {})

    def test_no_config(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(smlcore.load_config(d), {})
            self.assertEqual(smlcore.smlmk_section({}), {})


class Pdfpc(unittest.TestCase):
    def test_document(self):
        s = smlcore.parse_deck(DECK)
        doc = smlp.build_pdfpc_doc(s, note_font_size=20, duration=12)
        self.assertEqual(doc["pdfpcFormat"], 2)
        self.assertTrue(doc["disableMarkdown"])
        self.assertEqual(doc["duration"], 12)
        self.assertEqual([p["label"] for p in doc["pages"]], ["1", "2", "3"])
        self.assertEqual([p["idx"] for p in doc["pages"]], [0, 1, 2])
        self.assertEqual(doc["pages"][0]["note"], s[0][2])
        self.assertEqual(doc["pages"][2]["note"], "")

    def test_duration_omitted_when_unset(self):
        doc = smlp.build_pdfpc_doc(smlcore.parse_deck(DECK))
        self.assertNotIn("duration", doc)
        self.assertEqual(doc["noteFontSize"], smlp.DEFAULT_NOTE_FONT_SIZE)


class Keynote(unittest.TestCase):
    def test_canvas_height_follows_pdf_aspect(self):
        self.assertEqual(smlp.canvas_height(1920, 453.54, 255.12), 1080)   # 16:9 beamer page
        self.assertEqual(smlp.canvas_height(1920, 800, 600), 1440)          # 4:3 stays 4:3

    def test_applescript_string(self):
        self.assertEqual(smlp.applescript_string(""), '""')
        self.assertEqual(smlp.applescript_string('a"b\\c'), '"a\\"b\\\\c"')
        self.assertEqual(smlp.applescript_string("x\ny"), '"x" & linefeed & "y"')

    def test_script_shape(self):
        page = pathlib.Path("/t/p-01.pdf")
        script = smlp.build_applescript([page], ["n1\nn2"], 1920, 1080, "Blank", None)
        self.assertIn("make new document with properties {width:1920, height:1080}", script)
        self.assertIn('POSIX file "/t/p-01.pdf"', script)
        self.assertIn('"n1" & linefeed & "n2"', script)
        self.assertIn('master slide "Blank"', script)
        self.assertEqual(script.count("make new slide"), 1)
        self.assertNotIn("save thisDoc", script)
        saved = smlp.build_applescript([page], ["n"], 1920, 1080, "Blank", pathlib.Path("/o/x.key"))
        self.assertIn('save thisDoc in POSIX file "/o/x.key"', saved)
        self.assertLess(saved.index('save thisDoc in POSIX file'), saved.index('make new slide'))  # bind path before content
        self.assertTrue(saved.rstrip().endswith('save thisDoc\nend tell'))


class Resolve(unittest.TestCase):
    """Default resolution chain: CLI > own section > smlpdtp section > smlmk out/main > unique file."""

    @staticmethod
    def _args(d, deck=None, pdf=None):
        import argparse
        return argparse.Namespace(deck=deck, pdf=pdf, dir=str(d))

    def test_no_deck_candidate_is_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "main.pdf").write_bytes(b"%PDF")
            with self.assertRaises(SystemExit):
                smlp.resolve(self._args(d), "smlpdtp")

    def test_single_deck_in_script_dir_and_unique_pdf(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / "script").mkdir()
            (p / "script" / "deck-ja.md").write_text(DECK, encoding="utf-8")
            (p / "main.pdf").write_bytes(b"%PDF")
            _w, deck, pdf, _o, _s = smlp.resolve(self._args(d), "smlpdtp")
            self.assertEqual((deck.name, pdf.name), ("deck-ja.md", "main.pdf"))

    def test_two_deck_candidates_is_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / "deck.md").write_text(DECK, encoding="utf-8")
            (p / "deck-ja.md").write_text(DECK, encoding="utf-8")
            (p / "main.pdf").write_bytes(b"%PDF")
            with self.assertRaises(SystemExit):
                smlp.resolve(self._args(d), "smlpdtp")

    def test_smlptk_falls_back_to_smlpdtp_section(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / "talk.md").write_text(DECK, encoding="utf-8")
            (p / "slides.pdf").write_bytes(b"%PDF")
            (p / ".smlconfig").write_text("smlpdtp:\n  deck: talk.md\n  pdf: slides.pdf\nsmlptk:\n  width: 1600\n", encoding="utf-8")
            _w, deck, pdf, own, shared = smlp.resolve(self._args(d), "smlptk")
            self.assertEqual((deck.name, pdf.name, own["width"]), ("talk.md", "slides.pdf", 1600))

    def test_pdf_from_smlmk_out_then_fallback_to_unique(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / "deck.md").write_text(DECK, encoding="utf-8")
            (p / ".pdfmake").write_text("main=main.tex\nout=Final.tex\n", encoding="utf-8")
            (p / "Final.pdf").write_bytes(b"%PDF")
            self.assertEqual(smlp.resolve(self._args(d), "smlpdtp")[2].name, "Final.pdf")
            (p / "Final.pdf").unlink()
            (p / "main.pdf").write_bytes(b"%PDF")           # configured out missing, one pdf present
            self.assertEqual(smlp.resolve(self._args(d), "smlpdtp")[2].name, "main.pdf")
            (p / "main.pdf").unlink()
            with self.assertRaises(SystemExit):
                smlp.resolve(self._args(d), "smlpdtp")

    def test_non_utf8_deck_is_a_clean_error(self):
        with tempfile.TemporaryDirectory() as d:
            deck = pathlib.Path(d) / "deck.md"
            deck.write_bytes(b"\xff\xfe### Slide 1\n")
            with self.assertRaises(SystemExit):
                smlp.load_sections(deck, {}, {})

    def test_int_option(self):
        self.assertEqual(smlcore.int_option({"note_font_size": "18"}, "note_font_size", 20), 18)
        self.assertEqual(smlcore.int_option({}, "duration"), None)
        with self.assertRaises(SystemExit):
            smlcore.int_option({"duration": "twelve"}, "duration")

    def test_unreadable_pdfmake_warns_and_continues(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / ".pdfmake").write_bytes(b"\xff\xfemain=x\n")
            self.assertEqual(smlcore.load_config(d), {"smlmk": {}})

    def test_init_refuses_to_shadow_legacy_pdfmake(self):
        import os, smlmk
        with tempfile.TemporaryDirectory() as d:
            cwd = os.getcwd()
            os.chdir(d)
            try:
                pathlib.Path(".pdfmake").write_text("main=main.tex\n", encoding="utf-8")
                smlmk.create_template_config()
                self.assertFalse(pathlib.Path(".smlconfig").exists())
                pathlib.Path(".pdfmake").unlink()
                smlmk.create_template_config()
                self.assertTrue(pathlib.Path(".smlconfig").exists())
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
