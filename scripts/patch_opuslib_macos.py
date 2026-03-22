#!/usr/bin/env python3
"""Patch opuslib to find Homebrew libopus on macOS.

This script adds fallback paths for Homebrew libopus to opuslib's __init__.py,
allowing it to work on macOS without manual library path configuration.

Usage:
    python scripts/patch_opuslib_macos.py
"""

import sys
from pathlib import Path


def find_opuslib_init() -> Path | None:
    """Locate opuslib/api/__init__.py in the current venv."""
    try:
        import opuslib
        package_path = Path(opuslib.__file__).parent
        init_file = package_path / "api" / "__init__.py"
        return init_file if init_file.exists() else None
    except ImportError:
        return None


def is_already_patched(content: str) -> bool:
    """Check if the file is already patched."""
    return "Fallback for macOS Homebrew" in content


def apply_patch(init_file: Path) -> bool:
    """Apply the Homebrew fallback patch to opuslib/api/__init__.py."""
    content = init_file.read_text()
    
    if is_already_patched(content):
        print(f"✓ {init_file} is already patched")
        return True
    
    # Find the target line
    target = "lib_location = find_library('opus')"
    if target not in content:
        print(f"✗ Could not find target line in {init_file}")
        return False
    
    # Prepare the patch
    patch = '''lib_location = find_library('opus')

# Fallback for macOS Homebrew
if lib_location is None:
    import os
    homebrew_paths = ['/opt/homebrew/lib/libopus.dylib', '/usr/local/lib/libopus.dylib']
    for path in homebrew_paths:
        if os.path.exists(path):
            lib_location = path
            break
'''
    
    # Apply the patch
    patched = content.replace(target, patch)
    
    # Backup original
    backup = init_file.with_suffix(".py.bak")
    backup.write_text(content)
    
    # Write patched version
    init_file.write_text(patched)
    
    print(f"✓ Patched {init_file}")
    print(f"✓ Backup saved to {backup}")
    return True


def verify_patch() -> bool:
    """Verify that opuslib can now import successfully."""
    try:
        print("✓ opuslib imports successfully")
        return True
    except Exception as e:
        print(f"✗ opuslib import failed: {e}")
        return False


def main() -> int:
    print("macOS opuslib patcher")
    print("=" * 50)
    
    # Check platform
    if sys.platform != "darwin":
        print("⚠ This patch is only needed on macOS")
        return 0
    
    # Find opuslib
    init_file = find_opuslib_init()
    if not init_file:
        print("✗ Could not find opuslib installation")
        print("  Install it with: uv pip install opuslib")
        return 1
    
    print(f"Found opuslib at: {init_file.parent.parent}")
    
    # Apply patch
    if not apply_patch(init_file):
        return 1
    
    # Verify
    if not verify_patch():
        print("\n⚠ Patch applied but opuslib still fails to import")
        print("  Make sure Homebrew opus is installed: brew install opus")
        return 1
    
    print("\n✓ All done! TX audio transcoding should now work.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
