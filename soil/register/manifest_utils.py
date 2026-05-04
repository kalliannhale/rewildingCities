"""
soil/register/manifest_utils.py

Shared utilities for manifest management across acquisition scripts.
"""

import re
import logging
from pathlib import Path

logger = logging.getLogger("manifest_utils")


def set_available(manifest_path, dataset_name, available: bool):
    """
    Update a single dataset's 'available' field in the manifest.

    Uses targeted regex replacement — only touches the 'available'
    line within the named dataset block. Does not rewrite or
    reformat any other part of the manifest.
    """
    manifest_path = Path(manifest_path)

    with open(manifest_path) as f:
        text = f.read()

    pattern = f"(  {dataset_name}:.*?)(available: (?:true|false))"
    replacement = rf"\1available: {str(available).lower()}"
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)

    if count > 0:
        with open(manifest_path, "w") as f:
            f.write(new_text)
        logger.debug(f"  Set {dataset_name} available: {available}")
        return True
    else:
        logger.warning(f"  Could not find 'available' field for {dataset_name}")
        return False


def set_multiple_available(manifest_path, updates: dict):
    """
    Update multiple datasets' 'available' fields in one write.

    Args:
        manifest_path: path to manifest YAML
        updates: dict of {dataset_name: bool}
    """
    manifest_path = Path(manifest_path)

    with open(manifest_path) as f:
        text = f.read()

    changed = 0
    for dataset_name, available in updates.items():
        pattern = f"(  {dataset_name}:.*?)(available: (?:true|false))"
        replacement = rf"\1available: {str(available).lower()}"
        text, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
        if count > 0:
            changed += 1

    if changed > 0:
        with open(manifest_path, "w") as f:
            f.write(text)

    return changed
