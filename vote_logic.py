from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class VotingEngine:
    """Core calculation rules for expert/student ranked voting."""

    candidates: List[str]
    expert_ballots: List[Dict[str, int]] = field(default_factory=list)
    student_ballots: List[Dict[str, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.candidates) != 7:
            raise ValueError("候选人必须是7人")

    def _validate_ballot(self, ballot: Dict[str, int]) -> None:
        if set(ballot.keys()) != set(self.candidates):
            raise ValueError("投票中候选人与系统候选人不一致")

        ranks = sorted(ballot.values())
        if ranks != [1, 2, 3, 4, 5, 6, 7]:
            raise ValueError("每一票必须对7位候选人给出1~7且不重复的排名")

    def add_expert_ballot(self, ballot: Dict[str, int]) -> None:
        self._validate_ballot(ballot)
        self.expert_ballots.append(ballot)

    def add_student_ballot(self, ballot: Dict[str, int]) -> None:
        self._validate_ballot(ballot)
        self.student_ballots.append(ballot)

    def _sum_scores(self, ballots: List[Dict[str, int]]) -> Dict[str, int]:
        totals = {name: 0 for name in self.candidates}
        for ballot in ballots:
            for name, rank in ballot.items():
                totals[name] += rank
        return totals

    def _rank_from_totals(self, totals: Dict[str, int]) -> List[Tuple[int, str, int]]:
        ordered = sorted(totals.items(), key=lambda x: (x[1], x[0]))
        return [(i + 1, name, score) for i, (name, score) in enumerate(ordered)]

    def settle_experts(self) -> tuple[Dict[str, int], List[Tuple[int, str, int]]]:
        totals = self._sum_scores(self.expert_ballots)
        return totals, self._rank_from_totals(totals)

    def settle_students(self) -> tuple[Dict[str, int], List[Tuple[int, str, int]]]:
        totals = self._sum_scores(self.student_ballots)
        return totals, self._rank_from_totals(totals)

    def final_result(self) -> dict:
        expert_totals, expert_rank = self.settle_experts()
        student_totals, student_rank = self.settle_students()

        # 学生第1名减7分，第2名减6分...第7名减1分
        adjusted_expert = expert_totals.copy()
        student_adjustment = {}
        for rank, name, _ in student_rank:
            delta = 8 - rank
            adjusted_expert[name] -= delta
            student_adjustment[name] = delta

        final_rank = self._rank_from_totals(adjusted_expert)

        return {
            "expert_totals": expert_totals,
            "expert_rank": expert_rank,
            "student_totals": student_totals,
            "student_rank": student_rank,
            "student_adjustment": student_adjustment,
            "final_totals": adjusted_expert,
            "final_rank": final_rank,
        }
