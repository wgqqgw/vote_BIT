from __future__ import annotations

import csv
import io
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import qrcode
from PIL import Image, ImageTk

from vote_logic import VotingEngine
from wjx_parser import parse_wjx_ranking_text



class VotingApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("雷达院奖学金专家/学生投票系统")
        self.root.geometry("1180x820")

        self.candidate_vars = [tk.StringVar(value=f"候选人{i}") for i in range(1, 7)]
        self.candidates = [v.get().strip() for v in self.candidate_vars]
        self.engine = VotingEngine(self.candidates)

        self._build_ui()

    def _build_ui(self) -> None:
        title = ttk.Label(self.root, text="雷达院奖学金专家/学生投票系统（问卷星联动）", font=("Microsoft YaHei", 16, "bold"))
        title.pack(pady=10)

        candidate_frame = ttk.LabelFrame(self.root, text="候选人姓名（当前默认6人，可修改后点击“应用候选人”）")
        candidate_frame.pack(fill="x", padx=12, pady=8)

        for i, var in enumerate(self.candidate_vars):
            ttk.Label(candidate_frame, text=f"候选人{i+1}").grid(row=i // 3, column=(i % 3) * 2, padx=6, pady=5, sticky="e")
            ttk.Entry(candidate_frame, textvariable=var, width=18).grid(
                row=i // 3, column=(i % 3) * 2 + 1, padx=6, pady=5, sticky="w"
            )

        ttk.Button(candidate_frame, text="应用候选人", command=self.apply_candidates).grid(row=2, column=0, padx=8, pady=8, sticky="w")

        link_frame = ttk.LabelFrame(self.root, text="问卷星链接与二维码")
        link_frame.pack(fill="x", padx=12, pady=8)

        self.expert_link_var = tk.StringVar(value="")
        self.student_link_var = tk.StringVar(value="")

        ttk.Label(link_frame, text="专家问卷链接：").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(link_frame, textvariable=self.expert_link_var, width=90).grid(row=0, column=1, padx=6, pady=6)

        ttk.Label(link_frame, text="学生问卷链接：").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(link_frame, textvariable=self.student_link_var, width=90).grid(row=1, column=1, padx=6, pady=6)

        ttk.Button(link_frame, text="生成二维码", command=self.generate_qr).grid(row=0, column=2, rowspan=2, padx=8)

        self.qr_expert_label = ttk.Label(link_frame, text="专家二维码（待生成）")
        self.qr_expert_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=8)

        self.qr_student_label = ttk.Label(link_frame, text="学生二维码（待生成）")
        self.qr_student_label.grid(row=2, column=1, columnspan=2, sticky="e", padx=12, pady=8)

        import_frame = ttk.LabelFrame(self.root, text="导入问卷星CSV结果")
        import_frame.pack(fill="x", padx=12, pady=8)

        ttk.Button(import_frame, text="导入专家CSV", command=self.import_expert_csv).pack(side="left", padx=6, pady=8)
        ttk.Button(import_frame, text="导入学生CSV", command=self.import_student_csv).pack(side="left", padx=6, pady=8)
        ttk.Button(import_frame, text="重置数据", command=self.reset_all).pack(side="left", padx=6, pady=8)
        ttk.Button(import_frame, text="专家票结算", command=self.settle_expert).pack(side="left", padx=6, pady=8)
        ttk.Button(import_frame, text="学生票结算并计算最终排名", command=self.settle_final).pack(side="left", padx=6, pady=8)

        self.status_var = tk.StringVar(value="状态：请先填写问卷链接并生成二维码。")
        ttk.Label(self.root, textvariable=self.status_var).pack(fill="x", padx=12)

        self.output = tk.Text(self.root, height=24, font=("Consolas", 11))
        self.output.pack(fill="both", expand=True, padx=12, pady=10)
        self.output.insert(
            "end",
            "欢迎使用系统。\n"
            "当前适配问卷星固定导出格式：第6列为排序结果文本（A，单位→B，单位...）。\n",
        )

    def apply_candidates(self) -> None:
        names = [v.get().strip() for v in self.candidate_vars]
        if any(not n for n in names):
            messagebox.showwarning("提示", "候选人姓名不能为空")
            return
        if len(set(names)) != len(names):
            messagebox.showwarning("提示", "候选人姓名不能重复")
            return

        self.candidates = names
        self.engine = VotingEngine(self.candidates)
        self.status_var.set("状态：候选人已更新，历史票数已清空。")
        self.output.insert("end", f"已更新候选人：{self.candidates}\n")

    def _make_qr_image(self, text: str) -> ImageTk.PhotoImage:
        img = qrcode.make(text).resize((220, 220), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        pil_image = Image.open(buffer)
        return ImageTk.PhotoImage(pil_image)

    def generate_qr(self) -> None:
        expert_url = self.expert_link_var.get().strip()
        student_url = self.student_link_var.get().strip()
        if not expert_url or not student_url:
            messagebox.showwarning("提示", "请先填写专家和学生问卷链接")
            return

        if not (expert_url.startswith("http://") or expert_url.startswith("https://")):
            messagebox.showwarning("提示", "专家链接格式不正确")
            return
        if not (student_url.startswith("http://") or student_url.startswith("https://")):
            messagebox.showwarning("提示", "学生链接格式不正确")
            return

        self.qr_expert_photo = self._make_qr_image(expert_url)
        self.qr_student_photo = self._make_qr_image(student_url)

        self.qr_expert_label.configure(image=self.qr_expert_photo, text="")
        self.qr_student_label.configure(image=self.qr_student_photo, text="")

        self.status_var.set("状态：二维码已生成，可扫码进入问卷星。")
        self.output.insert("end", f"已生成二维码：\n专家：{expert_url}\n学生：{student_url}\n")

    def _load_ballots_from_csv(self, path: str) -> list[dict[str, int]]:
        ballots: list[dict[str, int]] = []
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            raise ValueError("CSV为空")

        for row in rows[1:]:
            if len(row) < 6:
                continue
            ranking_text = row[5].strip()
            if not ranking_text:
                continue

            ordered_names = parse_wjx_ranking_text(ranking_text)
            if len(ordered_names) != len(self.candidates):
                raise ValueError(
                    f"排序候选人数不匹配：CSV中{len(ordered_names)}人，系统中{len(self.candidates)}人"
                )

            if set(ordered_names) != set(self.candidates):
                raise ValueError(
                    "排序项与当前候选人不一致。\n"
                    f"CSV识别：{ordered_names}\n系统候选人：{self.candidates}"
                )

            ballot = {name: rank for rank, name in enumerate(ordered_names, start=1)}
            ballots.append(ballot)

        if not ballots:
            raise ValueError("CSV中没有有效投票数据")
        return ballots

    def _import_csv(self, role: str) -> None:
        path = filedialog.askopenfilename(
            title=f"选择{role}CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if not path:
            return

        try:
            ballots = self._load_ballots_from_csv(path)
            if role == "专家":
                for b in ballots:
                    self.engine.add_expert_ballot(b)
                self.output.insert("end", f"已导入专家CSV：{Path(path).name}，新增 {len(ballots)} 票。\n")
            else:
                for b in ballots:
                    self.engine.add_student_ballot(b)
                self.output.insert("end", f"已导入学生CSV：{Path(path).name}，新增 {len(ballots)} 票。\n")
            self.status_var.set("状态：CSV导入成功。")
        except Exception as e:
            messagebox.showerror("导入失败", str(e))

    def import_expert_csv(self) -> None:
        self._import_csv("专家")

    def import_student_csv(self) -> None:
        self._import_csv("学生")

    def reset_all(self) -> None:
        self.engine = VotingEngine(self.candidates)
        self.output.delete("1.0", "end")
        self.output.insert("end", "已重置票数数据。\n")
        self.status_var.set("状态：票数已重置。")

    def _render_rank(self, title: str, rank_rows: list[tuple[int, str, int]]) -> None:
        self.output.insert("end", f"\n{title}\n")
        self.output.insert("end", "排名\t候选人\t总分(越低越好)\n")
        for r, name, score in rank_rows:
            self.output.insert("end", f"{r}\t{name}\t{score}\n")

    def settle_expert(self) -> None:
        totals, rank_rows = self.engine.settle_experts()
        self._render_rank("专家票结算", rank_rows)
        self.status_var.set("状态：专家票已结算。")
        self.output.insert("end", f"专家票总分：{totals}\n")

    def settle_final(self) -> None:
        if not self.engine.student_ballots:
            messagebox.showwarning("提示", "尚未导入学生票")
            return

        result = self.engine.final_result()
        self._render_rank("学生票结算", result["student_rank"])

        self.output.insert("end", "\n学生排名对专家总分的加权（减分）\n")
        for rank, name, _ in result["student_rank"]:
            delta = result["student_adjustment"][name]
            self.output.insert("end", f"学生第{rank}名：{name}，专家总分减{delta}\n")

        self._render_rank("最终排名（按调整后的专家总分）", result["final_rank"])
        self.status_var.set("状态：最终结果已生成。")


def main() -> None:
    root = tk.Tk()
    VotingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
