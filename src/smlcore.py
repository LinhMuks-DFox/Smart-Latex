#!/usr/bin/env python3
"""
Shared helpers for the smart-latex-suite commands (smlmk, smlpdtp, smlptk).

Configuration file
------------------
`.smlconfig` (YAML) is the primary per-project configuration. One top-level
section per command; every key is optional:

    smlmk:
      main: main.tex                 # entry file (string or list)
      out: main                      # output basename (string or list)
      tool_chain: [xelatex, xelatex] # or a comma-separated string
      # compiler: xelatex            # used only when tool_chain is absent
    smlpdtp:
      deck: script/deck-ja.md        # speaker deck (markdown)
      pdf: main.pdf                  # defaults to smlmk.out / smlmk.main + .pdf
      note_font_size: 20
      # duration: 12                 # minutes; omitted unless set
      # heading_regex: '^### Slide (\\d+)'
    smlptk:
      # deck / pdf: fall back to the smlpdtp values when absent
      width: 1920                    # Keynote canvas width in points; height follows the PDF aspect
      master_slide: Blank

The legacy `.pdfmake` (key=value, smlmk only) is still honoured when no
`.smlconfig` exists; its keys are exposed as the `smlmk` section.
"""
import re
import subprocess
import sys
from pathlib import Path

CONFIG_NAME = ".smlconfig"
LEGACY_NAME = ".pdfmake"

# Default deck section heading: "### Slide 3 — Introduction". Group 1 is the
# slide number (must equal the PDF physical page), group 2 the optional title.
DECK_HEADING_RE = r"^### Slide (\d+)(?:\s*[—–-]+\s*(.*?))?\s*$"


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def fail(msg, code=1):
    print(f"{Colors.FAIL}Error: {msg}{Colors.ENDC}", file=sys.stderr)
    sys.exit(code)


def warn(msg):
    print(f"{Colors.WARNING}Warning: {msg}{Colors.ENDC}", file=sys.stderr)


def ok(msg):
    print(f"{Colors.GREEN}{msg}{Colors.ENDC}")


# --------------------------------------------------------------------------- config

def as_list(value):
    """Normalise a scalar / comma string / list into a list of stripped strings."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).replace('[', '').replace(']', '')
    return [x.strip() for x in text.split(',') if x.strip()]


def _parse_pdfmake(path):
    """Legacy `.pdfmake`: key=value lines, `#` comments. Returns the smlmk section.

    Unreadable file -> warning and empty section (the historical smlmk behaviour:
    build with defaults rather than abort)."""
    section = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.split('#', 1)[0].strip()
                if not line or '=' not in line:
                    continue
                key, val = line.split('=', 1)
                section[key.strip()] = val.strip()
    except (OSError, UnicodeDecodeError) as e:
        warn(f"failed to read {path}: {e}; ignoring it")
        return {}
    return section


def _parse_smlconfig(path):
    try:
        import yaml
    except ImportError:
        fail("'pyyaml' is required to read .smlconfig. Reinstall the suite "
             "(pipx install --force .) or run 'pip install pyyaml'.")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except (OSError, UnicodeDecodeError) as e:
        fail(f"{path}: cannot read: {e}")
    except yaml.YAMLError as e:
        fail(f"{path}: invalid YAML: {e}")
    if data is None:
        return {}
    if not isinstance(data, dict):
        fail(f"{path}: top level must be a mapping of command sections (smlmk:, smlpdtp:, ...)")
    for name, section in data.items():
        if section is not None and not isinstance(section, dict):
            fail(f"{path}: section '{name}' must be a mapping")
    return {k: (v or {}) for k, v in data.items()}


def load_config(work_dir):
    """Return {section: {key: value}} for the project in `work_dir`.

    `.smlconfig` wins; `.pdfmake` is read only when `.smlconfig` is absent.
    """
    d = Path(work_dir)
    sml, legacy = d / CONFIG_NAME, d / LEGACY_NAME
    if sml.is_file():
        if legacy.is_file():
            warn(f"both {CONFIG_NAME} and {LEGACY_NAME} exist; using {CONFIG_NAME}")
        return _parse_smlconfig(sml)
    if legacy.is_file():
        return {"smlmk": _parse_pdfmake(legacy)}
    return {}


def int_option(section, key, default=None):
    """Integer config value; a non-integer is a configuration error, not a traceback."""
    value = section.get(key, default)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        fail(f"config key '{key}' must be an integer, got {value!r}")


def smlmk_section(config):
    """The smlmk section with main/out/tool_chain normalised to lists."""
    section = dict(config.get("smlmk") or {})
    for key in ("main", "out", "tool_chain"):
        if key in section:
            section[key] = as_list(section[key])
    return section


SMLCONFIG_TEMPLATE = """# .smlconfig — smart-latex-suite configuration (YAML, one section per command)
smlmk:
  main: main.tex
  # out: FinalPaper
  # tool_chain: [xelatex, biber, xelatex, xelatex]

# smlpdtp:            # deck markdown -> <pdf>.pdfpc (pdfpc speaker notes)
#   deck: script/deck.md
#   note_font_size: 20

# smlptk:             # PDF + deck -> Keynote (one page per slide + presenter notes)
#   width: 1920
#   master_slide: Blank
"""


# --------------------------------------------------------------------------- pdf

def pdf_info(pdf):
    """(page_count, width_pt, height_pt) via poppler's pdfinfo."""
    pdf = Path(pdf)
    if not pdf.is_file():
        fail(f"PDF not found: {pdf}")
    try:
        out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        fail("'pdfinfo' (poppler) not found on PATH")
    except subprocess.CalledProcessError as e:
        fail(f"pdfinfo failed on {pdf}: {e.stderr.strip()}")
    pages = re.search(r"^Pages:\s+(\d+)", out, re.M)
    size = re.search(r"^Page size:\s+([\d.]+) x ([\d.]+)", out, re.M)
    if not pages or not size:
        fail(f"could not read page count / page size from pdfinfo output for {pdf}")
    return int(pages.group(1)), float(size.group(1)), float(size.group(2))


# --------------------------------------------------------------------------- deck

def parse_deck(text, heading_regex=DECK_HEADING_RE):
    """Split a speaker deck into [(number, title, body)], one per `### Slide N` heading.

    `---` separator lines are dropped from bodies. Numbers must run 1..N without
    gaps or repeats: section N is later mapped onto PDF physical page N, so a
    numbering slip would silently shift every note after it.
    """
    heading = re.compile(heading_regex, re.M)
    matches = list(heading.finditer(text))
    if not matches:
        fail(f"no slide headings matched {heading_regex!r}")
    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        body = re.sub(r"^---\s*$", "", body, flags=re.M).strip("\n").rstrip()
        title = (m.group(2) or "").strip() if m.re.groups >= 2 else ""
        sections.append((int(m.group(1)), title, body))
    numbers = [n for n, _, _ in sections]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        fail(f"slide headings must be numbered 1..{len(numbers)} in order; found {numbers}")
    return sections


def check_page_count(sections, pdf, n_pages):
    if len(sections) != n_pages:
        side = "the deck has more sections than the PDF has pages" if len(sections) > n_pages \
            else "the PDF has more pages than the deck has sections"
        fail(f"deck/PDF mismatch: {len(sections)} deck sections vs {n_pages} pages in {Path(pdf).name} "
             f"({side}). Slide N must be PDF physical page N; fix the deck (or rebuild the PDF) first.")
