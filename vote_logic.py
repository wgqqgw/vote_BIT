from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class VotingEngine:
    """Core calculation rules for expert/student ranked voting (supports top-N partial ballots)."""

    candidates: List[str]
    expert_ballots: List[Tuple[Dict[str, int], float]] = field(default_factory=list)
    student_ballots: List[Tuple[Dict[str, int], float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.candidates) < 2:
            raise ValueError("候选人至少2人")

    def ensure_candidates(self, new_candidates: List[str]) -> int:
        """Add unseen candidates and return count of newly added ones."""
        added = 0
        exists = set(self.candidates)
        for name in new_candidates:
            if name not in exists:
                self.candidates.append(name)
                exists.add(name)
                added += 1
        return added

    def _validate_ballot(self, ballot: Dict[str, int]) -> None:
        if not ballot:
            raise ValueError("投票不能为空")
        if not set(ballot.keys()).issubset(set(self.candidates)):
            raise ValueError("投票中存在系统未知候选人")

        ranks = sorted(ballot.values())
        expected = list(range(1, len(ballot) + 1))
        if ranks != expected:
            raise ValueError(f"每一票必须对已选择候选人给出1~{len(ballot)}且不重复的排名")

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
            unranked_score = len(ballot) + 1
            for name in self.candidates:
                totals[name] += ballot.get(name, unranked_score) * weight
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


    def _count_selected(self, ballots: List[Tuple[Dict[str, int], float]]) -> Dict[str, float]:
        counts = {name: 0.0 for name in self.candidates}
        for ballot, weight in ballots:
            for name in ballot.keys():
                counts[name] += weight
        return counts

    def _rank_from_counts(self, counts: Dict[str, float]) -> List[Tuple[int, str, float]]:
        ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        return [(i + 1, name, score) for i, (name, score) in enumerate(ordered)]

    def settle_expert_selection_count(self) -> tuple[Dict[str, float], List[Tuple[int, str, float]]]:
        counts = self._count_selected(self.expert_ballots)
        return counts, self._rank_from_counts(counts)

    def settle_student_selection_count(self) -> tuple[Dict[str, float], List[Tuple[int, str, float]]]:
        counts = self._count_selected(self.student_ballots)
        return counts, self._rank_from_counts(counts)

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
