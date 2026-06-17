"""The exact 2026 FIFA World Cup knockout bracket (from FIFA's published schedule,
via the Wikipedia knockout-stage article).

R32_SLOTS lists the sixteen round-of-32 ties in *bracket order*: the winners of
slots 1 and 2 meet in the round of 16, 3 and 4 meet, and so on up the tree, so a
flat consecutive-pairing reproduces the real bracket exactly.

Tokens:  ("W", "A") = winner of Group A,  ("R", "A") = runner-up of Group A,
         ("T", "T74") = the third-placed team routed into third-slot T74.
THIRD_SLOTS maps each third-slot to the set of groups whose third-placed team is
eligible for it (FIFA's round-of-32 allocation constraint).
"""

R32_SLOTS = [
    (("W", "E"), ("T", "T74")),   # M74
    (("W", "I"), ("T", "T77")),   # M77
    (("R", "A"), ("R", "B")),     # M73
    (("W", "F"), ("R", "C")),     # M75
    (("R", "K"), ("R", "L")),     # M83
    (("W", "H"), ("R", "J")),     # M84
    (("W", "D"), ("T", "T81")),   # M81
    (("W", "G"), ("T", "T82")),   # M82
    (("W", "C"), ("R", "F")),     # M76
    (("R", "E"), ("R", "I")),     # M78
    (("W", "A"), ("T", "T79")),   # M79
    (("W", "L"), ("T", "T80")),   # M80
    (("W", "J"), ("R", "H")),     # M86
    (("R", "D"), ("R", "G")),     # M88
    (("W", "B"), ("T", "T85")),   # M85
    (("W", "K"), ("T", "T87")),   # M87
]

# slot id -> allowed group letters for the third-placed team
THIRD_SLOTS = {
    "T74": set("ABCDF"),
    "T77": set("CDFGH"),
    "T81": set("BEFIJ"),
    "T82": set("AEHIJ"),
    "T79": set("CEFHI"),
    "T80": set("EHIJK"),
    "T85": set("EFGIJ"),
    "T87": set("DEIJL"),
}


def bracket_pairs(winners):
    """Pair a flat list consecutively for the next round."""
    return [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]
