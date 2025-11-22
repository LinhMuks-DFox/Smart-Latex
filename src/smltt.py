#!/usr/bin/env python3
"""
Smart Latex Template(sm-lt-t, smart latex template) Manager
============================

Manages local LaTeX project templates.

Usage:
    smltt register <name> <path>
    smltt list
    smltt new <project_name> --template <name>
    smltt delete <name>
"""

import argparse
import shutil
import sys
import os
from pathlib import Path

# 模板存储位置: ~/.smartlatex/templates
TEMPLATE_STORE = Path.home() / ".smartlatex" / "templates"

class Colors:
    GREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def init_store():
    if not TEMPLATE_STORE.exists():
        TEMPLATE_STORE.mkdir(parents=True, exist_ok=True)

def cmd_register(args):
    init_store()
    src_path = Path(args.path).resolve()
    dest_archive_base = TEMPLATE_STORE / args.name
    dest_archive_path = str(dest_archive_base) + ".zip"

    if not src_path.exists() or not src_path.is_dir():
        print(f"{Colors.FAIL}Error: Source path '{src_path}' does not exist or is not a directory.{Colors.ENDC}")
        sys.exit(1)

    if Path(dest_archive_path).exists():
        print(f"{Colors.FAIL}Error: Template '{args.name}' already exists.{Colors.ENDC}")
        sys.exit(1)

    try:
        # shutil.make_archive will create a zip file at dest_archive_path
        shutil.make_archive(str(dest_archive_base), 'zip', str(src_path))
        print(f"{Colors.GREEN}Template '{args.name}' registered successfully.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}Error registering template: {e}{Colors.ENDC}")
        sys.exit(1)

def cmd_new(args):
    init_store()
    template_archive = TEMPLATE_STORE / f"{args.template}.zip"
    project_path = Path(args.project_name).resolve()

    if not template_archive.exists():
        print(f"{Colors.FAIL}Error: Template '{args.template}' not found.{Colors.ENDC}")
        print(f"Run 'list' to see available templates.")
        sys.exit(1)

    if project_path.exists():
        print(f"{Colors.FAIL}Error: Target directory '{project_path}' already exists.{Colors.ENDC}")
        sys.exit(1)

    try:
        print(f"Creating project '{args.project_name}' from template '{args.template}'...")
        shutil.unpack_archive(str(template_archive), str(project_path), 'zip')
        
        # 确保 assets 目录存在
        assets_dir = project_path / "assets"
        assets_dir.mkdir(exist_ok=True)

        print(f"{Colors.GREEN}Project created at: {project_path}{Colors.ENDC}")
        
        # 检查是否有 .pdfmake
        if (project_path / ".pdfmake").exists():
            print("Note: Included .pdfmake configuration.")
        else:
            print("Note: No .pdfmake found in template. Run `smartlatex --init` inside the folder to generate one.")

    except Exception as e:
        print(f"{Colors.FAIL}Error creating project: {e}{Colors.ENDC}")
        sys.exit(1)

def cmd_list(args):
    init_store()
    templates = [p.stem for p in TEMPLATE_STORE.glob('*.zip') if p.is_file()]
    if not templates:
        print("No templates registered.")
    else:
        print(f"{Colors.BOLD}Available Templates:{Colors.ENDC}")
        for t in sorted(templates):
            print(f"  - {t}")

def cmd_delete(args):
    init_store()
    target = TEMPLATE_STORE / f"{args.name}.zip"
    if not target.exists():
        print(f"{Colors.FAIL}Template '{args.name}' not found.{Colors.ENDC}")
        sys.exit(1)
    
    target.unlink() # os.remove(target)
    print(f"{Colors.GREEN}Template '{args.name}' deleted.{Colors.ENDC}")

def cmd_update(args):
    init_store()
    template_archive = TEMPLATE_STORE / f"{args.name}.zip"
    src_path = Path(args.path).resolve()

    if not template_archive.exists():
        print(f"{Colors.FAIL}Template '{args.name}' not found. Cannot update.{Colors.ENDC}")
        sys.exit(1)
    
    if not src_path.exists() or not src_path.is_dir():
        print(f"{Colors.FAIL}Error: New source path '{src_path}' does not exist or is not a directory.{Colors.ENDC}")
        sys.exit(1)

    try:
        # Delete old archive
        template_archive.unlink()
        
        # Create new one
        dest_archive_base = TEMPLATE_STORE / args.name
        shutil.make_archive(str(dest_archive_base), 'zip', str(src_path))
        print(f"{Colors.GREEN}Template '{args.name}' updated successfully.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}Error updating template: {e}{Colors.ENDC}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Register
    p_reg = subparsers.add_parser('register', help='Register a new template from a directory')
    p_reg.add_argument('name', help='Name for the template')
    p_reg.add_argument('path', help='Path to the source directory')
    p_reg.set_defaults(func=cmd_register)

    # New
    p_new = subparsers.add_parser('new', help='Create a new project from a template')
    p_new.add_argument('project_name', help='Name of the new project directory')
    p_new.add_argument('--template', '-t', required=True, help='Name of the template to use')
    p_new.set_defaults(func=cmd_new)

    # List
    p_list = subparsers.add_parser('list', help='List registered templates')
    p_list.set_defaults(func=cmd_list)

    # Delete
    p_del = subparsers.add_parser('delete', help='Delete a registered template')
    p_del.add_argument('name', help='Name of the template to delete')
    p_del.set_defaults(func=cmd_delete)

    # Update
    p_upd = subparsers.add_parser('update', help='Update an existing template from a new path')
    p_upd.add_argument('name', help='Name of the template to update')
    p_upd.add_argument('path', help='Path to the new source directory')
    p_upd.set_defaults(func=cmd_update)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()