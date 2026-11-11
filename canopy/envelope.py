"""
canopy/envelope.py

Envelope construction, reading, writing, and validation.
"""

import json
import re
import time
import hashlib
import warnings as python_warnings
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone

import jsonschema

from .primitive import PrimitiveRunner, PrimitiveInput, PrimitiveResult


# === Exceptions ===

class EnvelopeValidationError(Exception):
    """Raised when envelope validation fails on write."""
    pass


# === Data Structures ===

@dataclass
class HashInfo:
    """Hash information for an input."""
    value: str | None
    method: str  # "full_file", "metadata", "skipped"
    algorithm: str | None = None
    reason: str | None = None


@dataclass 
class InputRecord:
    """Record of an input for provenance."""
    name: str
    semantic_type: str
    path: str
    hash: HashInfo


@dataclass
class ProvenanceEntry:
    """A single entry in the provenance chain."""
    primitive: str
    version: str
    timestamp: str
    params: dict[str, Any]
    inputs: list[InputRecord]
    duration_seconds: float
    lineage_branch: str | None = None
    # Contract 1, rule 11 (D-143): what this step changed about what could
    # leave, one record per change. the primitive says step, detail and count;
    # the builder stamps by and at from this entry, so a record always names
    # the step that made it. inherited with the entry, so it reaches every
    # descendant; empty when the step changed nothing.
    publication: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Warning:
    """A warning from the pipeline."""
    level: str  # "info", "warning", "critical"
    primitive: str
    message: str


@dataclass
class Envelope:
    """The complete envelope contract."""
    data: dict[str, Any]
    metadata: dict[str, Any]
    provenance: list[ProvenanceEntry]
    warnings: list[Warning]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "data": self.data,
            "metadata": self.metadata,
            "provenance": [
                {
                    "primitive": p.primitive,
                    "version": p.version,
                    "timestamp": p.timestamp,
                    "params": p.params,
                    "inputs": [
                        {
                            "name": i.name,
                            "semantic_type": i.semantic_type,
                            "path": i.path,
                            "hash": {
                                k: v for k, v in {
                                    "value": i.hash.value,
                                    "method": i.hash.method,
                                    "algorithm": i.hash.algorithm,
                                    "reason": i.hash.reason
                                }.items() if v is not None
                            }
                        }
                        for i in p.inputs
                    ],
                    "duration_seconds": p.duration_seconds,
                    "lineage_branch": p.lineage_branch,
                    "publication": [dict(r) for r in p.publication]
                }
                for p in self.provenance
            ],
            "warnings": [
                {
                    "level": w.level,
                    "primitive": w.primitive,
                    "message": w.message
                }
                for w in self.warnings
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Envelope":
        """Create Envelope from dictionary."""
        return cls(
            data=data["data"],
            metadata=data["metadata"],
            provenance=[
                ProvenanceEntry(
                    primitive=p["primitive"],
                    version=p["version"],
                    timestamp=p["timestamp"],
                    params=p["params"],
                    inputs=[
                        InputRecord(
                            name=i["name"],
                            semantic_type=i["semantic_type"],
                            path=i["path"],
                            hash=HashInfo(
                                value=i["hash"]["value"],
                                method=i["hash"]["method"],
                                algorithm=i["hash"].get("algorithm"),
                                reason=i["hash"].get("reason")
                            )
                        )
                        for i in p["inputs"]
                    ],
                    duration_seconds=p["duration_seconds"],
                    lineage_branch=p.get("lineage_branch"),
                    # a receipt written before D-143 has no records: none
                    publication=[dict(r) for r in p.get("publication") or []]
                )
                for p in data["provenance"]
            ],
            warnings=[
                Warning(
                    level=w["level"],
                    primitive=w["primitive"],
                    message=w["message"]
                )
                for w in data["warnings"]
            ]
        )


# === Schema Validation ===

_schema_cache: dict[str, dict] = {}


def _load_schema(schema_path: Path) -> dict:
    """Load a JSON schema, with caching."""
    cache_key = str(schema_path)
    
    if cache_key not in _schema_cache:
        with open(schema_path, 'r') as f:
            _schema_cache[cache_key] = json.load(f)
    
    return _schema_cache[cache_key]


def _get_schema_dir(project_root: Path | None = None) -> Path:
    """Get the schemas directory."""
    if project_root is None:
        # Walk up from this file to find project root
        current = Path(__file__).parent
        while current != current.parent:
            if (current / "seeds" / "schemas").exists():
                return current / "seeds" / "schemas"
            current = current.parent
        raise FileNotFoundError(
            "Could not find seeds/schemas directory. "
            "Provide project_root explicitly."
        )
    return project_root / "seeds" / "schemas"


def validate_envelope(
    envelope_data: dict,
    project_root: Path | None = None
) -> list[str]:
    """
    Validate envelope data against the JSON schema.
    
    Args:
        envelope_data: Envelope as dictionary
        project_root: Project root (to find schemas)
    
    Returns:
        List of validation error messages (empty if valid)
    """
    schema_dir = _get_schema_dir(project_root)
    schema_path = schema_dir / "envelope.schema.json"
    
    if not schema_path.exists():
        return [f"Schema file not found: {schema_path}"]
    
    schema = _load_schema(schema_path)
    
    # Build a registry with all referenced schemas
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
    
    def load_resource(uri: str) -> Resource:
        """Load a schema by URI."""
        # Extract filename from URI
        filename = uri.split("/")[-1]
        path = schema_dir / filename
        
        if not path.exists():
            raise FileNotFoundError(f"Referenced schema not found: {path}")
        
        with open(path, 'r') as f:
            contents = json.load(f)
        
        return Resource.from_contents(contents, default_specification=DRAFT202012)
    
    # Pre-load referenced schemas
    registry = Registry()
    for schema_file in [
        "provenance.schema.json",
        "warning.schema.json",
        "metadata.raster.schema.json",
        "metadata.vector.schema.json",
        "metadata.tabular.schema.json",
    ]:
        path = schema_dir / schema_file
        if path.exists():
            with open(path, 'r') as f:
                contents = json.load(f)
            resource = Resource.from_contents(contents, default_specification=DRAFT202012)
            # Register by the $id in the schema
            schema_id = contents.get("$id", schema_file)
            registry = registry.with_resource(schema_id, resource)
            # Also register by just the filename for relative refs
            registry = registry.with_resource(schema_file, resource)
    
    validator = jsonschema.Draft202012Validator(schema, registry=registry)
    
    errors = []
    for error in validator.iter_errors(envelope_data):
        path = " → ".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"{path}: {error.message}")
    
    return errors


# === Metadata Completeness Audit ===
#
# The per-category metadata schemas mark each field's tier ("expected" or
# "optional") as an annotation beside the field itself. Expected fields a
# primitive did not emit are NOT errors (a thin primitive is allowed), but they
# are not silent either: the builder emits a schema-legal Warning naming each
# absent expected field, so the omission travels in the envelope.
#
# Presence is the "no silent choices" concern handled here. Value-correctness
# (a malformed field that IS present) is a separate concern, caught as a hard
# validation error by the per-category $ref in envelope.schema.json.

_expected_cache: dict[str, list[str]] = {}


def expected_fields(data_category: str, project_root: Path | None = None) -> list[str]:
    """The expected (not merely optional) metadata fields for a category, read
    from the category schema's own `tier` annotations. The schema is the single
    source of truth; this never hardcodes a field list."""
    if data_category in _expected_cache:
        return _expected_cache[data_category]

    schema_dir = _get_schema_dir(project_root)
    schema_path = schema_dir / f"metadata.{data_category}.schema.json"
    if not schema_path.exists():
        _expected_cache[data_category] = []
        return []

    schema = _load_schema(schema_path)
    fields = [
        name for name, spec in (schema.get("properties") or {}).items()
        if isinstance(spec, dict) and spec.get("tier") == "expected"
    ]
    _expected_cache[data_category] = fields
    return fields


def completeness_warnings(
    metadata: dict,
    data_category: str,
    project_root: Path | None = None
) -> list["Warning"]:
    """One schema-legal Warning per expected metadata field the primitive did
    not emit. Absence is documented, never silently defaulted."""
    out: list[Warning] = []
    for field_name in expected_fields(data_category, project_root):
        if field_name not in metadata:
            out.append(Warning(
                level="warning",
                primitive="envelope",
                message=(
                    f"{data_category} metadata missing expected field "
                    f"'{field_name}'; it is not available for downstream steps "
                    f"to rely on."
                ),
            ))
    return out


# === Hashing ===

class Hasher:
    """Profile-aware file hashing."""
    
    def __init__(self, profile: str = "full"):
        """
        Args:
            profile: "full" (complete hash), "dev" (metadata only), "test" (skip)
        """
        self.profile = profile
    
    def hash_file(self, path: str | Path) -> HashInfo:
        """Hash a file according to profile settings."""
        path = Path(path)
        
        if self.profile == "test":
            return HashInfo(
                value=None,
                method="skipped",
                reason="test profile"
            )
        
        if self.profile == "dev":
            return self._metadata_hash(path)
        
        # Full profile - complete file hash
        return self._full_hash(path)
    
    def _full_hash(self, path: Path) -> HashInfo:
        """Compute full file hash."""
        hasher = hashlib.md5()
        
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        
        return HashInfo(
            value=hasher.hexdigest(),
            method="full_file",
            algorithm="md5"
        )
    
    def _metadata_hash(self, path: Path) -> HashInfo:
        """Compute metadata-based hash (fast)."""
        stat = path.stat()
        
        # Hash: size + modification time + first 1000 bytes
        hasher = hashlib.md5()
        hasher.update(str(stat.st_size).encode())
        hasher.update(str(stat.st_mtime).encode())
        
        with open(path, 'rb') as f:
            hasher.update(f.read(1000))
        
        return HashInfo(
            value=hasher.hexdigest(),
            method="metadata",
            algorithm="md5"
        )


# === Envelope I/O ===

def read_envelope(
    path: str | Path,
    validate: bool = True,
    project_root: Path | None = None
) -> Envelope:
    """
    Read an envelope from JSON file.
    
    Args:
        path: Path to envelope JSON file
        validate: Whether to validate against schema (warns if invalid)
        project_root: Project root for schema lookup
    
    Returns:
        Envelope object
    """
    path = Path(path)
    
    with open(path, 'r') as f:
        data = json.load(f)
    
    if validate:
        errors = validate_envelope(data, project_root)
        if errors:
            python_warnings.warn(
                f"Envelope at {path} has validation issues:\n" +
                "\n".join(f"  - {e}" for e in errors),
                stacklevel=2
            )
    
    return Envelope.from_dict(data)


def write_envelope(
    envelope: Envelope,
    path: str | Path,
    validate: bool = True,
    project_root: Path | None = None
) -> None:
    """
    Write an envelope to JSON file.
    
    Args:
        envelope: Envelope to write
        path: Output path
        validate: Whether to validate against schema (fails if invalid)
        project_root: Project root for schema lookup
    
    Raises:
        EnvelopeValidationError: If validation is enabled and envelope is invalid
    """
    path = Path(path)
    data = envelope.to_dict()
    
    if validate:
        errors = validate_envelope(data, project_root)
        if errors:
            raise EnvelopeValidationError(
                f"Envelope validation failed:\n" +
                "\n".join(f"  - {e}" for e in errors)
            )
    
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


# === Envelope Builder ===

@dataclass
class EnvelopeInput:
    """An input to the envelope builder - either an envelope or raw file."""
    name: str
    envelope: Envelope | None = None
    path: str | None = None
    semantic_type: str | None = None
    
    def __post_init__(self):
        if self.envelope is None and self.path is None:
            raise ValueError("Must provide either envelope or path")
        
        if self.envelope is None and self.semantic_type is None:
            raise ValueError("Raw inputs require semantic_type")


class EnvelopeBuilder:
    """
    Builds envelopes by invoking primitives with proper provenance tracking.
    
    Example:
        builder = EnvelopeBuilder(profile="dev")
        
        result = builder.run(
            primitive="geometry/generate_buffers",
            version="1.0.0",
            inputs=[
                EnvelopeInput(name="parks", path="data/parks.geojson", semantic_type="park_boundaries")
            ],
            output_path="data/buffers.geojson",
            params={"distances": [30, 60, 90]}
        )
        
        if result.success:
            envelope = result.envelope
            write_envelope(envelope, "data/buffers.envelope.json")
    """
    
    def __init__(
    self, 
    profile: str = "full",
    primitives_dir: str | Path = "roots",
    project_root: str | Path | None = None
):
        self.profile = profile
        if project_root:
            self.project_root = Path(project_root)
        else:
            # resolved from the installed package rather than the cwd, and
            # raising rather than guessing. a wrong root here means every
            # read lands somewhere unrelated with no error to show. C-04.
            from canopy.paths import project_root as _resolve_root
            self.project_root = _resolve_root()
        self.hasher = Hasher(profile=profile)
        self.runner = PrimitiveRunner(
            primitives_dir=primitives_dir,
            project_root=self.project_root
            )
    
    def run(
        self,
        primitive: str,
        version: str,
        inputs: list[EnvelopeInput],
        output_path: str | Path,
        output_format: str,
        output_semantic_type: str,
        output_data_category: str,
        params: dict[str, Any] | None = None,
        passthrough: bool = False
    ) -> "BuildResult":
        """
        Run a primitive and construct the output envelope.
        
        Args:
            primitive: Primitive path (e.g., "geometry/generate_buffers")
            version: Primitive version (e.g., "1.0.0")
            inputs: List of EnvelopeInput objects
            output_path: Where to write output data
            output_format: Output format (e.g., "geojson", "tiff")
            output_semantic_type: Semantic type of output
            output_data_category: "vector", "raster", or "tabular"
            params: Parameters for the primitive
        
        Returns:
            BuildResult with success status and envelope
        """
        params = params or {}
        
        # Prepare primitive inputs
        primitive_inputs = self._prepare_inputs(inputs)
        
        # Hash inputs
        input_records = self._hash_inputs(inputs, primitive_inputs)
        
        # Time the execution
        start_time = time.time()
        
        # Run primitive
        result = self.runner.run(
            primitive=primitive,
            inputs=primitive_inputs,
            output_path=output_path,
            params=params
        )
        
        duration = time.time() - start_time
        
        # Handle failure
        if not result.success:
            return BuildResult(
                success=False,
                envelope=None,
                error=result.error,
                message=result.message
            )
        
        # Rule 11 records the primitive printed (D-143). by and at are the
        # builder's to stamp; a primitive that writes either is refused, never
        # quietly corrected, because a record that misnames its step would
        # travel to every descendant.
        records, bad = self._publication_records(result.metadata)
        if bad:
            return BuildResult(
                success=False,
                envelope=None,
                error="Publication record not understood",
                message=bad
            )

        # Build provenance entry
        short_name = re.sub(r'\.(R|py)$', '', primitive.split('/')[-1])
        timestamp = datetime.now(timezone.utc).isoformat()
        provenance_entry = ProvenanceEntry(
            primitive=short_name,
            version=version,
            timestamp=timestamp,
            params=params,
            inputs=input_records,
            duration_seconds=round(duration, 3),
            lineage_branch=None,  # This is the creating primitive
            publication=[dict(r, by=short_name, at=timestamp) for r in records]
        )
        
        # Merge provenance from input envelopes
        merged_provenance = self._merge_provenance(inputs, provenance_entry)
        
        # Merge warnings from inputs and primitive
        merged_warnings = self._merge_warnings(inputs, result.warnings, primitive)
        
        # Build metadata, and collect any completeness warnings it raises
        metadata, completeness = self._build_metadata(
            result.metadata,
            output_semantic_type,
            output_data_category
        )
        merged_warnings.extend(completeness)
        
        # Determine final data path
        # For passthrough primitives, use the input path (no new file created)
        if passthrough and primitive_inputs:
            final_path = primitive_inputs[0].path
        else:
            final_path = str(output_path)
        
        # Construct envelope
        envelope = Envelope(
            data={
                "path": final_path,
                "format": output_format,
                "secondary": result.metadata.get("secondary", {})
            },
            metadata=metadata,
            provenance=merged_provenance,
            warnings=merged_warnings
        )
        
        return BuildResult(
            success=True,
            envelope=envelope,
            error=None,
            message=None
        )
    
    @staticmethod
    def _publication_records(primitive_metadata: dict) -> tuple[list[dict], str | None]:
        """the rule 11 records a primitive printed, or the reason they cannot
        be taken. the step names are checked by provenance.schema.json when
        the receipt is written, so this checks only what the schema cannot
        see: that the primitive left by and at to the builder."""
        records = primitive_metadata.get("publication")
        if records is None:
            return [], None
        if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
            return [], ("publication must be a list of records, each with step, "
                        "detail and count (Contract 1, section 8)")
        for r in records:
            stamped = [k for k in ("by", "at") if k in r]
            if stamped:
                return [], (f"the primitive stamped {', '.join(stamped)} on its own "
                            f"publication record ({r.get('step')}); by and at are "
                            f"written by the builder from the provenance entry (D-143)")
        return records, None

    def _prepare_inputs(self, inputs: list[EnvelopeInput]) -> list[PrimitiveInput]:
        """Convert EnvelopeInputs to PrimitiveInputs for the runner."""
        primitive_inputs = []
        
        for inp in inputs:
            if inp.envelope:
                path = inp.envelope.data["path"]
                semantic_type = inp.envelope.metadata["semantic_type"]
            else:
                path = inp.path
                semantic_type = inp.semantic_type
            
            primitive_inputs.append(PrimitiveInput(
                name=inp.name,
                path=path,
                semantic_type=semantic_type
            ))
        
        return primitive_inputs
    
    def _hash_inputs(
        self, 
        inputs: list[EnvelopeInput],
        primitive_inputs: list[PrimitiveInput]
    ) -> list[InputRecord]:
        """Hash all inputs and create input records."""
        records = []
        
        for inp, prim_inp in zip(inputs, primitive_inputs):
            hash_info = self.hasher.hash_file(prim_inp.path)
            
            records.append(InputRecord(
                name=prim_inp.name,
                semantic_type=prim_inp.semantic_type,
                path=prim_inp.path,
                hash=hash_info
            ))
        
        return records
    
    def _merge_provenance(
        self,
        inputs: list[EnvelopeInput],
        new_entry: ProvenanceEntry
    ) -> list[ProvenanceEntry]:
        """Merge provenance chains from all inputs, then append new entry."""
        merged = []
        
        for inp in inputs:
            if inp.envelope:
                # Tag inherited provenance with the input name
                for entry in inp.envelope.provenance:
                    tagged = ProvenanceEntry(
                        primitive=entry.primitive,
                        version=entry.version,
                        timestamp=entry.timestamp,
                        params=entry.params,
                        inputs=entry.inputs,
                        duration_seconds=entry.duration_seconds,
                        lineage_branch=inp.name if entry.lineage_branch is None else entry.lineage_branch,
                        publication=[dict(r) for r in entry.publication]
                    )
                    merged.append(tagged)
        
        # Add the new entry
        merged.append(new_entry)
        
        return merged
    
    def _merge_warnings(
        self,
        inputs: list[EnvelopeInput],
        primitive_warnings: list[dict],
        primitive_name: str
    ) -> list[Warning]:
        """Merge warnings from inputs and add new warnings from primitive."""
        merged = []
        
        # Inherit warnings from input envelopes
        for inp in inputs:
            if inp.envelope:
                merged.extend(inp.envelope.warnings)
        
        # Add warnings from this primitive
        primitive_short = re.sub(r'\.(R|py)$', '', primitive_name.split('/')[-1])
        for w in primitive_warnings:
            merged.append(Warning(
                level=w["level"],
                primitive=primitive_short,
                message=w["message"]
            ))
        
        return merged
    
    def _build_metadata(
        self,
        primitive_metadata: dict,
        semantic_type: str,
        data_category: str
    ) -> tuple[dict, list["Warning"]]:
        """Build envelope metadata from primitive output, and audit it for
        completeness. Returns (metadata, completeness_warnings). Expected fields
        the primitive did not emit become schema-legal Warnings; they do not
        block, but they are never silent."""
        
        # Start with what the primitive returned
        metadata = dict(primitive_metadata)
        
        # Remove warnings (they go in their own section)
        metadata.pop("warnings", None)
        metadata.pop("status", None)
        # Rule 11 records go in the provenance entry, never in metadata (D-143)
        metadata.pop("publication", None)
        
        # Add required fields
        metadata["semantic_type"] = semantic_type
        metadata["data_category"] = data_category
        
        # CRS should come from primitive metadata. Its absence is not audited
        # here as "missing expected": crs is required in envelope.schema.json,
        # so an absent crs is a hard validation error, not a soft warning.

        # Capacity to report both primary and secondary outputs
        secondary = primitive_metadata.get("secondary", {})
        if secondary:
            metadata["secondary"] = secondary
        
        # Audit completeness against the category's expected fields, read from
        # the schema's own tier annotations. No silent omissions.
        audit_warnings = completeness_warnings(
            metadata, data_category, self.project_root
        )
        
        return metadata, audit_warnings


@dataclass
class BuildResult:
    """Result of an envelope build operation."""
    success: bool
    envelope: Envelope | None
    error: str | None
    message: str | None


# === Convenience Function ===

def build_envelope(
    primitive: str,
    version: str,
    inputs: list[EnvelopeInput],
    output_path: str | Path,
    output_format: str,
    output_semantic_type: str,
    output_data_category: str,
    params: dict[str, Any] | None = None,
    profile: str = "full",
    primitives_dir: str | Path = "roots"
) -> BuildResult:
    """
    Convenience function to build an envelope.
    
    Example:
        result = build_envelope(
            primitive="geometry/generate_buffers",
            version="1.0.0",
            inputs=[EnvelopeInput(name="parks", path="data/parks.geojson", semantic_type="park_boundaries")],
            output_path="data/buffers.geojson",
            output_format="geojson",
            output_semantic_type="park_buffers",
            output_data_category="vector",
            params={"distances": [30, 60, 90]},
            profile="dev"
        )
    """
    builder = EnvelopeBuilder(profile=profile, primitives_dir=primitives_dir)
    return builder.run(
        primitive=primitive,
        version=version,
        inputs=inputs,
        output_path=output_path,
        output_format=output_format,
        output_semantic_type=output_semantic_type,
        output_data_category=output_data_category,
        params=params
    )