# 在线投票统计系统（可打包 EXE）

这是一个桌面版投票统计工具，满足你描述的 7 人专家/学生综合排名规则。

## 功能

- 扫码投票：点击“扫码打开在线投票链接”，使用摄像头识别二维码，并自动打开其中的在线投票地址（例如问卷星）。
- 专家投票：每一票都需对 7 位候选人给出 1~7 且不重复排名。
- 学生投票：同样给 7 位候选人排名。
- 结算规则：
  1. 先结算专家总分（分数越低排名越高）。
  2. 再结算学生总分并得到学生排名。
  3. 按学生排名对专家总分减分：第1名减7，第2名减6...第7名减1。
  4. 按调整后的专家总分输出最终排名（分数越低越好）。

## 运行

```bash
python -m venv .venv
source .venv/bin/activate   # Windows 用 .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## 打包 EXE（Windows）

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed app.py --name vote_app
```

打包后 EXE 在：

```text
dist/vote_app.exe
```

## 说明

- 候选人默认是“候选人1~候选人7”，可在 `app.py` 中修改。
- 若电脑没有摄像头，扫码功能会提示失败，但统计功能仍可正常使用。
