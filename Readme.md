# Smart LaTeX Suite

> A frictionless CLI workflow for automated LaTeX compilation and project scaffolding.

**Smart LaTeX Suite** eliminates the boilerplate of LaTeX project management. It consists of two decoupled tools: `smlmk` for intelligent compilation and error parsing, and `smltt` for instant project scaffolding.

## ✨ Features

* **Zero-Config Defaults**: Automatically detects compilers (`pdflatex`, `xelatex`, etc.) via magic comments.
* **Clean Logs**: Filters LaTeX's notorious log noise, displaying only critical file:line:error messages.
* **Flexible Toolchains**: Define custom build pipelines (e.g., `xelatex -> biber -> xelatex`) in a simple config file.
* **Project Scaffolding**: Instantly generate folder structures from local templates.

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
| `smlmk --init` | Generate a `.pdfmake` config file. |
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

-----

## ⚙️ Configuration (`.pdfmake`)

Place a `.pdfmake` file in your project root to override defaults.

```ini
# Entry file (optional if only one .tex exists)
main = main.tex

# Output filename (auto-renames final PDF)
out = Final_Submission

# Custom Build Chain (overrides auto-detection)
# Supports: pdflatex, xelatex, lualatex, bibtex, biber, dvipdfmx, makeglossaries
tool_chain = xelatex, biber, xelatex, xelatex
```

