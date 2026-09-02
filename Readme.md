# Smart LaTeX Suite

> A frictionless CLI workflow for automated LaTeX compilation and project scaffolding.

**Smart LaTeX Suite** eliminates the boilerplate of LaTeX project management. It consists of four decoupled tools: `smlmk` for intelligent compilation and error parsing, `smltt` for instant project scaffolding, and the presentation pair `smlpdtp` / `smlptk` (**s**mart **m**odular **l**atex **p**resentation) that turn a speaker deck plus a slide PDF into pdfpc notes or a Keynote document.

## ✨ Features

* **Zero-Config Defaults**: Automatically detects compilers (`pdflatex`, `xelatex`, etc.) via magic comments.
* **Clean Logs**: Filters LaTeX's notorious log noise, displaying only critical file:line:error messages.
* **Flexible Toolchains**: Define custom build pipelines (e.g., `xelatex -> biber -> xelatex`) in a simple config file.
* **Project Scaffolding**: Instantly generate folder structures from local templates.
* **Speaker Deck → pdfpc / Keynote**: one markdown deck (`### Slide N — title` sections) drives both the pdfpc speaker notes and a page-per-slide Keynote export, with the deck/PDF page alignment checked every time.
* **One Config File**: `.smlconfig` (YAML) holds a section per command; the legacy `.pdfmake` keeps working.

---

## 📦 Installation

This project is packaged as a standard Python application. The recommended way to install these command-line tools is with `pipx`.

### Recommended: `pipx`

`pipx` installs Python applications in isolated environments, making them available globally without dependency conflicts.

```bash
# 1. Install pipx (if you haven't already)
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# 2. Install the suite from the project's root directory
pipx install .
```

### Alternative: `pip` in a Virtual Environment

If you prefer to manage environments manually:

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install the suite
pip install .
```

---

## 🚀 Usage

### 1. The Builder (`smlmk`)

Run in any directory containing `.tex` files.

| Command | Description |
| :--- | :--- |
| `smlmk` | Auto-detect main file and build. |
| `smlmk -w` | Watch for changes and rebuild automatically. |
| `smlmk -bc` | **Build** then **Clean** auxiliary files (Recommended). |
| `smlmk -v` | Verbose mode (shows full compiler log). |
| `smlmk --init` | Generate a `.smlconfig` template. |
| `smlmk -o Paper`| Compile and rename output to `Paper.pdf`. |

### 2. The Manager (`smltt`)

Manage your local LaTeX templates (stored in `~/.smartlatex/templates` as zip files).

```bash
# Register an existing directory as a template
smltt register thesis-v1 ./my-thesis-folder

# Create a new project from template
smltt new ./Fall2025-Paper -t thesis-v1

# List available templates
smltt list

# Update a template from a new source
smltt update thesis-v1 ./my-new-thesis-folder

# Delete a template
smltt delete thesis-v1
```

### 3. Presentation: deck → pdfpc notes (`smlpdtp`)

`smlpdtp` = **s**mart **m**odular **l**atex **p**resentation, **d**eck **t**o **p**dfpc.
It reads a speaker deck written in markdown and writes `<pdf>.pdfpc`, the JSON sidecar
that [pdfpc](https://pdfpc.github.io) (≥ 4.7) loads automatically next to the PDF.

```bash
smlpdtp                          # deck/PDF from .smlconfig, or the single deck*.md + smlmk's PDF
smlpdtp script/deck.md --pdf main.pdf
smlpdtp --check                  # only verify the deck/PDF alignment, write nothing
pdfpc main.pdf                   # notes appear in the presenter window
```

The deck format is the interface:

```markdown
### Slide 1 — Title page
- 【Greeting】
- 【Title】：
  ...
---
### Slide 2 — Outline
- 【Overview】
```

* One `### Slide N — <title>` heading per PDF **physical** page, numbered 1..N without gaps.
  Beamer's `noframenumbering` makes the number printed on the title-less pages lag the physical page by one;
  pdfpc and Keynote both count physical pages, so the deck must too.
* `---` lines are separators and are dropped from the notes.
* The section count must equal the PDF page count (`pdfinfo`); otherwise the command exits 1 and writes nothing.
  A pattern other than `### Slide N` can be set with `heading_regex` (group 1 = slide number).
* Notes are written with `disableMarkdown: true` so the deck's indentation and line breaks survive verbatim.
* **The deck is the single source of truth.** pdfpc rewrites the `.pdfpc` file when it exits;
  notes edited inside pdfpc (`Ctrl+n`) are lost on the next `smlpdtp` run.

### 4. Presentation: PDF + deck → Keynote (`smlptk`)

`smlptk` (**t**o **K**eynote) is the fallback for venues that accept only `.key`: every PDF page becomes
one slide holding that page as a vector image, and the matching deck section becomes the slide's presenter notes.
Text is not editable in Keynote, but it stays vector: no resolution is baked in.

```bash
smlptk --check                   # split the PDF + compile the AppleScript, do not launch Keynote
smlptk                           # build the document in Keynote (left open, unsaved)
smlptk --out talk.key            # build and save
smlptk --width 1024              # canvas width in Keynote points; height follows the PDF aspect ratio
```

* Keynote cannot import a multi-page PDF one page per slide (it yields a single image showing page 1), so the PDF is
  split with `pdfseparate` and each single-page PDF is placed as an image object filling the canvas.
* The generated AppleScript is checked with `osacompile` before Keynote is launched, so a bad quote in a note
  fails fast instead of leaving a half-built document behind.
* Prefer `--out`: the document is bound to that path before any slide is added. Without it, Keynote autosaves the new document as `Untitled N` into iCloud Drive/Keynote; use *Save As* there, and note the page PDFs are read from the temp directory until the first save.
* Exporting the result from Keynote to `.pptx` rasterises the PDF images (PowerPoint has no PDF object); `.key` and
  Keynote's own PDF export keep them vector.
* `master_slide` (default `Blank`) is looked up by name; on a non-English Keynote set it in `.smlconfig`.

**Requirements**: poppler (`pdfinfo`, `pdfseparate`, e.g. `brew install poppler`); `pdfpc` for `smlpdtp`'s output;
macOS with Keynote for `smlptk`.

-----

## ⚙️ Configuration (`.smlconfig`)

Place a `.smlconfig` (YAML) in your project root; `smlmk --init` writes a template. One section per command,
every key optional:

```yaml
smlmk:
  main: main.tex                   # entry file (optional if only one .tex exists)
  out: Final_Submission            # output filename (auto-renames final PDF)
  # custom build chain (overrides auto-detection); supports
  # pdflatex, xelatex, lualatex, latex, uplatex, platex, bibtex, upbibtex, biber, dvipdfmx, makeglossaries
  tool_chain: [xelatex, biber, xelatex, xelatex]

smlpdtp:
  deck: script/deck.md             # speaker deck (markdown)
  pdf: main.pdf                    # defaults to smlmk out/main + .pdf
  note_font_size: 20
  # duration: 12                   # minutes, shown by pdfpc's timer
  # heading_regex: '^### Slide (\d+)'

smlptk:
  # deck / pdf fall back to the smlpdtp values
  width: 1920                      # Keynote canvas width in points
  master_slide: Blank
```

**Legacy `.pdfmake`** (`key=value`, `#` comments, smlmk only) is still read when no `.smlconfig` exists;
if both are present `.smlconfig` wins and a warning is printed.

```ini
main = main.tex
out = Final_Submission
tool_chain = xelatex, biber, xelatex, xelatex
```

