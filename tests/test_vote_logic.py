from vote_logic import VotingEngine


def test_final_result_rule() -> None:
    cands = [f"候选人{i}" for i in range(1, 8)]
    engine = VotingEngine(cands)

    # 专家票：候选人1最好
    expert_ballot = {
        "候选人1": 1,
        "候选人2": 2,
        "候选人3": 3,
        "候选人4": 4,
        "候选人5": 5,
        "候选人6": 6,
        "候选人7": 7,
    }
    engine.add_expert_ballot(expert_ballot)

    # 学生票：反向，候选人7最好
    student_ballot = {
        "候选人1": 7,
        "候选人2": 6,
        "候选人3": 5,
        "候选人4": 4,
        "候选人5": 3,
        "候选人6": 2,
        "候选人7": 1,
    }
    engine.add_student_ballot(student_ballot)

    result = engine.final_result()

    # 学生第一名候选人7应减7
    assert result["student_adjustment"]["候选人7"] == 7
    # 学生第七名候选人1应减1
    assert result["student_adjustment"]["候选人1"] == 1
    # 专家原分7 - 7 = 0
    assert result["final_totals"]["候选人7"] == 0


def test_invalid_ballot_reject() -> None:
    cands = [f"候选人{i}" for i in range(1, 8)]
    engine = VotingEngine(cands)
    bad = {name: 1 for name in cands}

    try:
        engine.add_expert_ballot(bad)
        assert False, "should raise"
    except ValueError:
        assert True
