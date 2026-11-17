"""
tests/test_no_threshold.py ~ NOTHR-1

a barrier with no threshold shows its value and never judges it; an entry
with no value (not acquired, withheld, absent) says so, never that a value
is shown. ~
"""

from canopy.wonder.verdicts import no_threshold


def test_a_value_is_shown_and_never_judged():
    v = no_threshold()
    assert v.verdict == "no_threshold" and "value is shown" in v.says


def test_no_value_never_says_a_value_is_shown():
    v = no_threshold(False, "not acquired: needs our observation")
    assert v.verdict == "no_threshold"
    assert "shown" not in v.says.replace("to show", "")
    assert "no value here" in v.says and "needs our observation" in v.says
    assert v.as_dict()["reason"] == "not acquired: needs our observation"
