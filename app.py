from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

import cv2

from vote_logic import VotingEngine


class VotingApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("在线投票统计系统")
        self.root.geometry("980x720")

        self.candidates = [f"候选人{i}" for i in range(1, 8)]
        self.engine = VotingEngine(self.candidates)

        self._build_ui()

    def _build_ui(self) -> None:
        title = ttk.Label(self.root, text="7人专家+学生综合投票", font=("Microsoft YaHei", 16, "bold"))
        title.pack(pady=10)

        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=12)

        ttk.Button(top_frame, text="扫码打开在线投票链接", command=self.scan_qr_and_open).pack(side="left", padx=6)
        ttk.Button(top_frame, text="重置所有数据", command=self.reset_all).pack(side="left", padx=6)

        self.status_var = tk.StringVar(value="状态：请先录入专家投票。")
        ttk.Label(top_frame, textvariable=self.status_var).pack(side="left", padx=16)

        form = ttk.LabelFrame(self.root, text="当前录入的一票（给每位候选人设置1~7且不重复）")
        form.pack(fill="x", padx=12, pady=10)

        self.rank_vars: dict[str, tk.IntVar] = {}
        for i, name in enumerate(self.candidates):
            row = i // 4
            col = (i % 4) * 2
            ttk.Label(form, text=name).grid(row=row, column=col, padx=6, pady=8, sticky="e")
            v = tk.IntVar(value=i + 1)
            self.rank_vars[name] = v
            spin = ttk.Spinbox(form, from_=1, to=7, width=5, textvariable=v)
            spin.grid(row=row, column=col + 1, padx=6, pady=8, sticky="w")

        actions = ttk.Frame(self.root)
        actions.pack(fill="x", padx=12, pady=8)

        ttk.Button(actions, text="添加专家票", command=self.add_expert_vote).pack(side="left", padx=6)
        ttk.Button(actions, text="专家票结算", command=self.settle_expert).pack(side="left", padx=6)
        ttk.Button(actions, text="添加学生票", command=self.add_student_vote).pack(side="left", padx=6)
        ttk.Button(actions, text="学生票结算并计算最终排名", command=self.settle_final).pack(side="left", padx=6)

        self.output = tk.Text(self.root, height=28, font=("Consolas", 11))
        self.output.pack(fill="both", expand=True, padx=12, pady=10)
        self.output.insert("end", "欢迎使用投票统计系统。\n")

    def reset_all(self) -> None:
        self.engine = VotingEngine(self.candidates)
        self.output.delete("1.0", "end")
        self.output.insert("end", "已重置。\n")
        self.status_var.set("状态：请先录入专家投票。")

    def _current_ballot(self) -> dict[str, int]:
        ballot = {name: int(var.get()) for name, var in self.rank_vars.items()}
        ranks = sorted(ballot.values())
        if ranks != [1, 2, 3, 4, 5, 6, 7]:
            raise ValueError("当前这一票无效：必须是1~7且不重复")
        return ballot

    def _render_rank(self, title: str, rank_rows: list[tuple[int, str, int]]) -> None:
        self.output.insert("end", f"\n{title}\n")
        self.output.insert("end", "排名\t候选人\t总分(越低越好)\n")
        for r, name, score in rank_rows:
            self.output.insert("end", f"{r}\t{name}\t{score}\n")

    def add_expert_vote(self) -> None:
        try:
            ballot = self._current_ballot()
            self.engine.add_expert_ballot(ballot)
            self.output.insert("end", f"已添加专家票，第 {len(self.engine.expert_ballots)} 票。\n")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def add_student_vote(self) -> None:
        if not self.engine.expert_ballots:
            messagebox.showwarning("提示", "请先录入并结算专家票")
            return
        try:
            ballot = self._current_ballot()
            self.engine.add_student_ballot(ballot)
            self.output.insert("end", f"已添加学生票，第 {len(self.engine.student_ballots)} 票。\n")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def settle_expert(self) -> None:
        totals, rank_rows = self.engine.settle_experts()
        self._render_rank("专家票结算", rank_rows)
        self.status_var.set("状态：专家票已结算，可开始录入学生票。")
        self.output.insert("end", f"专家票总分：{totals}\n")

    def settle_final(self) -> None:
        if not self.engine.student_ballots:
            messagebox.showwarning("提示", "请先录入学生票")
            return

        result = self.engine.final_result()
        self._render_rank("学生票结算", result["student_rank"])

        self.output.insert("end", "\n学生排名对专家总分的加权（减分）\n")
        for rank, name, _ in result["student_rank"]:
            delta = result["student_adjustment"][name]
            self.output.insert("end", f"学生第{rank}名：{name}，专家总分减{delta}\n")

        self._render_rank("最终排名（按调整后的专家总分）", result["final_rank"])
        self.status_var.set("状态：最终结果已生成。")

    def scan_qr_and_open(self) -> None:
        self.status_var.set("状态：正在打开摄像头扫码...按 Q 退出。")

        def worker() -> None:
            detector = cv2.QRCodeDetector()
            cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                self.root.after(0, lambda: messagebox.showerror("错误", "无法打开摄像头"))
                self.root.after(0, lambda: self.status_var.set("状态：摄像头打开失败。"))
                return

            decoded = None
            while True:
                ok, frame = cap.read()
                if not ok:
                    continue
                data, _, _ = detector.detectAndDecode(frame)
                cv2.imshow("扫码窗口 - 按 Q 退出", frame)
                key = cv2.waitKey(1) & 0xFF
                if data:
                    decoded = data
                    break
                if key == ord("q"):
                    break

            cap.release()
            cv2.destroyAllWindows()

            if decoded:
                self.root.after(0, lambda: self.status_var.set(f"状态：扫码成功，已尝试打开：{decoded}"))
                webbrowser.open(decoded)
            else:
                self.root.after(0, lambda: self.status_var.set("状态：未识别到二维码。"))

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    root = tk.Tk()
    app = VotingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
