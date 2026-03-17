# 在线投票统计系统（可打包 EXE）

这是一个桌面版投票统计工具，满足 7 人专家/学生综合排名规则。

## 核心说明（根据你的需求）

本系统的“扫码投票”含义是：
- 在桌面软件中展示二维码；
- 专家或学生用自己的手机扫码，打开投票网页并提交；
- 投票结果实时进入桌面软件中，方便你后续一键结算。

## 功能

- 启动投票服务后自动生成两个二维码：
  - 专家投票二维码
  - 学生投票二维码
- 手机扫码后进入网页投票：对 7 名候选人提交 1~7 且不重复的排名。
- 桌面端实时接收票数并显示“第几票已收到”。
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

启动后请点击“启动手机投票服务”，软件会显示二维码。

> 注意：手机需要和运行该软件的电脑在同一局域网下，才能访问二维码对应链接。

## 打包 EXE（Windows）

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed app.py --name vote_app
```

打包后 EXE 在：

```text
dist/vote_app.exe
```
