# GEMINI.md

## Project Overview

This project, "Smart LaTeX Suite," is a collection of command-line tools designed to simplify and automate the LaTeX workflow. It consists of two main Python 3 scripts: `smartlatex` and `latextemplates`. The project is written entirely in Python 3 and relies only on the standard library, so there are no external dependencies to install.

*   **`smartlatex`**: An intelligent LaTeX build tool. It can automatically detect the required compiler (e.g., `pdflatex`, `xelatex`) from magic comments in the `.tex` file, or use a custom build chain defined in a `.pdfmake` configuration file. It also parses the LaTeX output to provide a clean, user-friendly error summary.

*   **`latextemplates`**: A project scaffolding tool. It allows users to register existing directories as templates and then create new projects from these templates. Templates are stored in `~/.smartlatex/templates`.

*   **Configuration (`.pdfmake`)**: The behavior of `smartlatex` can be customized on a per-project basis using a `.pdfmake` file in the project's root directory. This file can specify the main `.tex` file, the output file name, and a custom tool chain.

## Building and Running

### Installation

The project does not have an automated installation script (the `install` script is currently empty). To install, you need to make the scripts executable and move them to a directory in your system's `PATH`.

```bash
chmod +x smartlatex latextemplates
sudo mv smartlatex /usr/local/bin/
sudo mv latextemplates /usr/local/bin/
```

### Running the Tools

#### `smartlatex`

To build a LaTeX project, run `smartlatex` in the directory containing your `.tex` files.

*   **Build:** `smartlatex`
*   **Build and clean:** `smartlatex -bc`
*   **Generate a config file:** `smartlatex --init`
*   **Specify output name:** `smartlatex -o MyPaper`

#### `latextemplates`

To manage your LaTeX templates:

*   **Register a template:** `latextemplates register <template-name> <path-to-template>`
*   **Create a new project:** `latextemplates new <project-name> -t <template-name>`
*   **List templates:** `latextemplates list`

## Development Conventions

*   **Language**: The project is written in Python 3.
*   **Command-Line Interface**: The scripts use the `argparse` module to define and parse command-line arguments.
*   **File Paths**: The code uses a mix of `os.path` and the more modern `pathlib` module for path manipulation. Future development should aim to use `pathlib` consistently.
*   **Testing**: There is no formal testing framework or test suite set up for this project.
*   **Dependencies**: The project uses only the Python standard library. No `requirements.txt` or other dependency management is currently in place.
