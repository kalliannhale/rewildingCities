"""
canopy/manifest/surgeon.py

Surgical regex-based YAML editing. Never reformats the document.

The manifest is a carefully authored YAML file with comments, 
intentional formatting, and human-readable structure. We NEVER 
run it through yaml.dump(). Instead, we use targeted regex 
replacements that touch only the specific field being changed.

If a field doesn't exist yet, the surgeon inserts it at the 
correct indent level within the dataset block.

Atomic writes via temp file + os.rename ensure the manifest
is never half-written.
"""

import os
import re
import tempfile
import logging
from pathlib import Path
from datetime import datetime, timezone

import yaml

logger = logging.getLogger("manifest.surgeon")


class ManifestSurgeon:
    """Surgical YAML editing for manifest files.
    
    Uses regex to modify specific fields within dataset blocks
    without touching anything else in the document. Can both 
    replace existing fields and insert new ones.
    
    Writes are atomic (temp file + rename).
    """
    
    # Fields that live inside the cache: sub-block
    CACHE_SUBFIELDS = {"fetched_at", "refresh_policy", "max_age_days", "path"}
    
    def __init__(self, manifest_path: Path):
        self.manifest_path = Path(manifest_path)
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
    
    def read(self) -> str:
        """Read the manifest file content as a string."""
        with open(self.manifest_path, 'r') as f:
            return f.read()
    
    def _find_dataset_block_end(self, text: str, dataset_name: str) -> tuple[int, int] | None:
        """Find the start of a dataset header and end of its block.
        
        Returns (header_start, block_end) character positions, or None.
        """
        pattern = rf'^  {re.escape(dataset_name)}:\s*$'
        match = re.search(pattern, text, re.MULTILINE)
        if not match:
            return None
        
        start = match.start()
        
        # Block ends at next 2-space-indented key or end of file
        rest = text[match.end():]
        end_match = re.search(r'^  [a-zA-Z_]', rest, re.MULTILINE)
        end = match.end() + end_match.start() if end_match else len(text)
        
        return start, end
    
    def _find_subblock_end(self, block_text: str, parent_field: str) -> tuple[int, int] | None:
        """Find a sub-block (like 'cache:') end within a dataset block."""
        pattern = rf'^    {re.escape(parent_field)}:\s*$'
        match = re.search(pattern, block_text, re.MULTILINE)
        if not match:
            return None
        
        start = match.start()
        rest = block_text[match.end():]
        end_match = re.search(r'^    [a-zA-Z_]', rest, re.MULTILINE)
        end = match.end() + end_match.start() if end_match else len(block_text)
        
        return start, end
    
    def set_field(
        self, 
        text: str, 
        dataset_name: str, 
        field_name: str, 
        value: str
    ) -> tuple[str, bool]:
        """Set a field value within a dataset block.
        
        If the field exists, replaces its value. If not, inserts it 
        at the correct indent level. Handles sub-fields (like fetched_at 
        inside cache:) automatically.
            
        Args:
            text: Current manifest content
            dataset_name: Dataset to modify
            field_name: Field to set
            value: New value as string
            
        Returns:
            Tuple of (modified_text, success_bool)
        """
        # Check dataset exists
        block_range = self._find_dataset_block_end(text, dataset_name)
        if block_range is None:
            logger.warning(f"Dataset '{dataset_name}' not found in manifest")
            return text, False
        
        # Try direct replacement first (field already exists)
        pattern = rf"(  {re.escape(dataset_name)}:.*?)({re.escape(field_name)}: )(.*?)(\n)"
        new_text, count = re.subn(
            pattern, rf"\g<1>\g<2>{value}\4", text, count=1, flags=re.DOTALL
        )
        if count > 0:
            return new_text, True
        
        # Field doesn't exist — insert it
        block_start, block_end = block_range
        block_text = text[block_start:block_end]
        
        if field_name in self.CACHE_SUBFIELDS:
            # Insert inside cache: sub-block
            sub_range = self._find_subblock_end(block_text, "cache")
            if sub_range is None:
                logger.info(
                    f"Inserting '{field_name}' for '{dataset_name}': "
                    f"no 'cache:' block found, creating field at dataset level instead"
                )
                # Fall through to top-level insert
            else:
                insert_pos = block_start + sub_range[1]
                insert_line = f"      {field_name}: {value}\n"
                new_text = text[:insert_pos] + insert_line + text[insert_pos:]
                logger.debug(
                    f"Inserted {dataset_name}/cache/{field_name} = {value}"
                )
                return new_text, True
        
        # Insert as top-level field in dataset block (4-space indent)
        # Place after the 'available:' line if it exists, otherwise after header
        avail_match = re.search(r'    available: .*?\n', block_text)
        if avail_match:
            insert_pos = block_start + avail_match.end()
        else:
            first_newline = block_text.find('\n')
            insert_pos = block_start + first_newline + 1 if first_newline != -1 else block_end
        
        insert_line = f"    {field_name}: {value}\n"
        new_text = text[:insert_pos] + insert_line + text[insert_pos:]
        logger.debug(f"Inserted {dataset_name}/{field_name} = {value}")
        return new_text, True
    
    def set_available(
        self, 
        text: str, 
        dataset_name: str, 
        available: bool
    ) -> tuple[str, bool]:
        """Set a dataset's available flag."""
        return self.set_field(text, dataset_name, "available", str(available).lower())
    
    def set_cache_timestamp(
        self,
        text: str,
        dataset_name: str,
        timestamp: str | None = None
    ) -> tuple[str, bool]:
        """Update or insert a dataset's fetched_at timestamp."""
        if timestamp is None:
            timestamp = f"'{datetime.now(timezone.utc).isoformat()}'"
        return self.set_field(text, dataset_name, "fetched_at", timestamp)
    
    def write_atomic(self, text: str) -> None:
        """Write manifest content atomically via temp file + rename."""
        dir_path = self.manifest_path.parent
        fd, tmp_path = tempfile.mkstemp(
            dir=dir_path, 
            prefix=".manifest_", 
            suffix=".tmp"
        )
        
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(text)
            os.rename(tmp_path, self.manifest_path)
            logger.debug(f"Manifest written atomically: {self.manifest_path}")
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    
    def append_changelog(self, entry: dict) -> None:
        """Append an entry to the manifest changelog."""
        changelog_path = self.manifest_path.parent / ".manifest_changelog.yml"
        
        existing = []
        if changelog_path.exists():
            with open(changelog_path, 'r') as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, list):
                    existing = loaded
        
        existing.append(entry)
        
        with open(changelog_path, 'w') as f:
            yaml.dump(existing, f, default_flow_style=False, sort_keys=False)
        
        logger.debug(f"Changelog appended: {changelog_path}")