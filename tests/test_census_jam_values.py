"""tests/test_census_jam_values.py

ACS-6: a Census annotation is recognized whatever decimals it is written
with, and an ordinary value is never mistaken for one.
"""

from canopy.providers.census_acs import jam_key


def test_count_and_median_spellings_are_the_same_annotation():
    assert jam_key("-666666666") == "-666666666"
    assert jam_key("-666666666.0") == "-666666666"
    assert jam_key("-666666666.00") == "-666666666"
    assert jam_key("-222222222.0") == "-222222222"


def test_ordinary_values_are_not_annotations():
    for token in ["24.0", "0", "-1", "51", "", "N", "-666666666.5"]:
        assert jam_key(token) is None
