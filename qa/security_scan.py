#!/usr/bin/env python3
"""Security/Privacy: 追跡ファイルと生成サイトに秘密情報・個人情報らしき文字列がないか検査。"""
import pathlib, re, subprocess, sys
root = pathlib.Path(__file__).resolve().parent.parent
files = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True).stdout.split()
files = [root / f for f in files] + [p for p in (root / "site").glob("*") if p.is_file()]
PAT = {
    "github_token": r"gh[pousr]_[A-Za-z0-9]{30,}", "aws_key": r"AKIA[0-9A-Z]{16}", "private_key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "estat_appid_literal": r"appId=[0-9a-f]{40}", "generic_secret": r"(?i)(api[_-]?key|secret|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
    "email": r"[A-Za-z0-9._%+-]+@(?!users\.noreply\.github\.com|anthropic\.com)[A-Za-z0-9.-]+\.[a-z]{2,}",
    "phone_jp": r"(?<![\w/.-])0\d{1,4}-\d{1,4}-\d{4}(?![\w-])",
}
errs = []
for f in files:
    if f.suffix in (".png", ".jpg", ".pdf", ".xls", ".xlsx") or not f.exists(): continue
    t = f.read_text(encoding="utf-8", errors="ignore")
    for k, p in PAT.items():
        for m in re.finditer(p, t):
            errs.append(f"{f.relative_to(root)}: {k}: {m.group(0)[:12]}…")
print("\n".join(errs) or f"Security scan passed ({len(files)} files)"); sys.exit(1 if errs else 0)
