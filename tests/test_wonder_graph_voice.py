"""
tests/test_wonder_graph_voice.py  |  rewildingCities, Sprint 05 change 11 (plan builds 4 and 5)

`wonder` opens its plot through open_plot, so it sees the graph's views, and
says what the graph made (D-178): one line when there is no graph, one line
naming every view made with its size, and a line for every view not made and
every value receipt left out, each with why. Nothing refused goes unsaid.
"""

from canopy.cli.wonder import _say_graph

MAINE_LIKE = {
    "places": {"made": True, "rows": 1663},
    "edges": {"made": True, "rows": 4200},
    "indicator_values": {"made": True, "rows": 12526, "collapsed": 3222,
                         "left_out": ["units_values.envelope.json: its file has no unit_authority (D-169)"]},
    "place_values": {"made": True, "by_status": {"attached": 2572, "no_place": 9618}},
    "plot_places": {"made": False, "why": "places[0] names no authority and code: {}"},
}


def test_a_plot_with_no_graph_says_so_once(capsys):
    _say_graph({
        "places": {"made": False, "why": "no run in plot 'nyc' has made places"},
        "edges": {"made": False, "why": "no run in plot 'nyc' has made place_edges"},
        "plot_places": {"made": False, "why": "there are no places to choose from"},
    })
    lines = capsys.readouterr().out.splitlines()
    assert lines == ["(no graph in this plot ~ no run in plot 'nyc' has made places)"]


def test_every_view_made_is_named_with_its_size(capsys):
    _say_graph(MAINE_LIKE)
    first = capsys.readouterr().out.splitlines()[0]
    assert first == ("🕸  graph: places (1,663), edges (4,200), "
                     "indicator_values (12,526), place_values (12,190)")


def test_every_view_not_made_and_every_receipt_left_out_says_why(capsys):
    _say_graph(MAINE_LIKE)
    out = capsys.readouterr().out
    assert "~ no plot_places: places[0] names no authority and code" in out
    assert "~ a value receipt left out: units_values.envelope.json" in out


def test_an_empty_report_says_there_is_no_graph(capsys):
    _say_graph({})
    assert capsys.readouterr().out.startswith("(no graph in this plot ~ ")
