# Smart LaTeX Suite

> A frictionless CLI workflow for automated LaTeX compilation and project scaffolding.

**Smart LaTeX Suite** eliminates the boilerplate of LaTeX project management. It consists of two decoupled tools: `smartlatex` for intelligent compilation and error parsing, and `latextemplates` for instant project scaffolding.

## ✨ Features

* **Zero-Config Defaults**: Automatically detects compilers (`pdflatex`, `xelatex`, etc.) via magic comments.
* **Clean Logs**: Filters LaTeX's notorious log noise, displaying only critical file:line:error messages.
* **Flexible Toolchains**: Define custom build pipelines (e.g., `xelatex -> biber -> xelatex`) in a simple config file.
* **Project Scaffolding**: Instantly generate folder structures from local templates.

---

## 📦 Installation

Place the scripts in your executable path:

```bash
chmod +x smartlatex latextemplates
sudo mv smartlatex /usr/local/bin/
sudo mv latextemplates /usr/local/bin/
````

-----

## 🚀 Usage

### 1\. The Builder (`smartlatex`)

Run in any directory containing `.tex` files.

| Command | Description |
| :--- | :--- |
| `smartlatex` | Auto-detect main file and build. |
| `smartlatex -bc` | **Build** then **Clean** auxiliary files (Recommended). |
| `smartlatex -v` | Verbose mode (shows full compiler log). |
| `smartlatex --init` | Generate a `.pdfmake` config file. |
| `smartlatex -o Paper`| Compile and rename output to `Paper.pdf`. |

### 2\. The Manager (`latextemplates`)

Manage your local LaTeX templates (stored in `~/.smartlatex/templates`).

```bash
# Register an existing directory as a template
latextemplates register thesis-v1 ./my-thesis-folder

# Create a new project from template
latextemplates new ./Fall2025-Paper -t thesis-v1

# List available templates
latextemplates list
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

