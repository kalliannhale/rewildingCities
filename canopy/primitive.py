"""
canopy/primitive.py

Handles invocation of R primitives and response parsing.
"""

import subprocess
import json
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Any


@dataclass
class PrimitiveInput:
    """A named input to a primitive."""
    name: str
    path: str
    semantic_type: str


@dataclass
class PrimitiveResult:
    """Result from a primitive invocation."""
    success: bool
    output_path: str | None
    metadata: dict[str, Any]
    warnings: list[dict[str, str]]
    error: str | None = None
    message: str | None = None
    duration_seconds: float | None = None


class PrimitiveRunner:
    """
    Invokes R primitives via subprocess and captures results.
    
    Example:
        runner = PrimitiveRunner(primitives_dir="roots")
        result = runner.run(
            primitive="geometry/generate_buffers",
            inputs=[PrimitiveInput("parks", "plots/nyc/.data/parks.geojson", "park_boundaries")],
            output_path="plots/nyc/.data/park_buffers.geojson",
            params={"distances": [30, 60, 90]}
        )
    """
    
    def __init__(self, primitives_dir: str | Path = "roots", project_root: str | Path | None = None):
        self.primitives_dir = Path(primitives_dir)
        self.project_root = Path(project_root) if project_root else Path.cwd()
    
    def run(
        self,
        primitive: str,
        inputs: list[PrimitiveInput],
        output_path: str | Path,
        params: dict[str, Any] | None = None
    ) -> PrimitiveResult:
        """
        Run an R primitive.
        
        Args:
            primitive: Path to primitive relative to primitives_dir 
                       (e.g., "geometry/generate_buffers")
            inputs: List of PrimitiveInput objects
            output_path: Where the primitive should write its output
            params: Parameters to pass to the primitive
        
        Returns:
            PrimitiveResult with success status, metadata, and warnings
        """
        
        # Resolve primitive path
        primitive_path = self._resolve_primitive_path(primitive)
        
        # Prepare arguments
        inputs_dict = {inp.name: inp.path for inp in inputs}
        params = params or {}
        
        # Create temp files for JSON arguments
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as inputs_file:
            json.dump(inputs_dict, inputs_file)
            inputs_json_path = inputs_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as params_file:
            json.dump(params, params_file)
            params_json_path = params_file.name
        
        try:
            # Invoke R
            result = subprocess.run(
                [
                    "Rscript",
                    str(primitive_path),
                    inputs_json_path,
                    str(output_path),
                    params_json_path
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            # Parse response
            return self._parse_response(result, output_path)
            
        finally:
            # Clean up temp files
            Path(inputs_json_path).unlink(missing_ok=True)
            Path(params_json_path).unlink(missing_ok=True)
    
    def _resolve_primitive_path(self, primitive: str) -> Path:
        """Resolve primitive name to full path."""
        
        # Add .R extension if not present
        if not primitive.endswith('.R'):
            primitive = f"{primitive}.R"
        
        # primitive already includes layer (e.g., "soil/validate/validate_vector.R")
        # so we resolve from project_root, not primitives_dir
        path = self.project_root / primitive
        
        if not path.exists():
            raise FileNotFoundError(f"Primitive not found: {path}")
        
        return path
    
    def _parse_response(
        self, 
        result: subprocess.CompletedProcess,
        output_path: str | Path
    ) -> PrimitiveResult:
        """Parse subprocess result into PrimitiveResult."""
        
        # Try to parse stdout as JSON
        try:
            response = json.loads(result.stdout) if result.stdout.strip() else {}
        except json.JSONDecodeError:
            # If stdout isn't valid JSON, treat as failure
            return PrimitiveResult(
                success=False,
                output_path=None,
                metadata={},
                warnings=[],
                error="Invalid response",
                message=f"Primitive returned non-JSON output: {result.stdout[:500]}"
            )
        
        # Check exit code
        if result.returncode != 0:
            return PrimitiveResult(
                success=False,
                output_path=None,
                metadata={},
                warnings=response.get("warnings", []),
                error=response.get("error", "Unknown error"),
                message=response.get("message", result.stderr or "Primitive failed")
            )
        
        # Success
        return PrimitiveResult(
            success=True,
            output_path=str(output_path),
            metadata=response,
            warnings=response.get("warnings", [])
        )


def run_primitive(
    primitive: str,
    inputs: list[PrimitiveInput],
    output_path: str | Path,
    params: dict[str, Any] | None = None,
    primitives_dir: str | Path = "roots"
) -> PrimitiveResult:
    """
    Convenience function to run a primitive.
    
    Example:
        result = run_primitive(
            "geometry/generate_buffers",
            inputs=[PrimitiveInput("parks", "data/parks.geojson", "park_boundaries")],
            output_path="data/buffers.geojson",
            params={"distances": [30, 60, 90]}
        )
        
        if result.success:
            print(f"Created {result.metadata['feature_count']} features")
        else:
            print(f"Failed: {result.error}")
    """
    runner = PrimitiveRunner(primitives_dir=primitives_dir)
    return runner.run(primitive, inputs, output_path, params)
