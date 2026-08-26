"""
tests/orchestrator/test_preconditions.py

Synthetic-first tests for the precondition gate. Uses tiny duck-typed fakes for
the input envelopes so nothing depends on the full envelope machinery.

Run with pytest, or standalone:  python tests/orchestrator/test_preconditions.py
"""

try:
    from canopy.orchestrator.preconditions import check_preconditions
except ImportError:  # local testbed
    from preconditions import check_preconditions


# ── duck-typed fakes matching what the real envelope exposes ────────────────

class _Prov:
    def __init__(self, primitive): self.primitive = primitive

class _Warn:
    def __init__(self, level): self.level = level

class _Env:
    def __init__(self, provenance=(), warnings=()):
        self.provenance = list(provenance)
        self.warnings = list(warnings)

class _Input:
    def __init__(self, env=None): self.envelope = env


def _validated_input(extra_warnings=()):
    return _Input(_Env(provenance=[_Prov("acquire"), _Prov("validate_vector")],
                       warnings=list(extra_warnings)))

def _unvalidated_input():
    return _Input(_Env(provenance=[_Prov("acquire")]))


# ── tests ───────────────────────────────────────────────────────────────────

def test_no_preconditions_passes():
    out = check_preconditions([], [_unvalidated_input()])
    assert out.ok and not out.failures

def test_provenance_contains_pass_with_note():
    out = check_preconditions([{"provenance_contains": "validate_vector"}],
                              [_validated_input()])
    assert out.ok
    assert any("validate_vector" in n for n in out.notes)

def test_provenance_contains_fail():
    out = check_preconditions([{"provenance_contains": "validate_vector"}],
                              [_unvalidated_input()])
    assert not out.ok
    assert any("validate_vector" in f for f in out.failures)

def test_no_unresolved_critical_pass():
    out = check_preconditions([{"no_unresolved_critical": True}],
                              [_validated_input(extra_warnings=[_Warn("info"), _Warn("warning")])])
    assert out.ok

def test_no_unresolved_critical_fail():
    out = check_preconditions([{"no_unresolved_critical": True}],
                              [_validated_input(extra_warnings=[_Warn("critical")])])
    assert not out.ok
    assert any("critical" in f for f in out.failures)

def test_combined_pass_emits_two_notes():
    out = check_preconditions(
        [{"provenance_contains": "validate_vector"}, {"no_unresolved_critical": True}],
        [_validated_input(extra_warnings=[_Warn("info")])],
    )
    assert out.ok
    assert len(out.notes) == 2

def test_combined_collects_all_failures():
    out = check_preconditions(
        [{"provenance_contains": "validate_vector"}, {"no_unresolved_critical": True}],
        [_Input(_Env(provenance=[_Prov("acquire")], warnings=[_Warn("critical")]))],
    )
    assert not out.ok
    assert len(out.failures) == 2   # both, not just the first

def test_provenance_union_across_inputs():
    # one input validated, one not — union should satisfy provenance_contains
    out = check_preconditions([{"provenance_contains": "validate_vector"}],
                              [_unvalidated_input(), _validated_input()])
    assert out.ok

def test_unknown_predicate_fails():
    out = check_preconditions([{"teleport": True}], [_validated_input()])
    assert not out.ok
    assert any("unknown precondition" in f for f in out.failures)

def test_malformed_precondition_fails():
    out = check_preconditions([{"a": 1, "b": 2}], [_validated_input()])
    assert not out.ok
    assert any("malformed" in f for f in out.failures)

def test_raw_input_without_envelope_is_safe():
    # a raw file input (no envelope) must not crash; provenance simply absent
    out = check_preconditions([{"provenance_contains": "validate_vector"}],
                              [_Input(env=None)])
    assert not out.ok
    assert any("validate_vector" in f for f in out.failures)


# ── standalone runner ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import traceback
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t(); print(f"PASS  {t.__name__}"); passed += 1
        except Exception:
            print(f"FAIL  {t.__name__}"); traceback.print_exc(); failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
