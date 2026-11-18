"""Seam 1: Steady Nerve (R20), a once-per-long-rest reroll of a failed saving throw."""
from pidm.tools import snapshot


def save(g, dc=15):
    return g.ok("saving_throw", target="character", ability="dex", dc=dc)


def test_failed_save_is_rerolled_and_the_new_roll_stands_even_if_lower(make_game):
    # R20: dex +2 vs DC 15. 12 fails (14); the reroll of 3 is lower (5) and still stands.
    g = make_game("fighter").script(12, 3)
    r = save(g)
    assert r["steady_nerve"] and r["total"] == 5 and not r["success"]
    assert [x.total for x in g.last_rolls] == [14, 5]


def test_reroll_can_turn_a_failure_into_a_success(make_game):
    g = make_game("fighter").script(5, 18)
    r = save(g)
    assert r["steady_nerve"] and r["success"] and r["total"] == 20


def test_a_passed_save_spends_nothing(make_game):
    g = make_game("fighter").script(18)
    r = save(g)
    assert r["success"] and "steady_nerve" not in r
    assert "steady_nerve" not in g.ch.feature_uses


def test_one_use_then_exhausted(make_game):
    g = make_game("fighter").script(5, 6, 4)
    assert save(g)["steady_nerve"]
    r = save(g)  # no second reroll: one die only
    assert not r["success"] and "steady_nerve" not in r
    assert len(g.last_rolls) == 1


def test_short_rest_keeps_it_spent_and_long_rest_restores_it(make_game):
    g = make_game("fighter").script(5, 6)
    save(g)
    g.ok("rest", kind="short")
    assert g.ch.feature_uses["steady_nerve"] == 1
    g.ok("rest", kind="long")
    assert "steady_nerve" not in g.ch.feature_uses
    g.script(5, 6)
    assert save(g)["steady_nerve"]


def test_auto_fail_has_no_roll_to_reroll(make_game):
    # §5: a paralyzed Character automatically fails Str and Dex saves.
    g = make_game("fighter")
    g.ok("set_condition", target="character", condition="paralyzed")
    r = save(g)
    assert r["auto_fail"] and "steady_nerve" not in g.ch.feature_uses


def test_death_saves_may_use_it(make_game):
    # R20: a death saving throw is a saving throw. 4 fails, the reroll of 15 succeeds.
    g = make_game("fighter").script(4, 15, 10, 12, 2)  # then 1d4 hours
    r = g.ok("apply_damage", target="character", amount="12", damage_type="slashing")
    saves = r["dying"]["death_saves"]
    assert saves[0]["roll"] == 15 and saves[0].get("steady_nerve")
    assert g.ch.feature_uses["steady_nerve"] == 1


def test_sheet_shows_the_feature_and_its_use(make_game):
    g = make_game("wizard").script(5, 6)
    assert snapshot(g.state)["character"]["features"]["steady_nerve"] == "ready"
    save(g)
    assert snapshot(g.state)["character"]["features"]["steady_nerve"] == "spent"
