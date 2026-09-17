"""

canopy/wonder/voice.py

voice ~ saying a wondering plainly, for anyone

the same truth, in words a fifth grader or a beloved elder can hold. voice
renders a composed wondering warmly and honestly ~ it never simplifies away
the caveats, because the honesty is the teaching. one telling serves the
child and the scientist; depth is emergent from attention, not a separate
mode. ♡

"""

from __future__ import annotations

from .wondering import Composed


def speak(composed: Composed) -> str:
    """tell the person, plainly, what we built together and what it means. ~"""
    g = composed.guidance
    opening = {
        "ready": "we built your experiment, and your community already has everything it needs. 🌱",
        "partial": "we built your experiment. it will work, with one honest thing to keep in mind. 🌤",
        "not_yet": "we built your experiment together. your community is missing a piece, and that is okay ~ you can still run it and see what happens. 🌰",
    }.get(g.verdict, "we built your experiment together.")

    lines = [opening, "", f'your question: "{g.question}"', ""]

    if g.what_youll_learn:
        lines.append("here is what you could find out:")
        for q in g.what_youll_learn[:4]:
            lines.append(f"   ~ {q}")
        lines.append("")

    if g.cannot_yet:
        lines.append("here is what it can't quite tell you yet, and why:")
        for c in g.cannot_yet:
            lines.append(f"   ~ {c}")
        lines.append("")
    if g.whats_uncertain:
        lines.append("here is where the answer is a little fuzzy, honestly:")
        for u in g.whats_uncertain:
            lines.append(f"   ~ {u}")
        lines.append("")

    lines.append(g.the_wide_door)
    if composed.path:
        lines.append("")
        lines.append(f"your experiment recipe is saved here: {composed.path}")
        lines.append("when you're ready, `rewilding sows` will run it for you.")
    return "\n".join(lines)
