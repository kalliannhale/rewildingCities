"""
canopy/orchestrator/semantic_types.py

Data-driven semantic type registry.
Loads vocabulary from seeds/schemas/semantic_types.yml
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class SemanticType:
    """A semantic type definition."""
    name: str
    category: str  # "vector", "raster", "tabular"
    format: str    # "geojson", "tif", "parquet"
    description: str
    extra: dict = field(default_factory=dict)  # typical_units, value_range, etc.


class SemanticTypeRegistry:
    """
    Registry of semantic types loaded from YAML.
    
    Example:
        registry = SemanticTypeRegistry("seeds/schemas/semantic_types.yml")
        
        fmt = registry.get_format("park_boundaries")  # "geojson"
        cat = registry.get_category("land_surface_temperature")  # "raster"
        
        if not registry.is_valid("made_up_type"):
            print("Unknown type!")
    """
    
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._types: dict[str, SemanticType] = {}
        self._load()
    
    def _load(self) -> None:
        """Load types from YAML file."""
        if not self.path.exists():
            raise FileNotFoundError(
                f"Semantic types file not found: {self.path}\n"
                f"Expected at: seeds/schemas/semantic_types.yml"
            )
        
        with open(self.path, 'r') as f:
            data = yaml.safe_load(f)
        
        for name, type_data in data.get("types", {}).items():
            # Extract known fields
            category = type_data.get("category")
            fmt = type_data.get("format")
            description = type_data.get("description", "")
            
            if not category:
                raise ValueError(
                    f"Semantic type '{name}' missing required field 'category'"
                )
            if not fmt:
                raise ValueError(
                    f"Semantic type '{name}' missing required field 'format'"
                )
            
            # Everything else goes in extra
            extra = {
                k: v for k, v in type_data.items()
                if k not in ("category", "format", "description")
            }
            
            self._types[name] = SemanticType(
                name=name,
                category=category,
                format=fmt,
                description=description,
                extra=extra
            )
    
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
    
    def is_valid(self, name: str) -> bool:
        """Check if a semantic type exists."""
        return name in self._types
    
    def all_types(self) -> list[str]:
        """Return all registered type names."""
        return sorted(self._types.keys())
    
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