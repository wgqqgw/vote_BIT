from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class VotingEngine:
    """Core calculation rules for expert/student ranked voting."""

    candidates: List[str]
    expert_ballots: List[Tuple[Dict[str, int], float]] = field(default_factory=list)
    student_ballots: List[Tuple[Dict[str, int], float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.candidates) < 2:
            raise ValueError("候选人至少2人")

    def _expected_ranks(self) -> list[int]:
        return list(range(1, len(self.candidates) + 1))

    def _validate_ballot(self, ballot: Dict[str, int]) -> None:
        if set(ballot.keys()) != set(self.candidates):
            raise ValueError("投票中候选人与系统候选人不一致")

        ranks = sorted(ballot.values())
        if ranks != self._expected_ranks():
            raise ValueError(f"每一票必须对候选人给出1~{len(self.candidates)}且不重复的排名")

    def add_expert_ballot(self, ballot: Dict[str, int], weight: float = 1.0) -> None:
        self._validate_ballot(ballot)
        if weight <= 0:
            raise ValueError("权重必须大于0")
        self.expert_ballots.append((ballot, float(weight)))

    def add_student_ballot(self, ballot: Dict[str, int], weight: float = 1.0) -> None:
        self._validate_ballot(ballot)
        if weight <= 0:
            raise ValueError("权重必须大于0")
        self.student_ballots.append((ballot, float(weight)))

    def _sum_scores(self, ballots: List[Tuple[Dict[str, int], float]]) -> Dict[str, float]:
        totals = {name: 0.0 for name in self.candidates}
        for ballot, weight in ballots:
            for name, rank in ballot.items():
                totals[name] += rank * weight
        return totals

    def _rank_from_totals(self, totals: Dict[str, float]) -> List[Tuple[int, str, float]]:
        ordered = sorted(totals.items(), key=lambda x: (x[1], x[0]))
        return [(i + 1, name, score) for i, (name, score) in enumerate(ordered)]

    def settle_experts(self) -> tuple[Dict[str, float], List[Tuple[int, str, float]]]:
        totals = self._sum_scores(self.expert_ballots)
        return totals, self._rank_from_totals(totals)

    def settle_students(self) -> tuple[Dict[str, float], List[Tuple[int, str, float]]]:
        totals = self._sum_scores(self.student_ballots)
        return totals, self._rank_from_totals(totals)

    def final_result(self) -> dict:
        expert_totals, expert_rank = self.settle_experts()
        student_totals, student_rank = self.settle_students()

        adjusted_expert = expert_totals.copy()
        student_adjustment = {}
        candidate_count = len(self.candidates)
        for rank, name, _ in student_rank:
            delta = candidate_count + 1 - rank
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
