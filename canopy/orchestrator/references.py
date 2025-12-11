# === Reference Resolution ===
from __future__ import annotations
from pathlib import Path

import re

class ReferenceResolver:
    """
    Resolves references in experiment step definitions.
    
    Handles:
        $manifest.{dataset_name} -> path to dataset from city manifest
        $choices.{choice_name} -> value from experiment's choices block
        $parameters.{param_name} -> value from experiment's parameters block
        $steps.{step_id}.{output_name} -> output from a previous step
    """
    
    # Valid reference patterns
    MANIFEST_PATTERN = re.compile(r'^\$manifest\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    CHOICES_PATTERN = re.compile(r'^\$choices\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    PARAMETERS_PATTERN = re.compile(r'^\$parameters\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    STEPS_PATTERN = re.compile(r'^\$steps\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    
    # Pattern to detect anything that looks like a reference attempt
    LOOKS_LIKE_REFERENCE = re.compile(r'^\$[a-zA-Z]')
    
    # Valid prefixes for error messages
    VALID_PREFIXES = ("$manifest.", "$choices.", "$parameters.", "$steps.")
    
    def __init__(
        self,
        manifest: Manifest,
        experiment: Experiment
    ):
        self.manifest = manifest
        self.experiment = experiment
        
        # Step outputs populated as steps complete
        self.step_outputs: dict[str, dict[str, str]] = {}
        self.step_envelopes: dict[str, dict[str, Envelope]] = {}
    
    def register_step_output(
        self,
        step_id: str,
        output_name: str,
        path: str,
        envelope: Envelope
    ) -> None:
        """Register a completed step's output for future reference resolution."""
        if step_id not in self.step_outputs:
            self.step_outputs[step_id] = {}
            self.step_envelopes[step_id] = {}
        
        self.step_outputs[step_id][output_name] = path
        self.step_envelopes[step_id][output_name] = envelope
    
    def _validate_reference_format(self, ref: str, context: str = "") -> None:
        """
        Check if a string looks like a malformed reference.
        
        Raises ValueError if string starts with $ but doesn't match valid patterns.
        """
        if not isinstance(ref, str):
            return
        
        if not self.LOOKS_LIKE_REFERENCE.match(ref):
            return  # Doesn't look like a reference, that's fine
        
        # It looks like a reference — check if it's valid
        is_valid = (
            self.MANIFEST_PATTERN.match(ref) or
            self.CHOICES_PATTERN.match(ref) or
            self.PARAMETERS_PATTERN.match(ref) or
            self.STEPS_PATTERN.match(ref)
        )
        
        if not is_valid:
            # Try to give a helpful error
            context_msg = f" in {context}" if context else ""
            
            # Check for common typos
            suggestions = []
            for prefix in self.VALID_PREFIXES:
                if ref.startswith(prefix.replace(".", "")):  # e.g., $choices without the dot
                    suggestions.append(f"Did you mean '{prefix}...'? (missing dot)")
                    break
            
            if ref.startswith("$params."):
                suggestions.append("Did you mean '$parameters.'? ($params is not valid)")
            
            if ref.startswith("$step."):
                suggestions.append("Did you mean '$steps.' (plural)?")
            
            if ref.startswith("$manifest.") and "." in ref[10:]:
                suggestions.append("$manifest references should be $manifest.{dataset_name} (one level deep)")
            
            suggestion_text = f" {' '.join(suggestions)}" if suggestions else ""
            
            raise ValueError(
                f"Invalid reference '{ref}'{context_msg}. "
                f"Starts with '$' but doesn't match valid patterns.{suggestion_text}\n"
                f"Valid formats: $manifest.{{name}}, $choices.{{name}}, "
                f"$parameters.{{name}}, $steps.{{step_id}}.{{output}}"
            )
    
    def _check_for_embedded_references(self, value: str, context: str = "") -> None:
        """
        Check if a string contains an embedded reference (not at start).
        
        e.g., "prefix_$choices.thing" or "path/to/$manifest.data"
        """
        if not isinstance(value, str):
            return
        
        # Look for $ followed by word characters anywhere except the start
        embedded_pattern = re.compile(r'.+\$[a-zA-Z]')
        if embedded_pattern.match(value):
            context_msg = f" in {context}" if context else ""
            raise ValueError(
                f"Embedded reference detected in '{value}'{context_msg}. "
                f"References must be the entire value, not embedded in strings. "
                f"If you need string interpolation, resolve the reference first."
            )
    
    def resolve_input(self, ref: str, context: str = "") -> tuple[str, str, Envelope | None]:
        """
        Resolve an input reference to a data path.
        
        Args:
            ref: Reference string like "$manifest.parks" or "$steps.validate_parks.validated"
            context: Description of where this reference appears (for error messages)
        
        Returns:
            Tuple of (path, semantic_type, envelope_or_none)
        
        Raises:
            ValueError: If reference is invalid or unresolvable
        """
        context_msg = f" (in {context})" if context else ""
        
        # Validate format first
        self._validate_reference_format(ref, context)
        self._check_for_embedded_references(ref, context)
        
        # Try $steps.{step_id}.{output_name}
        match = self.STEPS_PATTERN.match(ref)
        if match:
            step_id, output_name = match.groups()
            return self._resolve_step_ref(step_id, output_name, context)
        
        # Try $manifest.{dataset_name}
        match = self.MANIFEST_PATTERN.match(ref)
        if match:
            dataset_name = match.group(1)
            return self._resolve_manifest_ref(dataset_name, context)
        
        # Input references shouldn't use $choices or $parameters
        if self.CHOICES_PATTERN.match(ref):
            raise ValueError(
                f"Invalid input reference '{ref}'{context_msg}. "
                f"$choices is for params, not inputs. "
                f"Inputs must reference data: $manifest.{{dataset}} or $steps.{{step}}.{{output}}."
            )
        
        if self.PARAMETERS_PATTERN.match(ref):
            raise ValueError(
                f"Invalid input reference '{ref}'{context_msg}. "
                f"$parameters is for params, not inputs. "
                f"Inputs must reference data: $manifest.{{dataset}} or $steps.{{step}}.{{output}}."
            )
        
        raise ValueError(
            f"Cannot resolve input reference '{ref}'{context_msg}. "
            f"Expected $manifest.{{name}} or $steps.{{step_id}}.{{output_name}}."
        )
    
    def _resolve_step_ref(
        self, 
        step_id: str, 
        output_name: str, 
        context: str = ""
    ) -> tuple[str, str, Envelope]:
        """Resolve a reference to a previous step's output."""
        context_msg = f" (in {context})" if context else ""
        
        if step_id not in self.step_outputs:
            # Check if it's a known step that hasn't run yet vs unknown step
            known_steps = {step.id for step in self.experiment.steps}
            if step_id in known_steps:
                raise ValueError(
                    f"Step '{step_id}' has not been executed yet{context_msg}. "
                    f"Steps must be ordered so dependencies run first."
                )
            else:
                available = ", ".join(sorted(known_steps)) or "(none)"
                raise ValueError(
                    f"Unknown step '{step_id}'{context_msg}. "
                    f"Available steps: {available}"
                )
        
        if output_name not in self.step_outputs[step_id]:
            available = ", ".join(sorted(self.step_outputs[step_id].keys())) or "(none)"
            raise ValueError(
                f"Step '{step_id}' has no output named '{output_name}'{context_msg}. "
                f"Available outputs from '{step_id}': {available}"
            )
        
        path = self.step_outputs[step_id][output_name]
        envelope = self.step_envelopes[step_id][output_name]
        semantic_type = envelope.metadata["semantic_type"]
        
        return path, semantic_type, envelope
    
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
        path = str(self.manifest.data_dir / dataset.path)
        
        # Validate file exists
        if not Path(path).exists():
            raise FileNotFoundError(
                f"Dataset '{dataset_name}' declared in manifest but file not found{context_msg}. "
                f"Expected path: {path}\n"
                f"Run data fetch/download first, or check manifest cache path."
            )
        
        return path, dataset.semantic_type, None
    
    def resolve_param_value(self, value: Any, context: str = "") -> Any:
        """
        Resolve a parameter value, which may be a reference.
        
        Handles:
            - $choices.{name} -> experiment.choices[name]
            - $parameters.{name} -> experiment.parameters[name]
            - literal values -> returned as-is
            - lists -> each element resolved recursively
            - dicts -> each value resolved recursively
        
        Args:
            value: The value to resolve
            context: Description of where this value appears (for error messages)
        
        Returns:
            The resolved value
        
        Raises:
            ValueError: If a reference is invalid or unresolvable
        """
        # Handle None
        if value is None:
            return None
        
        # Handle lists recursively
        if isinstance(value, list):
            return [
                self.resolve_param_value(item, context=f"{context}[{i}]")
                for i, item in enumerate(value)
            ]
        
        # Handle dicts recursively
        if isinstance(value, dict):
            return {
                k: self.resolve_param_value(v, context=f"{context}.{k}")
                for k, v in value.items()
            }
        
        # Non-strings are literals
        if not isinstance(value, str):
            return value
        
        # Check for malformed references
        self._validate_reference_format(value, context)
        self._check_for_embedded_references(value, context)
        
        # Try $choices.{name}
        match = self.CHOICES_PATTERN.match(value)
        if match:
            choice_name = match.group(1)
            return self._resolve_choice(choice_name, context)
        
        # Try $parameters.{name}
        match = self.PARAMETERS_PATTERN.match(value)
        if match:
            param_name = match.group(1)
            return self._resolve_parameter(param_name, context)
        
        # Check for misuse of $manifest and $steps in params
        if self.MANIFEST_PATTERN.match(value):
            raise ValueError(
                f"Invalid param reference '{value}' in {context}. "
                f"$manifest references data files, not param values. "
                f"Use $choices.{{name}} or $parameters.{{name}} for params."
            )
        
        if self.STEPS_PATTERN.match(value):
            raise ValueError(
                f"Invalid param reference '{value}' in {context}. "
                f"$steps references data outputs, not param values. "
                f"Use $choices.{{name}} or $parameters.{{name}} for params."
            )
        
        # Not a reference — return literal value
        return value
    
    def _resolve_choice(self, choice_name: str, context: str = "") -> Any:
        """Resolve a choice reference."""
        context_msg = f" (in {context})" if context else ""
        
        if choice_name not in self.experiment.choices:
            available = ", ".join(sorted(self.experiment.choices.keys())) or "(none)"
            
            # Check for close matches (typos)
            close_matches = self._find_close_matches(
                choice_name, 
                self.experiment.choices.keys()
            )
            suggestion = ""
            if close_matches:
                suggestion = f" Did you mean: {', '.join(close_matches)}?"
            
            raise ValueError(
                f"Unknown choice '{choice_name}'{context_msg}. "
                f"Available choices: {available}.{suggestion}"
            )
        
        return self.experiment.choices[choice_name]
    
    def _resolve_parameter(self, param_name: str, context: str = "") -> Any:
        """Resolve a parameter reference."""
        context_msg = f" (in {context})" if context else ""
        
        if param_name not in self.experiment.parameters:
            available = ", ".join(sorted(self.experiment.parameters.keys())) or "(none)"
            
            # Check for close matches (typos)
            close_matches = self._find_close_matches(
                param_name,
                self.experiment.parameters.keys()
            )
            suggestion = ""
            if close_matches:
                suggestion = f" Did you mean: {', '.join(close_matches)}?"
            
            raise ValueError(
                f"Unknown parameter '{param_name}'{context_msg}. "
                f"Available parameters: {available}.{suggestion}"
            )
        
        return self.experiment.parameters[param_name]
    
    def _find_close_matches(
        self, 
        name: str, 
        candidates: list[str] | set[str],
        max_distance: int = 2
    ) -> list[str]:
        """Find candidates within edit distance of name (for typo suggestions)."""
        close = []
        for candidate in candidates:
            if self._levenshtein_distance(name, candidate) <= max_distance:
                close.append(candidate)
        return close
    
    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Compute Levenshtein edit distance between two strings."""
        if len(s1) < len(s2):
            return ReferenceResolver._levenshtein_distance(s2, s1)
        
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
    
    def resolve_step_params(self, step: StepDefinition) -> dict[str, Any]:
        """Resolve all references in a step's params dict."""
        context = f"step '{step.id}' params"
        return {
            key: self.resolve_param_value(value, context=f"{context}.{key}")
            for key, value in step.params.items()
        }
    
    def resolve_step_inputs(
        self, 
        step: StepDefinition
    ) -> dict[str, tuple[str, str, Envelope | None]]:
        """
        Resolve all input references for a step.
        
        Returns:
            Dict mapping input_name -> (path, semantic_type, envelope_or_none)
        """
        resolved = {}
        context = f"step '{step.id}' inputs"
        
        for input_name, ref in step.inputs.items():
            resolved[input_name] = self.resolve_input(
                ref, 
                context=f"{context}.{input_name}"
            )
        
        return resolved