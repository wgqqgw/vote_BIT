from __future__ import annotations

import io
import socket
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

import qrcode
from PIL import Image, ImageTk
from flask import Flask, redirect, render_template_string, request
from pyngrok import conf, installer, ngrok
from werkzeug.serving import make_server

from vote_logic import VotingEngine


VOTE_PAGE_TEMPLATE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ vote_type_label }}投票</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 700px; margin: 20px auto; padding: 0 12px; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 14px; margin-bottom: 10px; }
    select { width: 100%; font-size: 16px; padding: 8px; }
    button { font-size: 17px; padding: 10px 16px; width: 100%; }
  </style>
</head>
<body>
  <h2>{{ vote_type_label }}投票</h2>
  <p>请为7位候选人设置 <b>1~7 且不重复</b> 的名次（数字越小名次越高）。</p>
  {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
  <form method="post">
    {% for name in candidates %}
      <div class="card">
        <label>{{ name }}</label>
        <select name="{{ name }}" required>
          <option value="">请选择名次</option>
          {% for n in range(1,8) %}
            <option value="{{ n }}">{{ n }}</option>
          {% endfor %}
        </select>
      </div>
    {% endfor %}
    <button type="submit">提交投票</button>
  </form>
</body>
</html>
"""

SUCCESS_TEMPLATE = """
<!doctype html>
<html lang="zh-CN"><meta charset="utf-8" />
<body style="font-family:Arial;max-width:680px;margin:30px auto;padding:0 12px;">
  <h2>✅ 投票成功</h2>
  <p>你的{{ vote_type_label }}投票已提交，可以关闭此页面。</p>
</body></html>
"""


class FlaskServerThread(threading.Thread):
    def __init__(self, app: Flask, host: str, port: int) -> None:
        super().__init__(daemon=True)
        self.server = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self) -> None:
        self.server.serve_forever()


class VotingApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("在线投票统计系统")
        self.root.geometry("1120x780")

        self.candidates = [f"候选人{i}" for i in range(1, 8)]
        self.engine = VotingEngine(self.candidates)

        self.server_thread: FlaskServerThread | None = None
        self.server_host = self._get_local_ip()
        self.server_port = 8765
        self.public_base_url: str | None = None
        self.public_tunnel = None

        self._build_flask_app()
        self._build_ui()

    def _build_flask_app(self) -> None:
        app = Flask(__name__)

        @app.route("/")
        def index() -> Any:
            return redirect("/vote/student")

        @app.route("/vote/<vote_type>", methods=["GET", "POST"])
        def vote(vote_type: str) -> Any:
            if vote_type not in {"expert", "student"}:
                return "vote type invalid", 400

            vote_type_label = "专家" if vote_type == "expert" else "学生"
            if request.method == "GET":
                return render_template_string(
                    VOTE_PAGE_TEMPLATE,
                    vote_type_label=vote_type_label,
                    candidates=self.candidates,
                    error="",
                )

            try:
                ballot = {name: int(request.form.get(name, "0")) for name in self.candidates}
                if vote_type == "expert":
                    self.engine.add_expert_ballot(ballot)
                    self.root.after(
                        0,
                        lambda: self.output.insert(
                            "end", f"来自手机端：已添加专家票，第 {len(self.engine.expert_ballots)} 票。\n"
                        ),
                    )
                else:
                    self.engine.add_student_ballot(ballot)
                    self.root.after(
                        0,
                        lambda: self.output.insert(
                            "end", f"来自手机端：已添加学生票，第 {len(self.engine.student_ballots)} 票。\n"
                        ),
                    )
                return render_template_string(SUCCESS_TEMPLATE, vote_type_label=vote_type_label)
            except Exception as e:
                return render_template_string(
                    VOTE_PAGE_TEMPLATE,
                    vote_type_label=vote_type_label,
                    candidates=self.candidates,
                    error=str(e),
                )

        self.flask_app = app

    def _build_ui(self) -> None:
        title = ttk.Label(self.root, text="7人专家+学生综合投票", font=("Microsoft YaHei", 16, "bold"))
        title.pack(pady=10)

        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=12)

        self.server_mode_var = tk.StringVar(value="public")
        ttk.Label(top_frame, text="投票访问方式：").pack(side="left", padx=6)
        ttk.Radiobutton(top_frame, text="公网(手机4G/5G可访问)", variable=self.server_mode_var, value="public").pack(
            side="left", padx=2
        )
        ttk.Radiobutton(top_frame, text="局域网(同Wi-Fi)", variable=self.server_mode_var, value="lan").pack(side="left", padx=2)

        ttk.Button(top_frame, text="启动手机投票服务", command=self.start_server).pack(side="left", padx=6)
        ttk.Button(top_frame, text="重置所有数据", command=self.reset_all).pack(side="left", padx=6)

        self.status_var = tk.StringVar(value="状态：请选择公网模式后启动服务，生成二维码。")
        ttk.Label(top_frame, textvariable=self.status_var).pack(side="left", padx=16)

        qr_frame = ttk.LabelFrame(self.root, text="扫码投票二维码（手机扫码后可直接投票）")
        qr_frame.pack(fill="x", padx=12, pady=10)

        self.qr_expert_label = ttk.Label(qr_frame, text="专家投票二维码（未生成）")
        self.qr_expert_label.grid(row=0, column=0, padx=12, pady=8)

        self.qr_student_label = ttk.Label(qr_frame, text="学生投票二维码（未生成）")
        self.qr_student_label.grid(row=0, column=1, padx=12, pady=8)

        self.expert_url_var = tk.StringVar(value="专家链接：未生成")
        self.student_url_var = tk.StringVar(value="学生链接：未生成")
        ttk.Label(qr_frame, textvariable=self.expert_url_var).grid(row=1, column=0, padx=8, pady=4)
        ttk.Label(qr_frame, textvariable=self.student_url_var).grid(row=1, column=1, padx=8, pady=4)

        actions = ttk.Frame(self.root)
        actions.pack(fill="x", padx=12, pady=8)
        ttk.Button(actions, text="专家票结算", command=self.settle_expert).pack(side="left", padx=6)
        ttk.Button(actions, text="学生票结算并计算最终排名", command=self.settle_final).pack(side="left", padx=6)

        self.output = tk.Text(self.root, height=22, font=("Consolas", 11))
        self.output.pack(fill="both", expand=True, padx=12, pady=10)
        self.output.insert("end", "欢迎使用投票统计系统。\n")

    def _make_qr_image(self, text: str) -> ImageTk.PhotoImage:
        img = qrcode.make(text).resize((240, 240), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        pil_image = Image.open(buffer)
        return ImageTk.PhotoImage(pil_image)

    def _get_local_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def _get_ngrok_config(self) -> conf.PyngrokConfig:
        app_dir = Path.home() / ".vote_app"
        app_dir.mkdir(parents=True, exist_ok=True)
        ngrok_path = app_dir / "ngrok.exe"
        return conf.PyngrokConfig(ngrok_path=str(ngrok_path))

    def _build_vote_urls(self) -> tuple[str, str]:
        mode = self.server_mode_var.get()
        if mode == "public":
            if not self.public_base_url:
                pyngrok_config = self._get_ngrok_config()
                if not Path(pyngrok_config.ngrok_path).exists():
                    installer.install_ngrok(pyngrok_config)
                self.public_tunnel = ngrok.connect(addr=self.server_port, pyngrok_config=pyngrok_config)
                self.public_base_url = self.public_tunnel.public_url.rstrip("/")
            base = self.public_base_url
        else:
            base = f"http://{self.server_host}:{self.server_port}"

        return f"{base}/vote/expert", f"{base}/vote/student"

    def start_server(self) -> None:
        if self.server_thread is None:
            self.server_thread = FlaskServerThread(self.flask_app, "0.0.0.0", self.server_port)
            self.server_thread.start()

        try:
            expert_url, student_url = self._build_vote_urls()
        except Exception as e:
            self.status_var.set("状态：公网地址创建失败，请切换局域网模式或预置 ngrok.exe。")
            self.output.insert("end", f"公网地址创建失败：{e}\n")
            messagebox.showerror(
                "错误",
                "无法创建公网投票地址。\n"
                "可选方案：\n"
                "1) 切换为局域网模式；\n"
                "2) 手动将 ngrok.exe 放到 %USERPROFILE%/.vote_app/ngrok.exe 后重试。",
            )
            return

        self.expert_url_var.set(f"专家链接：{expert_url}")
        self.student_url_var.set(f"学生链接：{student_url}")

        self.qr_expert_photo = self._make_qr_image(expert_url)
        self.qr_student_photo = self._make_qr_image(student_url)
        self.qr_expert_label.configure(image=self.qr_expert_photo, text="")
        self.qr_student_label.configure(image=self.qr_student_photo, text="")

        access_mode = "公网" if self.server_mode_var.get() == "public" else "局域网"
        self.status_var.set(f"状态：服务已启动（{access_mode}模式），手机可扫码投票。")
        self.output.insert("end", f"投票服务已启动：{expert_url} / {student_url}\n")

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
        self.status_var.set("状态：专家票已结算，可继续学生投票。")
        self.output.insert("end", f"专家票总分：{totals}\n")

    def settle_final(self) -> None:
        if not self.engine.student_ballots:
            messagebox.showwarning("提示", "尚未收到学生票")
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
