"""
canopy/orchestrator/semantic_types.py

Data-driven semantic type registry.

Loads the BASE vocabulary from seeds/schemas/semantic_types.yml, then merges any
per-domain MODULE vocabularies from seeds/schemas/modules/*.yml on top of it.

Every type carries a `module` field naming its origin ("base", or the module
filename stem such as "thermal"). Names are flat and global: a name declared in
two files is a loud collision error, never a silent overwrite. The origin stays
visible; the names stay legible; conflicts are loud.
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class SemanticType:
    """A semantic type definition."""
    name: str
    category: str            # "vector", "raster", "tabular", "image"
    format: str              # "geojson", "tiff", "parquet", "joblib", ...
    description: str
    module: str = "base"     # origin: "base" or a module stem ("thermal", "perception", ...)
    extra: dict = field(default_factory=dict)  # typical_units, value_range, resolution_tier, ...


class SemanticTypeRegistry:
    """
    Registry of semantic types loaded from YAML (base + modules).

    Example:
        registry = SemanticTypeRegistry("seeds/schemas/semantic_types.yml")

        registry.get_format("park_boundaries")        # "geojson"
        registry.get_category("land_surface_temperature")  # "raster"
        registry.get_module("cooling_differential")   # "thermal"
        registry.by_module("information")             # ["access_infrastructure", ...]

        if not registry.is_valid("made_up_type"):
            print("Unknown type!")
    """

    MODULES_DIRNAME = "modules"

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._types: dict[str, SemanticType] = {}
        self._source: dict[str, str] = {}   # name -> source label, for collision reports
        self._load()

    def _load(self) -> None:
        """Load the base file, then merge every modules/*.yml on top."""
        if not self.path.exists():
            raise FileNotFoundError(
                f"Semantic types file not found: {self.path}\n"
                f"Expected at: seeds/schemas/semantic_types.yml"
            )

        # 1) base vocabulary
        self._ingest_file(self.path, module="base")

        # 2) module vocabularies (optional): seeds/schemas/modules/*.yml
        #    Absent directory is fine — the registry is simply base-only.
        modules_dir = self.path.parent / self.MODULES_DIRNAME
        if modules_dir.is_dir():
            for module_path in sorted(modules_dir.glob("*.yml")):
                self._ingest_file(module_path, module=module_path.stem)

    def _ingest_file(self, path: Path, module: str) -> None:
        """
        Load one YAML file's `types` block, stamping `module` and refusing any
        name that already exists (a loud collision, never a silent overwrite).
        """
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        source = "base" if module == "base" else f"{self.MODULES_DIRNAME}/{path.name}"

        for name, type_data in (data.get("types") or {}).items():
            category = type_data.get("category")
            fmt = type_data.get("format")
            description = type_data.get("description", "")

            if not category:
                raise ValueError(
                    f"Semantic type '{name}' ({source}) missing required field 'category'"
                )
            if not fmt:
                raise ValueError(
                    f"Semantic type '{name}' ({source}) missing required field 'format'"
                )

            if name in self._types:
                raise ValueError(
                    f"Semantic type name collision: '{name}' is declared in both "
                    f"'{self._source[name]}' and '{source}'. Names are flat and "
                    f"global across base + modules; rename one of them."
                )

            # `module` is authoritative from the filename, never read from the
            # file body; everything unrecognized goes in extra.
            extra = {
                k: v for k, v in type_data.items()
                if k not in ("category", "format", "description", "module")
            }

            self._types[name] = SemanticType(
                name=name,
                category=category,
                format=fmt,
                description=description,
                module=module,
                extra=extra,
            )
            self._source[name] = source

    def get(self, name: str) -> SemanticType:
        """
        Get a semantic type by name.

        Raises:
            KeyError: If type not found (with suggestions)
        """
        if name in self._types:
            return self._types[name]

        # Not found — provide helpful error
        suggestions = self._find_similar(name)
        msg = f"Unknown semantic type: '{name}'"
        if suggestions:
            msg += f"\n  Did you mean: {', '.join(suggestions)}?"
        msg += f"\n  Valid types: {', '.join(sorted(self._types.keys()))}"

        raise KeyError(msg)

    def get_format(self, name: str) -> str:
        """Get the file format for a semantic type."""
        return self.get(name).format

    def get_category(self, name: str) -> str:
        """Get the data category for a semantic type."""
        return self.get(name).category

    def get_module(self, name: str) -> str:
        """Get the origin module of a semantic type ('base' or a module stem)."""
        return self.get(name).module

    def is_valid(self, name: str) -> bool:
        """Check if a semantic type exists."""
        return name in self._types

    def all_types(self) -> list[str]:
        """Return all registered type names."""
        return sorted(self._types.keys())

    def modules(self) -> list[str]:
        """Return the distinct modules present, with 'base' first."""
        mods = sorted({t.module for t in self._types.values()})
        if "base" in mods:
            mods.remove("base")
            mods = ["base"] + mods
        return mods

    def by_module(self, module: str) -> list[str]:
        """Return the type names that belong to a given module."""
        return sorted(n for n, t in self._types.items() if t.module == module)

    def _find_similar(self, name: str, max_distance: int = 2) -> list[str]:
        """Find similar type names using Levenshtein distance."""
        similar = []
        for known in self._types.keys():
            distance = self._levenshtein(name.lower(), known.lower())
            if distance <= max_distance:
                similar.append(known)
        return similar

    @staticmethod
    def _levenshtein(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return SemanticTypeRegistry._levenshtein(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]