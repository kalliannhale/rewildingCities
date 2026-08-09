"""
canopy/primitive.py

Handles invocation of R primitives and response parsing.

Sprint 8 patch (2026-05): _parse_response is now tolerant of stdout
pollution. The rewildr contract is that primitives emit exactly one
JSON object on stdout (via primitive_success / primitive_failure),
but some R packages — notably terra under conda — write progress bars
and other chatter to stdout that breaks the previous whole-stdout
json.loads() approach. The new parser tries the clean parse first,
then falls back to scanning for the last JSON object in stdout.
The rewildr contract has not changed; this patch makes the Python
side robust to imperfect compliance from upstream R libraries.
"""

import subprocess
import json
import tempfile
import re
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

    @staticmethod
    def _extract_trailing_json(stdout: str) -> dict | None:
        """Find the last valid JSON object in stdout, scanning from the end.

        rewildr emits the protocol response as the final stdout write of the
        primitive. Anything before it — terra progress bars, sf load messages,
        R warnings printed via message() — is chatter that should be ignored.

        Strategy: walk stdout in reverse looking for the start of a JSON object
        ('{'), and try to parse from each candidate start to the matching end.
        Returns the first successful parse (which, walking from the end, is
        the last JSON object emitted). Returns None if no parse succeeds.

        We scan line-by-line first because the rewildr contract typically
        emits JSON on its own line. If that fails (e.g. the JSON got
        line-wrapped by a progress callback), we fall back to a character-
        level scan.
        """
        if not stdout or not stdout.strip():
            return None

        # Strategy 1: scan lines from the end, each candidate is the line + everything after it.
        # Cheap and handles the common case where JSON is its own line.
        lines = stdout.splitlines()
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if not line.startswith('{'):
                continue
            # Try the line by itself first
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
            # Then try the line plus everything after (in case JSON spans lines)
            candidate = "\n".join(lines[i:]).strip()
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass

        # Strategy 2 (fallback): character-level scan from the last '{' backwards.
        # Handles edge case where progress bar interleaved with JSON on the same line.
        last_brace = stdout.rfind('{')
        while last_brace >= 0:
            candidate = stdout[last_brace:].strip()
            # Try shrinking from the right to find balanced braces
            for end in range(len(candidate), 0, -1):
                try:
                    obj = json.loads(candidate[:end])
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    continue
            last_brace = stdout.rfind('{', 0, last_brace)

        return None

    def _parse_response(
        self, 
        result: subprocess.CompletedProcess,
        output_path: str | Path
    ) -> PrimitiveResult:
        """Parse subprocess result into PrimitiveResult.

        Sprint 8: tolerant of stdout chatter from R packages. Tries clean
        whole-stdout parse first; on failure, falls back to extracting the
        trailing JSON object via _extract_trailing_json.
        """
        
        stdout = result.stdout or ""

        # Fast path: stdout is clean JSON (the historical case).
        response: dict | None = None
        if stdout.strip():
            try:
                parsed = json.loads(stdout)
                if isinstance(parsed, dict):
                    response = parsed
            except json.JSONDecodeError:
                # Slow path: stdout has chatter; extract the trailing JSON.
                response = self._extract_trailing_json(stdout)

        # If we still don't have a response object, the primitive truly
        # produced nothing parseable — that's an Invalid response.
        if response is None:
            # An empty stdout with successful exit is also "no response",
            # but distinguishable enough from "garbage stdout" that we
            # preserve the message-truncation behavior for diagnosis.
            tail = stdout[-500:] if stdout else "(empty stdout)"
            return PrimitiveResult(
                success=False,
                output_path=None,
                metadata={},
                warnings=[],
                error="Invalid response",
                message=f"Primitive returned no parseable JSON. Last 500 chars of stdout:\n{tail}\n--- stderr ---\n{(result.stderr or '')[-500:]}"
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

        # An R primitive might emit a JSON response with status="failure"
        # while still exiting with code 0 (rewildr's primitive_failure path
        # may or may not exit non-zero depending on version). Surface this.
        if response.get("status") == "failure":
            return PrimitiveResult(
                success=False,
                output_path=None,
                metadata={},
                warnings=response.get("warnings", []),
                error=response.get("error", "Unknown error"),
                message=response.get("message", "Primitive reported failure")
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