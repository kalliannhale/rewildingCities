"""
canopy/pr_io.py
Kalli A. Hale | August 2026 | rewildingCities

Python side of the primitive contract. The R primitives use the rewildr
helpers (parse_primitive_args, get_input, get_param, warnings_collector,
primitive_success, primitive_failure); this module is the byte-for-byte
Python equivalent, so a Python primitive satisfies the SAME stdout-JSON
contract the orchestrator already speaks. No R involved.

Contract (identical to the R side):
  argv: <inputs_json_or_path> <output_path> <params_json_or_path>
  on success: print JSON {..metadata.., "warnings": [...], "status": "success"}, exit 0
  on failure: print JSON {"status": "failure", "error": ..., "message": ...,
                          "warnings": [...]}, exit 1
  warnings: {"level": "info"|"warning"|"critical", "primitive": str, "message": str}

The primitive writes its OUTPUT FILE itself and prints metadata to stdout.
It does NOT build the envelope; the EnvelopeBuilder wraps the primitive and
assembles provenance/hashes around this metadata.
"""

import sys
import json
import os
from contextlib import contextmanager


# ---- argument parsing ----------------------------------------------------

def _parse_json_arg(arg, name):
    """A JSON arg is either an inline JSON string or a path to a JSON file."""
    if os.path.exists(arg):
        try:
            with open(arg) as f:
                return json.load(f)
        except Exception as e:
            primitive_failure(f"Failed to parse {name} file", str(e))
    try:
        return json.loads(arg)
    except Exception as e:
        primitive_failure(f"Failed to parse {name} JSON", str(e))


def parse_primitive_args(argv=None):
    """Standard arg parse. Returns dict with 'inputs', 'output', 'params'."""
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) < 3:
        primitive_failure(
            "Invalid arguments",
            "Usage: primitive.py <inputs_json> <output_path> <params_json>")
    return {
        "inputs": _parse_json_arg(argv[0], "inputs"),
        "output": argv[1],
        "params": _parse_json_arg(argv[2], "params"),
    }


def get_input(inputs, name, required=True, must_exist=True):
    """Extract a named input path. Fails if required-and-missing, or if the
    path must exist and does not. (Directories are valid inputs; a calibration
    set is a directory of frames.)"""
    path = inputs.get(name) if isinstance(inputs, dict) else None
    if path is None:
        if required:
            primitive_failure("Missing required input",
                              f"Input '{name}' is required but not provided")
        return None
    if must_exist and not os.path.exists(path):
        primitive_failure("Input not found",
                          f"Input '{name}' path does not exist: {path}")
    return path


def get_param(params, name, default=None):
    """Parameter with default. Nothing capture-specific should be hardcoded in
    a primitive; it should arrive here."""
    if not isinstance(params, dict):
        return default
    val = params.get(name)
    return default if val is None else val


def require_param(params, name):
    """A parameter with no safe default (e.g. board dimensions). Fail loudly
    rather than guess, since a wrong silent default is the worst failure mode."""
    val = params.get(name) if isinstance(params, dict) else None
    if val is None:
        primitive_failure("Missing required parameter",
                          f"Parameter '{name}' is required (no safe default)")
    return val


# ---- warnings collector --------------------------------------------------

class WarningsCollector:
    """Mirror of rewildr::warnings_collector. Accumulates typed warnings."""
    _LEVELS = ("info", "warning", "critical")

    def __init__(self, primitive=None):
        self._primitive = primitive
        self._warnings = []

    def add(self, level, primitive_name, message):
        if level not in self._LEVELS:
            raise ValueError("level must be info, warning, or critical")
        self._warnings.append({"level": level,
                               "primitive": primitive_name,
                               "message": message})

    def _shorthand(self, level, message):
        if self._primitive is None:
            raise ValueError("No default primitive set for shorthand warning")
        self._warnings.append({"level": level,
                               "primitive": self._primitive,
                               "message": message})

    def info(self, message):     self._shorthand("info", message)
    def warn(self, message):     self._shorthand("warning", message)
    def critical(self, message): self._shorthand("critical", message)

    def get(self):           return list(self._warnings)
    def has_warnings(self):  return len(self._warnings) > 0
    def has_critical(self):  return any(w["level"] == "critical" for w in self._warnings)
    def count(self, level=None):
        if level is None:
            return len(self._warnings)
        return sum(1 for w in self._warnings if w["level"] == level)


# ---- success / failure ---------------------------------------------------

def _emit(payload):
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def primitive_success(metadata, warnings=None):
    """Print metadata + warnings to stdout, exit 0."""
    if isinstance(warnings, WarningsCollector):
        warnings = warnings.get()
    out = dict(metadata)
    out["warnings"] = warnings or []
    out["status"] = "success"
    _emit(out)
    sys.exit(0)


def primitive_failure(error, message, warnings=None):
    """Print an error blob to stdout, exit 1."""
    if isinstance(warnings, WarningsCollector):
        warnings = warnings.get()
    _emit({"status": "failure", "error": error,
           "message": message, "warnings": warnings or []})
    sys.exit(1)


@contextmanager
def primitive_error_handling(warnings=None):
    """Wrap primitive logic; any uncaught exception becomes a clean failure
    blob instead of a traceback the orchestrator can't parse."""
    try:
        yield
    except SystemExit:
        raise  # primitive_success/failure already handled it
    except Exception as e:
        primitive_failure("Execution error", str(e), warnings=warnings)
