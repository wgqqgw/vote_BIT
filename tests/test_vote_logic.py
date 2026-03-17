from wjx_parser import parse_wjx_ranking_text
from vote_logic import VotingEngine


def test_final_result_rule_with_6_candidates() -> None:
    cands = [f"候选人{i}" for i in range(1, 7)]
    engine = VotingEngine(cands)

    expert_ballot = {
        "候选人1": 1,
        "候选人2": 2,
        "候选人3": 3,
        "候选人4": 4,
        "候选人5": 5,
        "候选人6": 6,
    }
    engine.add_expert_ballot(expert_ballot)

    student_ballot = {
        "候选人1": 6,
        "候选人2": 5,
        "候选人3": 4,
        "候选人4": 3,
        "候选人5": 2,
        "候选人6": 1,
    }
    engine.add_student_ballot(student_ballot)

    result = engine.final_result()

    assert result["student_adjustment"]["候选人6"] == 6
    assert result["student_adjustment"]["候选人1"] == 1
    assert result["final_totals"]["候选人6"] == 0.0


def test_weighted_ballot() -> None:
    cands = [f"候选人{i}" for i in range(1, 7)]
    engine = VotingEngine(cands)
    ballot = {name: i + 1 for i, name in enumerate(cands)}
    engine.add_expert_ballot(ballot, weight=2)
    totals, _ = engine.settle_experts()
    assert totals["候选人1"] == 2.0
    assert totals["候选人6"] == 12.0


def test_parse_wjx_ranking_text_comma_format() -> None:
    text = "李喆，特种雷达→赵泽玮，民用雷达→郑彭楠，特种雷达"
    names = parse_wjx_ranking_text(text)
    assert names == ["李喆", "赵泽玮", "郑彭楠"]


def test_parse_wjx_ranking_text_dash_and_bar_format() -> None:
    text = "陈轲-特种雷达研究所┋张光伟-特种雷达研究所┋王江涛-民用雷达研究所"
    names = parse_wjx_ranking_text(text)
    assert names == ["陈轲", "张光伟", "王江涛"]


def test_parse_wjx_ranking_text_with_varied_separators() -> None:
    text = "李喆，特种雷达┋赵泽玮，民用雷达｜郑彭楠，特种雷达；张凯翔，特种雷达"
    names = parse_wjx_ranking_text(text)
    assert names == ["李喆", "赵泽玮", "郑彭楠", "张凯翔"]


def test_invalid_ballot_reject() -> None:
    cands = [f"候选人{i}" for i in range(1, 7)]
    engine = VotingEngine(cands)
    bad = {name: 1 for name in cands}

    try:
        engine.add_expert_ballot(bad)
        assert False, "should raise"
    except ValueError:
        assert True


def test_parse_wjx_ranking_text_real_dash_sample() -> None:
    text = "田德智-特种雷达研究所┋陈轲-特种雷达研究所┋张光伟-特种雷达研究所┋王江涛-民用雷达研究所┋徐智祥-民用雷达研究所┋杨晓静-多源探测研究所┋李涌睿-空天遥感研究所"
    names = parse_wjx_ranking_text(text)
    assert names == ["田德智", "陈轲", "张光伟", "王江涛", "徐智祥", "杨晓静", "李涌睿"]
