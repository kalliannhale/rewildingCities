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
        $loam.{semantic_type} -> the one artifact of that type another run
            in this plot made, read through the plot's loam bed, with its
            envelope (D-163, D-164). inputs only.
        $indicators.{indicator_id} -> an indicator's declaration from the
            registry (seeds/indicators/), params only. the primitive receives
            the parsed derivation, so R never reads YAML and a variable code
            is written in exactly one place. D-33.
        $crosswalks.{name} -> a crosswalk's declaration, the one file
            seeds/crosswalks/**/{name}.yml, parsed, params only. resolved
            into params so a run's receipt records the declaration it read,
            and an edit to it is a changed param that freshness sees (D-206).
    """
    
    # Valid reference patterns
    MANIFEST_PATTERN = re.compile(r'^\$manifest\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    CHOICES_PATTERN = re.compile(r'^\$choices\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    PARAMETERS_PATTERN = re.compile(r'^\$parameters\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    STEPS_PATTERN = re.compile(r'^\$steps\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    LOAM_PATTERN = re.compile(r'^\$loam\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    INDICATORS_PATTERN = re.compile(r'^\$indicators\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    WEIGHTS_PATTERN = re.compile(r'^\$weights\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    # the declared small-sample rule (D-106), resolved like $weights
    RELIABILITY_PATTERN = re.compile(r'^\$reliability\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    # a declared crosswalk under seeds/crosswalks/, resolved like $weights (D-206)
    CROSSWALKS_PATTERN = re.compile(r'^\$crosswalks\.([a-zA-Z_][a-zA-Z0-9_]*)$')
    
    # Pattern to detect anything that looks like a reference attempt
    LOOKS_LIKE_REFERENCE = re.compile(r'^\$[a-zA-Z]')
    
    # Valid prefixes for error messages
    VALID_PREFIXES = ("$manifest.", "$choices.", "$parameters.", "$steps.", "$loam.", "$indicators.", "$weights.", "$reliability.", "$crosswalks.")
    
    def __init__(
        self,
        manifest: Manifest,
        experiment: Experiment,
        indicator_registry=None,
        loam_reach=None,
    ):
        self.manifest = manifest
        self.experiment = experiment
        # what answers $loam.<type> (canopy.loam.reach.LoamReach). None means
        # this resolver was given no plot to read, and a $loam. input says so.
        self.loam_reach = loam_reach
        # loaded on first use, so an experiment that never names an indicator
        # never needs the registry to exist. injectable for tests.
        self._indicator_registry = indicator_registry
        
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
            self.STEPS_PATTERN.match(ref) or
            self.LOAM_PATTERN.match(ref) or
            self.INDICATORS_PATTERN.match(ref) or
            self.WEIGHTS_PATTERN.match(ref) or
            self.RELIABILITY_PATTERN.match(ref) or
            self.CROSSWALKS_PATTERN.match(ref)
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

            if ref.startswith("$indicator."):
                suggestions.append("Did you mean '$indicators.' (plural)?")
            
            if ref.startswith("$manifest.") and "." in ref[10:]:
                suggestions.append("$manifest references should be $manifest.{dataset_name} (one level deep)")

            if ref.startswith("$loam.") and "." in ref[6:]:
                suggestions.append("$loam references name a type only, $loam.{semantic_type}, never who made it (D-163)")
            
            suggestion_text = f" {' '.join(suggestions)}" if suggestions else ""
            
            raise ValueError(
                f"Invalid reference '{ref}'{context_msg}. "
                f"Starts with '$' but doesn't match valid patterns.{suggestion_text}\n"
                f"Valid formats: $manifest.{{name}}, $choices.{{name}}, "
                f"$parameters.{{name}}, $steps.{{step_id}}.{{output}}, "
                f"$loam.{{semantic_type}}, "
                f"$indicators.{{indicator_id}}, $weights.{{weighting_id}}, "
                f"$reliability.{{rule_id}}, $crosswalks.{{name}}"
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

        # Try $loam.{semantic_type}
        match = self.LOAM_PATTERN.match(ref)
        if match:
            return self._resolve_loam_ref(match.group(1), context)
        
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
        
        if self.CROSSWALKS_PATTERN.match(ref):
            raise ValueError(
                f"Invalid input reference '{ref}'{context_msg}. "
                f"$crosswalks is for params, not inputs: it names a declaration "
                f"of how to read data, not data (D-206).")

        if (self.INDICATORS_PATTERN.match(ref) or self.WEIGHTS_PATTERN.match(ref)
                or self.RELIABILITY_PATTERN.match(ref)):
            raise ValueError(
                f"Invalid input reference '{ref}'{context_msg}. "
                f"$indicators is for params, not inputs: it names a definition, "
                f"not data. The data an indicator is derived from is a "
                f"$manifest.{{dataset}} of type indicator_source."
            )
        
        raise ValueError(
            f"Cannot resolve input reference '{ref}'{context_msg}. "
            f"Expected $manifest.{{name}}, $steps.{{step_id}}.{{output_name}} "
            f"or $loam.{{semantic_type}}."
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
    
    def _resolve_loam_ref(
        self,
        semantic_type: str,
        context: str = ""
    ) -> tuple[str, str, Envelope]:
        """Resolve a reference to what another run in this plot made (D-163).

        Refusals come from the reach as ValueError, so a step that cannot
        reach its input fails as an input resolution, naming why."""
        context_msg = f" (in {context})" if context else ""
        if self.loam_reach is None:
            raise ValueError(
                f"$loam.{semantic_type}{context_msg}: this resolver was given no "
                f"plot to read, so nothing another run made can be reached (D-164)")
        reached = self.loam_reach.reach(semantic_type, context)
        return reached.path, reached.envelope.metadata["semantic_type"], reached.envelope

    def _resolve_manifest_ref(
        self, 
        dataset_name: str, 
        context: str = ""
    ) -> tuple[str, str, None]:
        """Resolve a reference to a manifest dataset.
        
        Now checks the available flag and provides clear advisory
        messages when data is unavailable or missing from disk.
        """
        context_msg = f" (in {context})" if context else ""
        
        # Check if dataset is declared at all
        if dataset_name not in self.manifest.datasets:
            declared = ", ".join(sorted(self.manifest.datasets.keys())) or "(none)"
            raise ValueError(
                f"Manifest has no dataset '{dataset_name}'{context_msg}. "
                f"Declared datasets in {self.manifest.city_id} manifest: {declared}"
            )
        
        dataset = self.manifest.datasets[dataset_name]
        
        # Check availability flag
        if not dataset.available:
            # Build helpful message based on what we know about the source
            if dataset.is_auto_acquirable:
                hint = (
                    f"This dataset can be auto-acquired. "
                    f"Run the experiment with --resolve-only to attempt acquisition."
                )
            elif dataset.requires_auth:
                hint = (
                    f"This dataset requires authentication "
                    f"(source type: {dataset.source_type}). "
                    f"Run with --resolve-only for setup instructions."
                )
            elif dataset.requires_manual_action:
                notes = dataset.source.get("notes", "") if dataset.source else ""
                hint = (
                    f"This dataset requires manual acquisition. "
                    f"{notes}"
                )
            elif dataset.source is None:
                hint = (
                    f"No source configuration exists for this dataset. "
                    f"Add a 'source:' block to the manifest to enable acquisition."
                )
            else:
                hint = (
                    f"Source type: {dataset.source_type}. "
                    f"Run with --resolve-only to attempt acquisition."
                )
            
            raise ValueError(
                f"Dataset '{dataset_name}' is declared but not available{context_msg}. "
                f"{hint}"
            )
        
        # Dataset is available — check file exists on disk
        path = str(self.manifest.data_dir / dataset.path)
        
        if not Path(path).exists():
            raise FileNotFoundError(
                f"Dataset '{dataset_name}' is marked available but file not found{context_msg}. "
                f"Expected path: {path}\n"
                f"The manifest and filesystem are inconsistent. "
                f"Run with --resolve-only to reconcile, or verify the cache path in the manifest."
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

        # Try $indicators.{id}
        match = self.INDICATORS_PATTERN.match(value)
        if match:
            return self._resolve_indicator(match.group(1), context)

        # Try $weights.{id}
        match = self.WEIGHTS_PATTERN.match(value)
        if match:
            return self._resolve_weights(match.group(1), context)

        # Try $reliability.{id}
        match = self.RELIABILITY_PATTERN.match(value)
        if match:
            return self._resolve_reliability(match.group(1), context)

        # Try $crosswalks.{name}
        match = self.CROSSWALKS_PATTERN.match(value)
        if match:
            return self._resolve_crosswalk(match.group(1), context)
        
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

        if self.LOAM_PATTERN.match(value):
            raise ValueError(
                f"Invalid param reference '{value}' in {context}. "
                f"$loam references data another run made, not param values. "
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
    
    def _resolve_indicator(self, indicator_id: str, context: str = "") -> dict:
        """Resolve an indicator reference to its declaration, as plain JSON."""
        context_msg = f" (in {context})" if context else ""
        registry = self._indicator_registry
        if registry is None:
            from canopy.indicators import IndicatorRegistry
            from canopy.paths import project_root
            try:
                registry = IndicatorRegistry.load(project_root() / "seeds" / "indicators")
            except (FileNotFoundError, ValueError) as e:
                raise ValueError(
                    f"$indicators.{indicator_id}{context_msg} could not be "
                    f"resolved because the indicator registry did not load: {e}")
            self._indicator_registry = registry
        if indicator_id not in registry.all():
            close = self._find_close_matches(indicator_id, registry.all())
            suggestion = f" Did you mean: {', '.join(close)}?" if close else ""
            raise ValueError(
                f"Unknown indicator '{indicator_id}'{context_msg}. "
                f"Declared: {', '.join(registry.all())}.{suggestion}")
        return registry.declaration(indicator_id)

    def _resolve_weights(self, weighting_id: str, context: str = "") -> dict:
        """Resolve a weighting reference to its declaration, as plain JSON."""
        context_msg = f" (in {context})" if context else ""
        from canopy.indicators.weights import WeightsRegistry
        from canopy.paths import project_root
        ids = None
        try:
            from canopy.indicators import IndicatorRegistry
            ids = IndicatorRegistry.load(project_root() / "seeds" / "indicators").all()
        except (FileNotFoundError, ValueError):
            pass
        try:
            reg = WeightsRegistry.load(project_root() / "seeds" / "weights", ids)
            return reg.declaration(weighting_id)
        except KeyError as e:
            raise ValueError(f"{e.args[0]}{context_msg}")
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(f"$weights.{weighting_id}{context_msg} could not be resolved: {e}")

    def _resolve_reliability(self, rule_id: str, context: str = "") -> dict:
        """Resolve a small-sample rule to its declaration, as plain JSON (D-106)."""
        context_msg = f" (in {context})" if context else ""
        from canopy.indicators.reliability import ReliabilityRegistry
        from canopy.paths import project_root
        try:
            reg = ReliabilityRegistry.load(project_root() / "seeds" / "reliability")
            return reg.declaration(rule_id)
        except KeyError as e:
            raise ValueError(f"{e.args[0]}{context_msg}")
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(f"$reliability.{rule_id}{context_msg} could not be resolved: {e}")

    def _resolve_crosswalk(self, name: str, context: str = "") -> dict:
        """Resolve a crosswalk reference to its declaration, as plain JSON (D-206)."""
        context_msg = f" (in {context})" if context else ""
        from canopy.paths import project_root
        try:
            return load_crosswalk(name, project_root() / "seeds" / "crosswalks")
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(f"$crosswalks.{name}{context_msg} could not be resolved: {e}")

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


def load_crosswalk(name: str, root) -> dict:
    """the declaration in the one file <root>/**/<name>.yml, parsed (D-206).

    a crosswalk is found by its name alone, at any depth, so a run never
    writes a path. none, or two files of that name, is refused by name: which
    of two is a choice, not a lookup. the file must hold a mapping. ~"""
    import yaml
    root = Path(root)
    hits = sorted(root.rglob(f"{name}.yml")) if root.is_dir() else []
    if not hits:
        known = sorted(p.stem for p in root.rglob("*.yml")) if root.is_dir() else []
        raise FileNotFoundError(
            f"no crosswalk {name}.yml under {root}. declared: {', '.join(known) or '(none)'}")
    if len(hits) > 1:
        raise ValueError(
            f"{len(hits)} crosswalks are named {name}.yml: "
            f"{', '.join(str(h.relative_to(root)) for h in hits)}; name one uniquely")
    doc = yaml.safe_load(hits[0].read_text())
    if not isinstance(doc, dict):
        raise ValueError(f"{hits[0]} must hold a mapping, not {type(doc).__name__}")
    return doc
