# === Registry Lookup ===
# canopy/orchestrator/registry.py

from __future__ import annotations
from pathlib import Path
import yaml
from dataclasses import dataclass, field

@dataclass
class PrimitiveSpec:
    """A primitive's specification from a registry."""
    name: str
    path: str  # relative path within layer
    version: str
    inputs: list[dict]
    outputs: dict
    params: dict
    passthrough: bool = False
    # declared per-primitive under `preconditions:`; normalized to a list of
    # single-key dicts, which is what check_preconditions() contracts for.
    # a YAML mapping cannot hold two predicates of the same kind, so a list
    # is the honest shape: `provenance_contains` twice is a legitimate ask.
    preconditions: list = field(default_factory=list)

def _normalize_preconditions(raw, primitive_name: str, layer: str) -> list:
    """
    Accept either shape a registry might declare and return the list form.

        preconditions:                  ->  [{"provenance_contains": "x"}]
          provenance_contains: x

        preconditions:                  ->  [{"provenance_contains": "x"},
          - provenance_contains: x           {"no_unresolved_critical": True}]
          - no_unresolved_critical: true

    A mapping is convenient but cannot express the same predicate twice, so
    the list is authoritative and a mapping is converted. An unusable shape
    raises rather than silently declaring no preconditions: a gate that
    quietly guards nothing is worse than no gate.
    """
    if not raw:
        return []
    if isinstance(raw, dict):
        return [{k: v} for k, v in raw.items()]
    if isinstance(raw, list):
        out = []
        for item in raw:
            if isinstance(item, dict):
                out.extend({k: v} for k, v in item.items())
            else:
                raise ValueError(
                    f"primitive '{primitive_name}' ({layer}/_registry.yml): each "
                    f"precondition must be a mapping like "
                    f"'- provenance_contains: validate_vector', got {item!r}")
        return out
    raise ValueError(
        f"primitive '{primitive_name}' ({layer}/_registry.yml): "
        f"`preconditions:` must be a mapping or a list of mappings, "
        f"got {type(raw).__name__}")


class UniqueKeyLoader(yaml.SafeLoader):
    """a SafeLoader that refuses a mapping key written twice (REG-5).

    plain YAML keeps the last of two equal keys and says nothing, so a
    registry could declare a primitive twice and silently run the second.
    this raises instead, naming the key and both lines. ~"""


def _construct_unique_mapping(loader, node, deep=False):
    seen: dict = {}
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise ValueError(
                f"duplicate key '{key}' in {getattr(loader, 'name', 'a registry')}: "
                f"first at line {seen[key] + 1}, again at line "
                f"{key_node.start_mark.line + 1}. YAML would keep the second "
                f"silently; declare it once (REG-5)")
        seen[key] = key_node.start_mark.line
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


def load_registry(layer: str, project_root: Path | None = None) -> dict[str, PrimitiveSpec]:
    """Load a layer's primitive registry."""
    # Path.cwd() was the old default and it only worked from a checkout;
    # canopy.paths resolves from the installed package and raises rather than
    # guessing. C-04.
    if project_root is None:
        from canopy.paths import project_root as _resolve_root
        project_root = _resolve_root()
    registry_path = project_root / layer / "_registry.yml"
    
    if not registry_path.exists():
        raise FileNotFoundError(f"Registry not found: {registry_path}")
    
    with open(registry_path, 'r') as f:
        data = yaml.load(f, Loader=UniqueKeyLoader)
    
    specs = {}
    for name, spec_data in data.get("primitives", {}).items():
        specs[name] = PrimitiveSpec(
            name=name,
            path=spec_data["path"],
            version=spec_data.get("version", "1.0.0"),
            inputs=spec_data.get("inputs", []),
            outputs=spec_data.get("outputs", {}),
            params=spec_data.get("params", {}),
            passthrough=spec_data.get("passthrough", False),
            preconditions=_normalize_preconditions(
                spec_data.get("preconditions"), name, layer)
        )
    
    return specs

class RegistryManager:
    """
    Manages primitive registries across layers.
    
    Resolves primitive references like "soil/repair_geometry"
    to full paths like "soil/repair/repair_geometry.R"
    """
    
    def __init__(self, project_root: Path | None = None):
        if project_root is None:
            # resolved from the installed package rather than the cwd, and
            # raising rather than guessing. a wrong root here means every
            # read lands somewhere unrelated with no error to show. C-04.
            from canopy.paths import project_root as _resolve_root
            project_root = _resolve_root()
        self.project_root = Path(project_root)
        self._registries: dict[str, dict[str, PrimitiveSpec]] = {}
    
    def _ensure_registry_loaded(self, layer: str) -> None:
        """Load a registry if not already cached."""
        if layer not in self._registries:
            self._registries[layer] = load_registry(layer, self.project_root)
    
    def resolve_primitive(
        self, 
        primitive_ref: str, 
        validate_exists: bool = True
    ) -> tuple[str, PrimitiveSpec]:
        """
        Resolve a primitive reference to its full path and spec.
        
        Args:
            primitive_ref: Reference like "soil/repair_geometry" or "roots/generate_buffers"
            validate_exists: If True, verify the primitive's file (.R or .py) exists on disk.
                This runs only when a step references the primitive, so a broken
                registry path stays silent until something uses it (REG-6).
        
        Returns:
            Tuple of (full_path, PrimitiveSpec)
            e.g., ("soil/repair/repair_geometry.R", PrimitiveSpec(...))
        
        Raises:
            ValueError: If layer or primitive not found
            FileNotFoundError: If validate_exists=True and file doesn't exist
        """
        # Parse the reference
        parts = primitive_ref.split("/", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid primitive reference: '{primitive_ref}'. "
                f"Expected format: 'layer/primitive_name' (e.g., 'roots/generate_buffers')"
            )
        
        layer, primitive_name = parts
        
        # Validate layer
        if layer not in ("roots", "soil"):
            raise ValueError(
                f"Unknown layer: '{layer}'. Must be 'roots' or 'soil'."
            )
        
        # Load registry and find primitive
        self._ensure_registry_loaded(layer)
        registry = self._registries[layer]
        
        if primitive_name not in registry:
            available = ", ".join(sorted(registry.keys()))
            raise ValueError(
                f"Primitive '{primitive_name}' not found in {layer}/_registry.yml. "
                f"Available: {available}"
            )
        
        spec = registry[primitive_name]
        
        # Construct full path
        full_path = f"{layer}/{spec.path}"
        
        # Validate file exists
        if validate_exists:
            absolute_path = self.project_root / full_path
            if not absolute_path.exists():
                raise FileNotFoundError(
                    f"Primitive file not found: {absolute_path}\n"
                    f"Registry entry '{primitive_name}' in {layer}/_registry.yml "
                    f"points to '{spec.path}', but file doesn't exist.\n"
                    f"Either create the file or update the registry."
                )
        
        return full_path, spec
    
    def get_spec(self, primitive_ref: str) -> PrimitiveSpec:
        """Get just the spec for a primitive reference."""
        _, spec = self.resolve_primitive(primitive_ref)
        return spec
    
    def get_path(self, primitive_ref: str) -> str:
        """Get just the full path for a primitive reference."""
        path, _ = self.resolve_primitive(primitive_ref)
        return path
    
    def validate_all_primitives(self, experiment: "Experiment") -> list[str]:
        """
        Validate all primitives referenced in an experiment exist.
        
        Returns list of errors (empty if all valid).
        """
        errors = []
        
        for step in experiment.steps:
            try:
                self.resolve_primitive(step.primitive, validate_exists=True)
            except (ValueError, FileNotFoundError) as e:
                errors.append(f"Step '{step.id}': {e}")
        
        return errors