# === Update 1: parse_manifest in orchestrator.py ===
# Replace the dataset loading loop to include ALL datasets,
# not just available ones. Add 'available' to ManifestDataset.

# Update the ManifestDataset dataclass:

@dataclass
class ManifestDataset:
    """A dataset declared in a manifest."""
    name: str
    path: str
    semantic_type: str
    format: str
    available: bool = True


# Update parse_manifest's dataset loop:

def parse_manifest(path: str | Path) -> Manifest:
    """Parse a city manifest YAML file."""
    path = Path(path)
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    datasets = {}
    for name, ds_data in data.get("datasets", {}).items():
        cache_path = ds_data.get("cache", {}).get("path", f".data/{name}.geojson")
        datasets[name] = ManifestDataset(
            name=name,
            path=cache_path,
            semantic_type=ds_data.get("semantic_type", name),
            format=ds_data.get("format", "geojson"),
            available=ds_data.get("available", False)
        )
    
    return Manifest(
        city_name=data["city"]["name"],
        city_id=data["city"]["id"],
        datasets=datasets,
        data_dir=path.parent
    )


# === Update 2: _resolve_manifest_ref in references.py ===
# Check 'available' flag and file existence separately
# with clear error messages for each case.

def _resolve_manifest_ref(
    self, 
    dataset_name: str, 
    context: str = ""
) -> tuple[str, str, None]:
    """Resolve a reference to a manifest dataset."""
    context_msg = f" (in {context})" if context else ""
    
    if dataset_name not in self.manifest.datasets:
        available = ", ".join(sorted(self.manifest.datasets.keys())) or "(none)"
        raise ValueError(
            f"Manifest has no dataset '{dataset_name}'{context_msg}. "
            f"Available datasets in {self.manifest.city_id} manifest: {available}"
        )
    
    dataset = self.manifest.datasets[dataset_name]
    
    # Check available flag
    if not dataset.available:
        raise ValueError(
            f"Dataset '{dataset_name}' is not yet available{context_msg}. "
            f"Run acquisition scripts to fetch it:\n"
            f"  python -m soil.register.fetch_dataset plots/{self.manifest.city_id}/manifest.yml -v\n"
            f"  python -m soil.register.acquire_landsat plots/{self.manifest.city_id}/manifest.yml -v\n"
            f"  python -m soil.register.acquire_land_cover plots/{self.manifest.city_id}/manifest.yml -v\n"
            f"  python -m soil.register.acquire_gee plots/{self.manifest.city_id}/manifest.yml -v\n"
            f"Then run: python -m soil.register.verify_manifest plots/{self.manifest.city_id}/manifest.yml"
        )
    
    path = str(self.manifest.data_dir / dataset.path)
    
    # Check file exists on disk
    if not Path(path).exists():
        raise FileNotFoundError(
            f"Dataset '{dataset_name}' is marked available but file not found{context_msg}. "
            f"Expected path: {path}\n"
            f"Run: python -m soil.register.verify_manifest plots/{self.manifest.city_id}/manifest.yml\n"
            f"to update availability flags."
        )
    
    return path, dataset.semantic_type, None
