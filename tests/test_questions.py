from reflexarc.questions import HAZARDS, HAZARD_IDS, CATEGORIES, REVERSIBILITY_LEVELS


def test_hazards_structure():
    assert len(HAZARDS) == 6
    assert len(HAZARD_IDS) == 6
    assert "destructive" in HAZARD_IDS
    assert "exfil" in HAZARD_IDS
    assert "secrets" in HAZARD_IDS
    assert "privilege" in HAZARD_IDS
    assert "money" in HAZARD_IDS
    assert "injection" in HAZARD_IDS

    for q in HAZARDS:
        assert q.id in HAZARD_IDS
        assert len(q.instructions) > 10
        assert len(q.true_text) > 5
        assert len(q.false_text) > 5


def test_reversibility_and_categories():
    assert len(REVERSIBILITY_LEVELS) == 3
    assert len(CATEGORIES) == 6
    assert "read_only" in CATEGORIES
    assert "system_change" in CATEGORIES
