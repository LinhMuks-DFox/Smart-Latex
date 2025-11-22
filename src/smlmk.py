#!/usr/bin/env python3
"""
Smart LaTeX Build Tool (smlmk, sm-l-mk, smart latex make)
======================

A configurable, automated build script for LaTeX projects.

Features:
    1. **Auto-Detection**: Detects `%!TEX program` magic comments.
    2. **Configuration**: Per-directory `.pdfmake` config files.
    3. **Error Parsing**: Filters LaTeX log noise.
    4. **Workflow**: Handles clean/build cycles and DVI->PDF.

Usage:
    ./make [TARGET] [OPTIONS]

Arguments:
    TARGET           Directory or .tex file. (Defaults to current dir)
    --init           Create a template .pdfmake config file in current dir.
    -c, --clean      Clean auxiliary files.
    -b, --build      Execute build.
    -bc              Build then clean.
    -cb              Clean then build.
    -o NAME          Rename final PDF.
    -v               Verbose debug logging.

Configuration File (.pdfmake):
    key=value format. Comments start with #.
    
    main=main.tex
    out=FinalPaper
    compiler=xelatex
    # Simple comma-separated list for tool chain:
    tool_chain=xelatex, biber, xelatex, xelatex
"""
import os
import subprocess
import argparse
import sys
import re
import time
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print(f"Error: 'watchdog' library not found. Please run 'pip install watchdog'", file=sys.stderr)
    sys.exit(1)

VERBOSE = False

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def debug(msg):
    if VERBOSE:
        print(f"{Colors.BLUE}[DEBUG] {msg}{Colors.ENDC}", file=sys.stderr)

TOOL_MAP = {
    "pdflatex": "pdflatex -file-line-error -interaction=nonstopmode {file}.tex",
    "xelatex":  "xelatex -file-line-error -interaction=nonstopmode {file}.tex",
    "lualatex": "lualatex -file-line-error -interaction=nonstopmode {file}.tex",
    "latex":    "latex -file-line-error -interaction=nonstopmode {file}.tex",
    "dvipdfmx": "dvipdfmx {file}",
    "biber":    "biber {file}",
    "bibtex":   "bibtex {file}",
    "makeglossaries": "makeglossaries {file}"
}

clean_files = [
    "*.aux", "*.bbl", "*.blg", "*.dvi", "*.out", "*.log", "*.toc",
    "*.lof", "*.lot", "build/", "*.synctex.gz", "*.fls",
    "*.fdb_latexmk", "*.bcf", "*.run.xml", "*.glg", "*.gls", "*.glsdefs", "*.ist",
    "*.nav", "*.snm"
]

def create_template_config():
    content = """# .pdfmake configuration file
main=main.tex
# out=FinalPaper
# tool_chain = xelatex, bibtex, xelatex, xelatex
"""
    p = Path(".pdfmake")
    if p.exists():
        print(f"{Colors.WARNING}File .pdfmake already exists. Skipping.{Colors.ENDC}")
    else:
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"{Colors.GREEN}Created template .pdfmake{Colors.ENDC}")

def clean(rules=clean_files):
    print(f"{Colors.CYAN}Cleaning auxiliary files...{Colors.ENDC}")
    for pattern in rules:
        subprocess.run(f"rm -rf {pattern}", shell=True, capture_output=True)

def print_error_summary(stdout_content):
    print(f"\n{Colors.FAIL}================ BUILD FAILED ================ {Colors.ENDC}")
    found_error = False
    lines = stdout_content.splitlines()
    file_line_pattern = re.compile(r'^.*:\d+:.*')
    tex_error_pattern = re.compile(r'^! .*')

    for i, line in enumerate(lines):
        if file_line_pattern.match(line) or tex_error_pattern.match(line):
            print(f"{Colors.FAIL}>> {line}{Colors.ENDC}")
            if tex_error_pattern.match(line) and i + 1 < len(lines) and lines[i+1].strip().startswith('l.'):
                print(f"{Colors.CYAN}   {lines[i+1].strip()}{Colors.ENDC}")
            found_error = True

    if not found_error:
        print(f"{Colors.WARNING}Last 20 lines:{Colors.ENDC}")
        print('\n'.join(lines[-20:]))
    print(f"{Colors.FAIL}============================================== {Colors.ENDC}")

def detect_compiler(tex_file_path):
    debug(f"Detecting compiler from: {tex_file_path}")
    try:
        with open(tex_file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i > 20: break
                m = re.match(r'%\s*!TEX\s+(?:TS-)?program\s*=\s*([a-zA-Z0-9]+)', line, re.IGNORECASE)
                if m: return m.group(1).lower()
                m2 = re.match(r'%\s*!TEX\s+(pdflatex|xelatex|lualatex|latex)\b', line, re.IGNORECASE)
                if m2: return m2.group(1).lower()
    except Exception:
        pass
    return "pdflatex"

def generate_build_rules(config, tex_file_path):
    # 1. 获取基础编译器（检测 或 配置指定）
    detected = detect_compiler(tex_file_path)
    compiler = config.get('compiler', detected)

    rules = []
    chain_names = []

    # 2. 逻辑修正：优先判断是否存在 tool_chain
    if 'tool_chain' in config and config['tool_chain']:
        chain_names = config['tool_chain']
        # 如果定义了 tool_chain，打印它而不是打印默认编译器
        print(f"{Colors.CYAN}Custom Tool Chain: {', '.join(chain_names)}{Colors.ENDC}")
    else:
        # 只有没有 tool_chain 时，才打印检测到的编译器
        print(f"Compiler: {Colors.GREEN}{compiler}{Colors.ENDC}")
        if compiler == 'latex':
            chain_names = [compiler, "biber", compiler, compiler, "dvipdfmx"]
        else:
            chain_names = [compiler, "biber", compiler, compiler]

    # 3. 生成命令列表
    for tool in chain_names:
        # 支持 tool_chain 里写 "compiler" 占位符
        if tool == "compiler":
            real_tool = compiler
        else:
            real_tool = tool
        
        # 如果工具在 MAP 里则取 MAP，否则认为是一个直接命令
        rules.append(TOOL_MAP.get(real_tool, f"{real_tool} {{file}}"))
        
    return rules

def build(file_basename, rules):
    if not Path(f"{file_basename}.tex").exists():
        print(f"{Colors.FAIL}Error: '{file_basename}.tex' not found.{Colors.ENDC}", file=sys.stderr)
        return False
    
    total = len(rules)
    for idx, rule in enumerate(rules):
        cmd = rule.format(file=file_basename)
        print(f"{Colors.BOLD}[{idx+1}/{total}]{Colors.ENDC} {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print_error_summary(result.stdout)
            if VERBOSE:
                print(f"\n{Colors.WARNING}------ FULL OUTPUT (STDOUT) ------{Colors.ENDC}")
                print(result.stdout)
                if result.stderr:
                    print(f"\n{Colors.WARNING}------ STDERR ------{Colors.ENDC}")
                    print(result.stderr, file=sys.stderr)
            else:
                # 提示用户可以使用 -v
                print(f"\n{Colors.CYAN}(Run with -v to see the full log){Colors.ENDC}")
                
            return False
    return True

def load_config(work_dir):
    config = {}
    config_path = Path(work_dir) / ".pdfmake"
    if config_path.is_file():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.split('#', 1)[0].strip()
                    if not line or '=' not in line: continue
                    key, val = line.split('=', 1)
                    key, val = key.strip(), val.strip()
                    if key == 'tool_chain':
                        val = val.replace('[', '').replace(']', '')
                        val = [x.strip() for x in val.split(',') if x.strip()]
                    config[key] = val
        except Exception as e:
            print(f"{Colors.WARNING}Warning: Failed to read .pdfmake: {e}{Colors.ENDC}", file=sys.stderr)
    return config

def resolve_target(target_path):
    path = Path(target_path).resolve()
    if path.is_dir():
        config = load_config(path)
        basename = Path(config['main']).stem if 'main' in config else None
        if not basename:
            tex_files = list(path.glob('*.tex'))
            if len(tex_files) == 1: basename = tex_files[0].stem
            else: return str(path), None, config
        return str(path), basename, config
    elif path.suffix == '.tex':
        return str(path.parent), path.stem, load_config(path.parent)
    return None, None, {}

class BuildHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        self.last_triggered = 0
        self.debounce_interval = 0.5  # seconds

    def on_any_event(self, event):
        # Ignore changes to PDF files to avoid loops
        if event.src_path.endswith('.pdf'):
            return
            
        current_time = time.time()
        if current_time - self.last_triggered > self.debounce_interval:
            self.last_triggered = current_time
            print(f"\n{Colors.CYAN}--- Detected change in {event.src_path}, rebuilding ---{Colors.ENDC}")
            self.callback()

def main():
    global VERBOSE
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('target', nargs='?', default='.', help="Target dir or .tex file")
    parser.add_argument('--init', action='store_true', help="Generate config template")
    parser.add_argument("-c", "--clean", action="store_true")
    parser.add_argument("-b", "--build", action="store_true")
    parser.add_argument("-bc", "--build-clean", action="store_true")
    parser.add_argument("-cb", "--clean-build", action="store_true")
    parser.add_argument("-o", "--output", help="Rename output PDF")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-w", "--watch", action="store_true", help="Watch for file changes and rebuild automatically")

    args = parser.parse_args()
    VERBOSE = args.verbose

    if args.init:
        create_template_config(); sys.exit(0)

    work_dir, file_basename, config = resolve_target(args.target)
    if not work_dir: print(f"{Colors.FAIL}Invalid target.{Colors.ENDC}"); sys.exit(1)
    
    original_cwd = Path.cwd()
    os.chdir(work_dir)

    def run_build_cycle():
        if not file_basename and not args.clean:
             print(f"{Colors.FAIL}Error: No main file found.{Colors.ENDC}", file=sys.stderr); return
        
        no_flags = not any([args.clean, args.build, args.build_clean, args.clean_build, args.watch])
        do_build = args.build or args.build_clean or args.clean_build or no_flags or args.watch

        if args.clean_build or args.clean: clean()

        success = False
        if do_build and file_basename:
            rules = generate_build_rules(config, f"{file_basename}.tex")
            success = build(file_basename, rules)
            if success:
                print(f"{Colors.GREEN}================ BUILD SUCCEEDED ================{Colors.ENDC}")


        if args.build_clean and success: clean()

        final_out = args.output if args.output else config.get('out')
        if success and final_out:
            src = f"{file_basename}.pdf"
            dst = f"{final_out}.pdf" if not final_out.endswith('.pdf') else final_out
            if dst.endswith('.tex'): dst += ".pdf"
            
            if Path(src).exists() and src != dst:
                Path(src).rename(dst)
                print(f"Output: {Colors.GREEN}{dst}{Colors.ENDC}")
    
    try:
        if args.watch:
            if not file_basename:
                print(f"{Colors.FAIL}Error: Cannot watch without a main file to build.{Colors.ENDC}", file=sys.stderr)
                sys.exit(1)
            
            # Run once before watching
            run_build_cycle()

            event_handler = BuildHandler(run_build_cycle)
            observer = Observer()
            observer.schedule(event_handler, '.', recursive=True)
            observer.start()
            
            print(f"\n{Colors.BOLD}{Colors.CYAN}Watching for file changes. Press Ctrl+C to stop.{Colors.ENDC}")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
                print(f"\n{Colors.WARNING}Watcher stopped.{Colors.ENDC}")
            observer.join()
        else:
            run_build_cycle()

    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    main()