# Smart LaTeX Suite

> A frictionless CLI workflow for automated LaTeX compilation and project scaffolding.

**Smart LaTeX Suite** eliminates the boilerplate of LaTeX project management. It consists of two decoupled tools: `muxpdfmk` for intelligent compilation and error parsing, and `smartlatex_template` for instant project scaffolding.

## ✨ Features

* **Zero-Config Defaults**: Automatically detects compilers (`pdflatex`, `xelatex`, etc.) via magic comments.
* **Clean Logs**: Filters LaTeX's notorious log noise, displaying only critical file:line:error messages.
* **Flexible Toolchains**: Define custom build pipelines (e.g., `xelatex -> biber -> xelatex`) in a simple config file.
* **Project Scaffolding**: Instantly generate folder structures from local templates.

---

## 📦 Installation

Place the scripts in your executable path:

```bash
chmod +x muxpdfmk smartlatex_template
sudo mv muxpdfmk /usr/local/bin/
sudo mv smartlatex_template /usr/local/bin/
````

-----

## 🚀 Usage

### 1\. The Builder (`muxpdfmk`)

Run in any directory containing `.tex` files.

| Command | Description |
| :--- | :--- |
| `muxpdfmk` | Auto-detect main file and build. |
| `muxpdfmk -bc` | **Build** then **Clean** auxiliary files (Recommended). |
| `muxpdfmk -v` | Verbose mode (shows full compiler log). |
| `muxpdfmk --init` | Generate a `.pdfmake` config file. |
| `muxpdfmk -o Paper`| Compile and rename output to `Paper.pdf`. |

### 2\. The Manager (`smartlatex_template`)

Manage your local LaTeX templates (stored in `~/.smartlatex/templates`).

```bash
# Register an existing directory as a template
smartlatex_template register thesis-v1 ./my-thesis-folder

# Create a new project from template
smartlatex_template new ./Fall2025-Paper -t thesis-v1

# List available templates
smartlatex_template list
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

