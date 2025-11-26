#!/usr/bin/env python3
"""
Smart Latex Template (smltt) Manager
====================================

Manages local and remote LaTeX project templates.

Usage:
    smltt register <name> --path <path>
    smltt register <name> --url <url> [--download | --lazydownload]
    smltt new <project_name> -t <template>
    smltt list
    smltt delete <name>
    smltt update <name>

Commands:
  register    Register a new template.
              - From a local path:
                  smltt register my-template --path /path/to/template/dir
              - From a Git repository:
                  smltt register my-git-template --url https://github.com/user/repo.git
              - From a direct URL to a .zip file:
                  smltt register my-zip-template --url http://example.com/template.zip --download
                  (use --lazydownload to download it on first use)

  new         Create a new project from a template.
              smltt new MyNewProject -t my-template

  list        List all available templates.
              Shows the name, type (local, git, url), and status.

  delete      Delete a template and all its assets.
              smltt delete my-template

  update      Update a template from its original source (git or URL).
              smltt update my-template
              (Local path-based templates cannot be updated.)
"""

import argparse
import shutil
import sys
import os
import json
import urllib.request
import subprocess
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

def _write_template_metadata(name, metadata):
    meta_path = TEMPLATE_STORE / f"{name}.json"
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)

def _register_from_path(args):
    src_path = Path(args.path).resolve()
    if not src_path.exists() or not src_path.is_dir():
        print(f"{Colors.FAIL}Error: Source path '{src_path}' does not exist or is not a directory.{Colors.ENDC}")
        sys.exit(1)

    dest_archive_base = TEMPLATE_STORE / args.name
    try:
        shutil.make_archive(str(dest_archive_base), 'zip', str(src_path))
        _write_template_metadata(args.name, {'source': 'local', 'path': str(src_path)})
        print(f"{Colors.GREEN}Template '{args.name}' registered successfully from path '{src_path}'.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}Error registering template: {e}{Colors.ENDC}")
        sys.exit(1)

def _download_template(name, url):
    dest_zip = TEMPLATE_STORE / f"{name}.zip"
    print(f"Downloading template '{name}' from {url}...")
    try:
        urllib.request.urlretrieve(url, dest_zip)
        # Update metadata if it exists
        meta_path = TEMPLATE_STORE / f"{name}.json"
        if meta_path.exists():
            with open(meta_path, 'r+') as f:
                metadata = json.load(f)
                metadata['status'] = 'downloaded'
                f.seek(0)
                json.dump(metadata, f, indent=2)
        return True
    except Exception as e:
        print(f"{Colors.FAIL}Error downloading template: {e}{Colors.ENDC}")
        return False

def _register_from_url(args):
    url = args.url
    name = args.name
    is_git_repo = url.endswith('.git')

    if is_git_repo:
        if args.download or args.lazydownload:
            print(f"Note: --download / --lazydownload flags are ignored for git repositories.")
        
        dest_path = TEMPLATE_STORE / name
        print(f"Cloning git repository from {url}...")
        # Using subprocess to run git clone for better error handling
        result = subprocess.run(["git", "clone", url, str(dest_path)], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"{Colors.FAIL}Error cloning repository:\n{result.stderr}{Colors.ENDC}")
            sys.exit(1)
        
        _write_template_metadata(name, {"source": "git", "url": url})
        print(f"{Colors.GREEN}Template '{name}' registered successfully from git repository.{Colors.ENDC}")

    else:  # Assumed to be a direct download link
        metadata = {"source": "url", "url": url}
        if args.download:
            if _download_template(name, url):
                metadata["status"] = "downloaded"
                _write_template_metadata(name, metadata)
                print(f"{Colors.GREEN}Template '{name}' downloaded and registered successfully.{Colors.ENDC}")
            else:
                sys.exit(1)
        else:  # Lazy download is the default
            metadata["status"] = "lazy"
            _write_template_metadata(name, metadata)
            print(f"{Colors.GREEN}Template '{name}' registered for lazy download.{Colors.ENDC}")
            print("It will be downloaded the first time you use it.")

def cmd_register(args):
    init_store()
    template_name = args.name
    template_zip_path = TEMPLATE_STORE / f"{template_name}.zip"
    template_dir_path = TEMPLATE_STORE / template_name
    template_meta_path = TEMPLATE_STORE / f"{template_name}.json"

    if template_zip_path.exists() or template_dir_path.exists() or template_meta_path.exists():
        print(f"{Colors.FAIL}Error: Template '{template_name}' already exists.{Colors.ENDC}")
        sys.exit(1)

    if args.path:
        _register_from_path(args)
    elif args.url:
        _register_from_url(args)
    else:
        # This case should not be reached due to argparse configuration
        print(f"{Colors.FAIL}Error: You must specify either a --path or a --url.{Colors.ENDC}")
        sys.exit(1)

def cmd_new(args):
    init_store()
    template_name = args.template
    project_path = Path(args.project_name).resolve()

    if project_path.exists():
        print(f"{Colors.FAIL}Error: Target directory '{project_path}' already exists.{Colors.ENDC}")
        sys.exit(1)

    template_dir = TEMPLATE_STORE / template_name
    template_zip = TEMPLATE_STORE / f"{template_name}.zip"
    template_meta = TEMPLATE_STORE / f"{template_name}.json"

    try:
        if template_dir.is_dir():
            print(f"Creating project '{args.project_name}' from git template '{template_name}'...")
            # Ignore .git directory when copying
            shutil.copytree(template_dir, project_path, ignore=shutil.ignore_patterns('.git'))
        elif template_zip.is_file():
            print(f"Creating project '{args.project_name}' from template '{template_name}'...")
            shutil.unpack_archive(str(template_zip), str(project_path), 'zip')
        elif template_meta.is_file():
            with open(template_meta, 'r') as f:
                metadata = json.load(f)
            if metadata.get('source') == 'url' and metadata.get('status') == 'lazy':
                print(f"Template '{template_name}' is a lazy URL, downloading now.")
                if not _download_template(template_name, metadata['url']):
                    sys.exit(1)
                # After download, the zip file should exist
                if template_zip.is_file():
                    print(f"Creating project '{args.project_name}' from template '{template_name}'...")
                    shutil.unpack_archive(str(template_zip), str(project_path), 'zip')
                else:
                    print(f"{Colors.FAIL}Error: Failed to find downloaded template zip file.{Colors.ENDC}")
                    sys.exit(1)
            else:
                print(f"{Colors.FAIL}Error: Invalid metadata for template '{template_name}'.{Colors.ENDC}")
                sys.exit(1)
        else:
            print(f"{Colors.FAIL}Error: Template '{template_name}' not found.{Colors.ENDC}")
            print(f"Run 'smltt list' to see available templates.")
            sys.exit(1)

        # Common post-creation steps
        assets_dir = project_path / "assets"
        assets_dir.mkdir(exist_ok=True)
        print(f"{Colors.GREEN}Project created at: {project_path}{Colors.ENDC}")
        if (project_path / ".pdfmake").exists():
            print("Note: Included .pdfmake configuration.")
        else:
            print("Note: No .pdfmake found in template. Run `smartlatex --init` inside the folder to generate one.")

    except Exception as e:
        print(f"{Colors.FAIL}Error creating project: {e}{Colors.ENDC}")
        sys.exit(1)

def cmd_list(args):
    init_store()
    templates = {}

    for p in TEMPLATE_STORE.iterdir():
        if p.is_dir():
            templates[p.name] = {'status': 'git'}
        elif p.suffix == '.zip':
            name = p.stem
            if name not in templates:
                templates[name] = {}
            templates[name]['zip'] = True
        elif p.suffix == '.json':
            name = p.stem
            if name not in templates:
                templates[name] = {}
            templates[name]['meta'] = p

    if not templates:
        print("No templates registered.")
        return

    print(f"{Colors.BOLD}Available Templates:{Colors.ENDC}")
    for name in sorted(templates.keys()):
        info = templates[name]
        status = info.get('status')
        if status == 'git':
            details = '(git repo)'
        elif 'zip' in info:
            details = '(local)'
            if 'meta' in info:
                with open(info['meta'], 'r') as f:
                    meta = json.load(f)
                if meta.get('source') == 'url':
                    details = '(url, downloaded)'
        elif 'meta' in info:
            with open(info['meta'], 'r') as f:
                meta = json.load(f)
            if meta.get('status') == 'lazy':
                details = '(url, lazy download)'
            else:
                details = '(meta only)'
        else:
            details = '(unknown)'
        
        print(f"  - {name} {details}")

def cmd_delete(args):
    init_store()
    name = args.name
    template_dir = TEMPLATE_STORE / name
    template_zip = TEMPLATE_STORE / f"{name}.zip"
    template_meta = TEMPLATE_STORE / f"{name}.json"

    found = False
    if template_dir.exists():
        found = True
        try:
            shutil.rmtree(template_dir)
        except Exception as e:
            print(f"{Colors.FAIL}Error removing directory {template_dir}: {e}{Colors.ENDC}")
            sys.exit(1)
            
    if template_zip.exists():
        found = True
        template_zip.unlink()
        
    if template_meta.exists():
        found = True
        template_meta.unlink()

    if not found:
        print(f"{Colors.FAIL}Template '{name}' not found.{Colors.ENDC}")
        sys.exit(1)
    
    print(f"{Colors.GREEN}Template '{name}' and all its assets deleted.{Colors.ENDC}")

def cmd_update(args):
    init_store()
    name = args.name
    meta_path = TEMPLATE_STORE / f"{name}.json"

    if not meta_path.exists():
        # Check if it's a legacy local template (zip only, no meta)
        if (TEMPLATE_STORE / f"{name}.zip").exists():
            print(f"Template '{name}' is a local template and cannot be automatically updated.")
        else:
            print(f"{Colors.FAIL}Template '{name}' not found or has no metadata for updating.{Colors.ENDC}")
        sys.exit(1)

    with open(meta_path, 'r') as f:
        metadata = json.load(f)

    source_type = metadata.get('source')
    url = metadata.get('url')

    if source_type == 'git':
        template_dir = TEMPLATE_STORE / name
        if not template_dir.is_dir():
            print(f"{Colors.FAIL}Error: Git template directory not found at '{template_dir}'.{Colors.ENDC}")
            sys.exit(1)
        
        print(f"Updating git template '{name}' from {url}...")
        # Change directory and run git pull
        try:
            result = subprocess.run(["git", "-C", str(template_dir), "pull"], check=True, capture_output=True, text=True)
            print(result.stdout)
            print(f"{Colors.GREEN}Template '{name}' updated successfully.{Colors.ENDC}")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.FAIL}Error updating git repository:\n{e.stderr}{Colors.ENDC}")
            sys.exit(1)
        except Exception as e:
            print(f"{Colors.FAIL}An unexpected error occurred: {e}{Colors.ENDC}")
            sys.exit(1)

    elif source_type == 'url':
        print(f"Updating URL template '{name}' from {url}...")
        if _download_template(name, url):
            print(f"{Colors.GREEN}Template '{name}' re-downloaded and updated successfully.{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}Failed to update template '{name}'.{Colors.ENDC}")
            sys.exit(1)
            
    elif source_type == 'local':
        print(f"Template '{name}' is a local template and cannot be automatically updated.")
        print(f"To update it, delete the existing template and register the new version.")
    else:
        print(f"{Colors.FAIL}Unknown template source type: {source_type}{Colors.ENDC}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Register
    p_reg = subparsers.add_parser('register', help='Register a new template')
    p_reg.add_argument('name', help='Name for the template')
    source_group = p_reg.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--path', help='Path to the source directory')
    source_group.add_argument('--url', help='URL to a git repository or a zip file')

    download_group = p_reg.add_mutually_exclusive_group()
    download_group.add_argument('--download', action='store_true', help='Download the template immediately (for non-git URLs)')
    download_group.add_argument('--lazydownload', action='store_true', help='Download the template when used for the first time (for non-git URLs)')
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
    p_upd = subparsers.add_parser('update', help='Update an existing template from its source (git or URL)')
    p_upd.add_argument('name', help='Name of the template to update')
    p_upd.set_defaults(func=cmd_update)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()