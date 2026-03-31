"""
Create a clean distribution ZIP of RealizeOS Full Edition.

Includes all code and templates, excludes personal data and dev artifacts.
The output ZIP is a complete, standalone package for new users.

Usage:
    python create_release_zip.py
"""

import os
import zipfile
from pathlib import Path

SOURCE_DIR = Path(__file__).parent.resolve()
ZIP_NAME = "RealizeOS-Full-V03.zip"
OUTPUT_PATH = SOURCE_DIR / ZIP_NAME
PREFIX = "RealizeOS-Full-V03"

# --- Directories to INCLUDE (relative to SOURCE_DIR) ---
INCLUDE_DIRS = [
    "realize_core",
    "realize_api",
    "realize_lite",
    "templates",
    "tests",
    "docs",
    ".github",
]

# --- Top-level files to INCLUDE ---
INCLUDE_FILES = [
    "cli.py",
    "Dockerfile",
    "docker-compose.yml",
    "requirements.txt",
    "pyproject.toml",
    ".env.example",
    "setup.yaml.example",
    "setup-guide.md",
    "README.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    ".gitignore",
]

# --- Patterns to EXCLUDE (anywhere in the path) ---
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".obsidian",
    ".pyc",
]

# --- Specific top-level items to EXCLUDE ---
EXCLUDE_TOP_LEVEL = {
    ".env",
    "realize-os.yaml",
    "setup.yaml",
    "shared",
    "systems",
    ".credentials",
    "data",
    ".claude",
    "kb_index.db",
    "fix_lint.py",
    "AGENTS.md",
    "WEBSITE-CHANGES-PROMPT.md",
    "create_release_zip.py",
    "pytest_report.txt",
    "ruff_out.txt",
    "ruff_report.txt",
    "test_output.txt",
    ZIP_NAME,
}


def should_exclude(rel_path: str) -> bool:
    """Check if a relative path should be excluded."""
    for pattern in EXCLUDE_PATTERNS:
        if pattern in rel_path:
            return True
    return False


def collect_files() -> list[tuple[Path, str]]:
    """Collect all files to include in the ZIP.

    Returns list of (absolute_path, archive_name) tuples.
    """
    files = []

    # Top-level files
    for filename in INCLUDE_FILES:
        filepath = SOURCE_DIR / filename
        if filepath.exists():
            files.append((filepath, f"{PREFIX}/{filename}"))

    # Directories
    for dirname in INCLUDE_DIRS:
        dirpath = SOURCE_DIR / dirname
        if not dirpath.exists():
            print(f"  Warning: directory '{dirname}' not found, skipping")
            continue
        for root, dirs, filenames in os.walk(dirpath):
            # Filter out excluded directories in-place
            dirs[:] = [d for d in dirs if not should_exclude(d)]
            for fname in filenames:
                abs_path = Path(root) / fname
                rel_path = abs_path.relative_to(SOURCE_DIR).as_posix()
                if not should_exclude(rel_path):
                    files.append((abs_path, f"{PREFIX}/{rel_path}"))

    return files


def main():
    print(f"Creating distribution package: {ZIP_NAME}")
    print(f"Source: {SOURCE_DIR}")
    print()

    files = collect_files()

    with zipfile.ZipFile(OUTPUT_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for abs_path, archive_name in sorted(files, key=lambda x: x[1]):
            zf.write(abs_path, archive_name)

    print(f"Package created: {OUTPUT_PATH}")
    print(f"Total files: {len(files)}")
    print(f"Size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
