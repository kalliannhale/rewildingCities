"""
canopy/primitive.py

Handles invocation of primitives (R and Python) and response parsing.

Sprint 8 patch (2026-05): _parse_response is tolerant of stdout pollution.
The rewildr contract is that primitives emit exactly one JSON object on
stdout (via primitive_success / primitive_failure), but some R packages —
notably terra under conda — write progress bars and other chatter to stdout
that breaks a whole-stdout json.loads(). The parser tries the clean parse
first, then falls back to scanning for the last JSON object in stdout.

Sprint 9 patch (2026-08): the runner now dispatches by primitive extension.
The contract (three JSON args in, one JSON object on stdout) is language-
agnostic, so a Python primitive satisfies it identically; only the invocation
differs. `.R` runs via Rscript, `.py` runs via the current interpreter
(sys.executable, so the subprocess inherits the active canopy env). All parse
logic below is unchanged and shared across both.
"""

import subprocess
import sys
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


# Interpreter dispatch by primitive file extension. The contract is identical
# across languages; only the executable differs. sys.executable keeps a Python
# primitive in the same env as the orchestrator that launched it.
_INTERPRETERS: dict[str, list[str]] = {
    ".R": ["Rscript"],
    ".py": [sys.executable],
}


class PrimitiveRunner:
    """
    Invokes primitives via subprocess and captures results.

    Example:
        runner = PrimitiveRunner()
        result = runner.run(
            primitive="soil/calibrate/solve_intrinsics",   # .R or .py, resolved
            inputs=[PrimitiveInput("images", "plots/.../calibration", "calibration_frames")],
            output_path="seeds/profiles/delton_intrinsics.yml",
            params={"board_cols": 7, "board_rows": 7}
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
        Run a primitive (R or Python).

        Args:
            primitive: Path to primitive relative to project_root, with or
                       without extension (e.g. "soil/calibrate/solve_intrinsics"
                       or "geometry/generate_buffers.R").
            inputs: List of PrimitiveInput objects
            output_path: Where the primitive should write its output
            params: Parameters to pass to the primitive

        Returns:
            PrimitiveResult with success status, metadata, and warnings
        """

        # Resolve primitive path, then pick the interpreter from its extension.
        primitive_path = self._resolve_primitive_path(primitive)
        interpreter = self._interpreter_for(primitive_path)

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
            # Invoke: <interpreter> <primitive> <inputs_json> <output> <params_json>
            result = subprocess.run(
                interpreter + [
                    str(primitive_path),
                    inputs_json_path,
                    str(output_path),
                    params_json_path
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            # Parse response (identical for R and Python)
            return self._parse_response(result, output_path)

        finally:
            # Clean up temp files
            Path(inputs_json_path).unlink(missing_ok=True)
            Path(params_json_path).unlink(missing_ok=True)

    def _resolve_primitive_path(self, primitive: str) -> Path:
        """Resolve a primitive name to a full path.

        If an explicit .R or .py extension is given, honor it. Otherwise look
        for <primitive>.R first (the existing convention, so R behavior is
        unchanged), then <primitive>.py. Paths already include the layer,
        e.g. "soil/calibrate/solve_intrinsics", resolved from project_root.
        """
        suffix = Path(primitive).suffix

        if suffix in _INTERPRETERS:
            candidates = [self.project_root / primitive]
        else:
            candidates = [
                self.project_root / f"{primitive}.R",
                self.project_root / f"{primitive}.py",
            ]

        for path in candidates:
            if path.exists():
                return path

        raise FileNotFoundError(
            f"Primitive not found. Tried: "
            f"{', '.join(str(c) for c in candidates)}"
        )

    @staticmethod
    def _interpreter_for(path: Path) -> list[str]:
        """Choose the interpreter command from the primitive's extension."""
        suffix = Path(path).suffix
        interpreter = _INTERPRETERS.get(suffix)
        if interpreter is None:
            raise ValueError(
                f"Unsupported primitive type '{suffix}'. "
                f"Supported: {', '.join(_INTERPRETERS)}"
            )
        return interpreter

    @staticmethod
    def _extract_trailing_json(stdout: str) -> dict | None:
        """Find the last valid JSON object in stdout, scanning from the end.

        rewildr emits the protocol response as the final stdout write of the
        primitive. Anything before it — terra progress bars, sf load messages,
        R warnings via message(), or torch/cv2 chatter from a Python primitive —
        is ignored. This logic is unchanged from Sprint 8 and shared by both
        languages.
        """
        if not stdout or not stdout.strip():
            return None

        # Strategy 1: scan lines from the end.
        lines = stdout.splitlines()
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if not line.startswith('{'):
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
            candidate = "\n".join(lines[i:]).strip()
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass

        # Strategy 2 (fallback): character-level scan from the last '{'.
        last_brace = stdout.rfind('{')
        while last_brace >= 0:
            candidate = stdout[last_brace:].strip()
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
        """Parse subprocess result into PrimitiveResult. Unchanged from Sprint 8;
        works for R and Python primitives alike."""

        stdout = result.stdout or ""

        response: dict | None = None
        if stdout.strip():
            try:
                parsed = json.loads(stdout)
                if isinstance(parsed, dict):
                    response = parsed
            except json.JSONDecodeError:
                response = self._extract_trailing_json(stdout)

        if response is None:
            tail = stdout[-500:] if stdout else "(empty stdout)"
            return PrimitiveResult(
                success=False,
                output_path=None,
                metadata={},
                warnings=[],
                error="Invalid response",
                message=f"Primitive returned no parseable JSON. Last 500 chars of stdout:\n{tail}\n--- stderr ---\n{(result.stderr or '')[-500:]}"
            )

        if result.returncode != 0:
            return PrimitiveResult(
                success=False,
                output_path=None,
                metadata={},
                warnings=response.get("warnings", []),
                error=response.get("error", "Unknown error"),
                message=response.get("message", result.stderr or "Primitive failed")
            )

        if response.get("status") == "failure":
            return PrimitiveResult(
                success=False,
                output_path=None,
                metadata={},
                warnings=response.get("warnings", []),
                error=response.get("error", "Unknown error"),
                message=response.get("message", "Primitive reported failure")
            )

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
    """Convenience function to run a primitive (R or Python)."""
    runner = PrimitiveRunner(primitives_dir=primitives_dir)
    return runner.run(primitive, inputs, output_path, params)