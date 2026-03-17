from wjx_parser import parse_wjx_ranking_text
from vote_logic import VotingEngine


def test_final_result_rule_with_full_6_candidates() -> None:
    cands = [f"候选人{i}" for i in range(1, 7)]
    engine = VotingEngine(cands)

    expert_ballot = {name: i + 1 for i, name in enumerate(cands)}
    student_ballot = {name: 6 - i for i, name in enumerate(cands)}

    engine.add_expert_ballot(expert_ballot)
    engine.add_student_ballot(student_ballot)

    result = engine.final_result()
    assert result["student_adjustment"]["候选人6"] == 6
    assert result["student_adjustment"]["候选人1"] == 1


def test_partial_ballot_supported_for_topx() -> None:
    engine = VotingEngine(["甲", "乙", "丙", "丁"])
    # 只投前2名
    engine.add_expert_ballot({"甲": 1, "乙": 2})
    totals, _ = engine.settle_experts()
    # 未入选者按 len(ballot)+1=3 计分
    assert totals["丙"] == 3.0
    assert totals["丁"] == 3.0


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


def test_parse_wjx_ranking_text_real_dash_sample() -> None:
    text = "田德智-特种雷达研究所┋陈轲-特种雷达研究所┋张光伟-特种雷达研究所┋王江涛-民用雷达研究所┋徐智祥-民用雷达研究所┋杨晓静-多源探测研究所┋李涌睿-空天遥感研究所"
    names = parse_wjx_ranking_text(text)
    assert names == ["田德智", "陈轲", "张光伟", "王江涛", "徐智祥", "杨晓静", "李涌睿"]


def test_invalid_ballot_reject() -> None:
    engine = VotingEngine(["甲", "乙", "丙"])
    bad = {"甲": 1, "乙": 1}
    try:
        engine.add_expert_ballot(bad)
        assert False, "should raise"
    except ValueError:
        assert True


def test_topx_selection_count() -> None:
    engine = VotingEngine(["李涌睿", "王国庆", "张三"])
    # 3位评委：李涌睿被选3次，王国庆2次，张三1次
    engine.add_expert_ballot({"李涌睿": 1, "王国庆": 2})
    engine.add_expert_ballot({"李涌睿": 1, "张三": 2})
    engine.add_expert_ballot({"李涌睿": 1, "王国庆": 2})

    counts, rows = engine.settle_expert_selection_count()
    assert counts["李涌睿"] == 3
    assert counts["王国庆"] == 2
    assert counts["张三"] == 1
    assert rows[0][1] == "李涌睿"
