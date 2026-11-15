#!/usr/bin/env python3
"""proposals/*.md の承認記録を検査。判断を書いたのに承認者・理由・日付が空なら失敗。"""
import pathlib, re, sys
root = pathlib.Path(__file__).resolve().parent.parent
errs = []
for f in sorted((root / "proposals").glob("*.md")):
    if f.name == "README.md": continue
    t = f.read_text(encoding="utf-8")
    sec = t.split("## Human Approval", 1)
    if len(sec) < 2: errs.append(f"{f.name}: Human Approval 欄がない"); continue
    body = sec[1].split("\n## ", 1)[0]
    field = lambda k: (re.search(rf"-\s*{k}：(.*)", body) or [None, ""])[1].strip()
    dec = field("判断")
    if dec in ("", "approved / rejected / revise"): continue  # 未承認（proposed）
    if dec not in ("approved", "rejected", "revise"): errs.append(f"{f.name}: 判断は approved / rejected / revise のいずれか（現在: {dec}）")
    for k in ("承認者", "理由", "日付"):
        if not field(k): errs.append(f"{f.name}: {k} が空")
    if field("日付") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", field("日付")): errs.append(f"{f.name}: 日付は YYYY-MM-DD")
print("\n".join(errs) or "Proposals check passed"); sys.exit(1 if errs else 0)
