#!/usr/bin/env python3
"""
smlp — smart latex presentation tools
=====================================

Two entry points share this module:

    smlpdtp   deck markdown -> <pdf>.pdfpc       pdfpc speaker notes
    smlptk    PDF + deck    -> Keynote document  one page per slide + presenter notes

The deck is a markdown file split by ``### Slide N — <title>`` headings
(regex configurable, see smlcore.DECK_HEADING_RE). Section N is attached to
PDF *physical* page N. Beamer's ``noframenumbering`` makes the number printed
on the slide lag the physical page by one; pdfpc and Keynote both count
physical pages, so the deck must too. Both commands refuse to run when the
section count differs from the page count.

Usage:
    smlpdtp [DECK] [--pdf PDF] [-C DIR] [--check]
    smlptk  [DECK] [--pdf PDF] [-C DIR] [--check] [--out FILE.key] [--width PT]

    DECK and --pdf default to the `smlpdtp:` / `smlptk:` sections of
    .smlconfig; the PDF further defaults to smlmk's out/main + ".pdf".
    Without any config: a single deck*.md in ./ or ./script/, and a single
    *.pdf in ./, are picked up automatically.

Facts the implementation depends on (verified 2026-09-02 with pdfpc 4.7.0):
    * pdfpc reads `<basename>.pdfpc` next to the PDF as JSON ("pdfpcFormat": 2).
      The INI-style `[notes]` / `### N` layout described in older documentation
      is not read, and pdfpc overwrites it with an empty document on exit.
    * Notes are matched to pages by PDF page label (poppler). beamer + hyperref
      label pages with their physical number, so label = str(N); the 0-based
      `idx` is written as well for pdfpc's fallback path.
    * `disableMarkdown` must be true: a handcard carries information in its
      line layout, and Markdown rendering folds the indented continuation
      lines into one paragraph.
    * pdfpc writes the file back on exit. The deck stays the single source of
      truth; do not edit notes inside pdfpc (Ctrl+n) — the next run overwrites them.
    * Keynote cannot import a multi-page PDF page-per-slide (dragging it in
      yields one image object showing page 1). Pages are split into single-page
      PDFs with pdfseparate and each is inserted as an image object by
      AppleScript; Keynote keeps PDF images as vectors, so text stays sharp at
      any projector resolution. (The prototype rasterised to PNG at 305 dpi;
      superseded 2026-09-02 at the author's suggestion.)
    * AppleScript string literals have no `\\n`; multi-line notes are escaped
      line by line and joined with `& linefeed &`. `osacompile -o` validates the
      generated script without launching Keynote, which is what `--check` runs;
      without it a syntax error surfaces only after Keynote has built half a deck.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from smlcore import (
    DECK_HEADING_RE, Colors, check_page_count, fail, int_option, load_config, ok,
    parse_deck, pdf_info, smlmk_section, warn,
)

DEFAULT_NOTE_FONT_SIZE = 20
DEFAULT_CANVAS_WIDTH = 1920
DEFAULT_MASTER_SLIDE = "Blank"


# --------------------------------------------------------------------------- resolution

def _auto_deck(work):
    cands = sorted(work.glob("deck*.md")) + sorted((work / "script").glob("deck*.md"))
    if len(cands) == 1:
        return cands[0]
    if not cands:
        fail("no deck given and no deck*.md found in ./ or ./script/ "
             "(pass DECK, or set `deck:` under smlpdtp: in .smlconfig)")
    fail("no deck given and several candidates found: " + ", ".join(str(c.relative_to(work)) for c in cands)
         + " (pass DECK, or set `deck:` under smlpdtp: in .smlconfig)")


def _auto_pdf(config, work):
    names = smlmk_section(config)
    basenames = names.get("out") or names.get("main") or []
    configured = work / (Path(basenames[0]).stem + ".pdf") if len(basenames) == 1 else None
    if configured and configured.is_file():
        return configured
    cands = sorted(work.glob("*.pdf"))
    if len(cands) == 1:
        return cands[0]
    hint = f"smlmk's configured PDF {configured.name} does not exist; " if configured else ""
    if not cands:
        fail(hint + "no PDF found in the project directory (build it first, or pass --pdf)")
    fail(hint + "several PDFs found: " + ", ".join(c.name for c in cands)
         + " (pass --pdf, or set `pdf:` under smlpdtp: in .smlconfig)")


def resolve(args, section):
    """(work_dir, deck_path, pdf_path, own_section, smlpdtp_section)."""
    work = Path(args.dir or ".").resolve()
    if not work.is_dir():
        fail(f"not a directory: {work}")
    config = load_config(work)
    own = config.get(section) or {}
    shared = config.get("smlpdtp") or {}   # smlptk falls back to the smlpdtp values

    def pick(key):
        return own.get(key, shared.get(key))

    deck = args.deck or pick("deck")
    deck = (work / deck) if deck else _auto_deck(work)
    if not deck.is_file():
        fail(f"deck not found: {deck}")

    pdf = args.pdf or pick("pdf")
    pdf = (work / pdf) if pdf else _auto_pdf(config, work)
    if not pdf.is_file():
        fail(f"PDF not found: {pdf} (build it first, e.g. `smlmk -b`)")

    return work, deck, pdf, own, shared


def load_sections(deck, own, shared):
    heading = own.get("heading_regex") or shared.get("heading_regex") or DECK_HEADING_RE
    try:
        text = deck.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        fail(f"{deck}: not UTF-8 text ({e})")
    return parse_deck(text, heading)


def _summary(deck, sections, pdf, n_pages):
    empty = [n for n, _, body in sections if not body]
    line = f"{deck.name}: {len(sections)} sections / {pdf.name}: {n_pages} pages -> aligned"
    if empty:
        line += f" (empty note on slide {', '.join(map(str, empty))})"
    return line


# --------------------------------------------------------------------------- smlpdtp

def build_pdfpc_doc(sections, note_font_size=DEFAULT_NOTE_FONT_SIZE, duration=None):
    pages = []
    for i, (num, _title, body) in enumerate(sections):
        pages.append({
            "idx": i,
            "label": str(num),
            "overlay": 0,
            "forcedOverlay": False,
            "hidden": False,
            "note": body,
        })
    doc = {"pdfpcFormat": 2, "disableMarkdown": True, "noteFontSize": int(note_font_size)}
    if duration is not None:
        doc["duration"] = int(duration)
    doc["pages"] = pages
    return doc


def main_dtp():
    p = argparse.ArgumentParser(
        prog="smlpdtp", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="deck markdown -> <pdf>.pdfpc (pdfpc speaker notes). Section N of the deck "
                    "becomes the note of PDF physical page N.",
        epilog="Config: `smlpdtp:` section of .smlconfig (deck, pdf, note_font_size, duration, heading_regex).")
    p.add_argument("deck", nargs="?", help="deck markdown (default: .smlconfig smlpdtp.deck, else the single deck*.md)")
    p.add_argument("--pdf", help="target PDF (default: .smlconfig smlpdtp.pdf, else smlmk out/main + .pdf)")
    p.add_argument("-C", "--dir", help="project directory (default: .)")
    p.add_argument("--check", action="store_true", help="validate deck/PDF alignment only; write nothing")
    args = p.parse_args()

    _work, deck, pdf, own, shared = resolve(args, "smlpdtp")
    sections = load_sections(deck, own, shared)
    n_pages, _w, _h = pdf_info(pdf)
    check_page_count(sections, pdf, n_pages)
    print(_summary(deck, sections, pdf, n_pages))

    note_font_size = int_option(own, "note_font_size", DEFAULT_NOTE_FONT_SIZE)   # validated before --check returns
    duration = int_option(own, "duration")
    out = pdf.with_suffix(".pdfpc")
    if args.check:
        ok(f"--check: alignment OK, {out.name} not written")
        return 0

    doc = build_pdfpc_doc(sections, note_font_size=note_font_size, duration=duration)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ok(f"wrote {out.name} ({len(sections)} notes). pdfpc loads it automatically: pdfpc {pdf.name}")
    print(f"{Colors.CYAN}The deck is the source of truth: re-run after editing it; "
          f"do not edit notes inside pdfpc.{Colors.ENDC}")
    return 0


# --------------------------------------------------------------------------- smlptk

def canvas_height(width, page_w_pt, page_h_pt):
    """Keynote canvas height for `width`, following the PDF page aspect (1920 -> 1080 for 16:9)."""
    return round(width * page_h_pt / page_w_pt)


def applescript_string(text):
    """AppleScript string literal. No `\\n` escape exists, so lines are joined with `linefeed`."""
    if not text:
        return '""'
    lines = [line.replace("\\", "\\\\").replace('"', '\\"') for line in text.split("\n")]
    return " & linefeed & ".join(f'"{line}"' for line in lines)


def build_applescript(pages, notes, width, height, master_slide, out_path=None):
    body = []
    for page, note in zip(pages, notes):
        body.append(f"""
    set s to make new slide at end of slides
    try
      set base slide of s to master slide {applescript_string(master_slide)} of thisDoc
    end try
    tell s
      make new image with properties {{file:POSIX file {applescript_string(str(page))}, position:{{0, 0}}, width:{width}, height:{height}}}
      set presenter notes of s to {applescript_string(note)}
    end tell""")
    # Saving right after creation binds the document to `out_path`; otherwise Keynote
    # autosaves a new document as "Untitled N" into iCloud Drive/Keynote as soon as
    # content is added, and a later `save in` only writes a copy.
    first_save = f"\n  save thisDoc in POSIX file {applescript_string(str(out_path))}" if out_path else ""
    final_save = "\n  save thisDoc" if out_path else ""
    return f"""tell application "Keynote"
  activate
  set thisDoc to make new document with properties {{width:{width}, height:{height}}}{first_save}
  tell thisDoc{"".join(body)}
    delete slide 1
  end tell{final_save}
end tell
"""


def main_tk():
    p = argparse.ArgumentParser(
        prog="smlptk", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="PDF + deck -> Keynote: every PDF page becomes one slide holding that page as a vector image, "
                    "deck section N becomes its presenter notes. Text is not editable in Keynote.",
        epilog="Config: `smlptk:` section of .smlconfig (width, master_slide; deck/pdf fall back to smlpdtp:).")
    p.add_argument("deck", nargs="?", help="deck markdown (default: .smlconfig, else the single deck*.md)")
    p.add_argument("--pdf", help="source PDF (default: .smlconfig, else smlmk out/main + .pdf)")
    p.add_argument("-C", "--dir", help="project directory (default: .)")
    p.add_argument("--check", action="store_true",
                   help="split the PDF and compile the AppleScript with osacompile, but do not launch Keynote")
    p.add_argument("--out", help="save the Keynote document to this .key path (default: leave it unsaved in Keynote)")
    p.add_argument("--width", type=int, help=f"canvas width in Keynote points (default: {DEFAULT_CANVAS_WIDTH}); height follows the PDF aspect")
    args = p.parse_args()

    _work, deck, pdf, own, shared = resolve(args, "smlptk")
    sections = load_sections(deck, own, shared)
    n_pages, page_w, page_h = pdf_info(pdf)
    check_page_count(sections, pdf, n_pages)
    print(_summary(deck, sections, pdf, n_pages))

    width = args.width or int_option(own, "width", DEFAULT_CANVAS_WIDTH)
    height = canvas_height(width, page_w, page_h)
    master = str(own.get("master_slide", DEFAULT_MASTER_SLIDE))
    out_path = None
    if args.out:
        out_path = (_work / args.out).resolve()          # relative to the project dir, like deck and --pdf
        if out_path.suffix.lower() != ".key":
            out_path = out_path.with_suffix(".key")
        if out_path.exists():
            fail(f"refusing to overwrite existing file: {out_path}")
        if not out_path.parent.is_dir():
            fail(f"output directory does not exist: {out_path.parent}")

    workdir = Path(tempfile.gettempdir()) / f"smlptk-{pdf.stem}"
    workdir.mkdir(parents=True, exist_ok=True)
    for old in list(workdir.glob("p-*.pdf")) + list(workdir.glob("p-*.png")):
        old.unlink()
    pattern = str(workdir / f"p-%0{len(str(n_pages))}d.pdf")   # zero-padded so sorted() keeps page order
    try:
        subprocess.run(["pdfseparate", str(pdf), pattern], check=True, capture_output=True, text=True)
    except FileNotFoundError:
        fail("'pdfseparate' (poppler) not found on PATH")
    except subprocess.CalledProcessError as e:
        fail(f"pdfseparate failed: {e.stderr.strip()}")
    pages = sorted(workdir.glob("p-*.pdf"))
    if len(pages) != n_pages:
        fail(f"pdfseparate produced {len(pages)} files for {n_pages} pages")

    script = build_applescript(pages, [body for _n, _t, body in sections], width, height, master, out_path)
    src = workdir / "build.applescript"
    src.write_text(script, encoding="utf-8")
    try:
        syntax = subprocess.run(["osacompile", "-o", str(workdir / "build.scpt"), str(src)],
                                capture_output=True, text=True)
    except FileNotFoundError:
        fail("'osacompile' not found (macOS only)")
    if syntax.returncode:
        fail(f"generated AppleScript does not compile:\n{syntax.stderr.strip()}\n(script kept at {src})")

    print(f"{n_pages} pages split into single-page PDFs -> {width}x{height} pt canvas; "
          f"AppleScript compiles clean ({src})")
    if args.check:
        ok("--check: Keynote not launched")
        return 0

    run = subprocess.run(["osascript", str(src)], capture_output=True, text=True)
    if run.returncode:
        fail(f"osascript failed:\n{run.stderr.strip()}")
    if out_path:
        ok(f"Keynote document saved: {out_path}")
    else:
        ok("Keynote document created.")
        warn("Keynote autosaves it as 'Untitled' in iCloud Drive/Keynote; use Save As (or --out next time) "
             f"to put it where you want. The page PDFs are read from {workdir} until the first save.")
    return 0

