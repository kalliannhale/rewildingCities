"""a carrier is read apart (D-209): the count first, what it rests on, who
counted it, and no range of towns."""

from canopy.wonder.place import IndicatorReading, PlaceReading, _is_carrier, say_place


def _reading(**kw):
    ind = IndicatorReading(
        indicator="library_outlets_per_1000", name="Public library outlets per 1,000 people",
        own_value=kw.get("value", 2 / 9500 * 1000), own_status=kw.get("status", "attached"),
        own_why=kw.get("why", ""), own_moe=None, own_moe_status=None, own_reliability="",
        universe="persons", universe_relation=None, universe_note="",
        carrier=True, own_count=kw.get("count", 2), own_universe_count=kw.get("persons", 9500),
        counted_by="rewildingcities", counts_noun="library outlets")
    return PlaceReading(authority="us_census_sldl", code="23042", found=True, level="sldl",
                        kind="house_district", name="State House District 42",
                        vintage="2024", indicators=[ind])


def test_the_count_comes_first_with_its_persons_and_its_maker():
    text = say_place(_reading())
    assert "this place: 2 library outlets on 9,500 persons (0.21 per 1,000)" in text
    assert "counted by rewildingcities" in text


def test_no_range_of_towns_and_never_an_estimate():
    text = say_place(_reading())
    assert "no range of towns stands in for it" in text
    assert "estimate" not in text
    assert "each range is one estimate per town" not in text


def test_a_place_with_no_people_says_why_it_has_no_rate():
    text = say_place(_reading(value=None, count=0, persons=0, why="zero_population"))
    assert "0 library outlets on 0 persons (no rate: zero_population)" in text


def test_a_carrier_is_known_by_its_method_never_its_name():
    assert _is_carrier({"method": "count_located:located_count"})
    assert not _is_carrier({"method": "derive_indicator:ratio",
                            "indicator": "library_outlets_per_1000"})
    assert not _is_carrier(None)
