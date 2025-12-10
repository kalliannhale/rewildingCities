# === Registry Lookup ===
# canopy/orchestrator/registry.py

class RegistryManager:
    """
    Manages primitive registries across layers.
    
    Resolves primitive references like "soil/validate_boundaries" 
    to full paths like "soil/validate/validate_boundaries.R"
    """
    
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
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
            primitive_ref: Reference like "soil/validate_boundaries" or "roots/generate_buffers"
            validate_exists: If True, verify the .R file exists on disk
        
        Returns:
            Tuple of (full_path, PrimitiveSpec)
            e.g., ("soil/validate/validate_boundaries.R", PrimitiveSpec(...))
        
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