#!/usr/bin/env python3
"""Synthetic E2E: 実ビルドの site/index.html をヘッドレスChromeで開き、
(1) 画面の主要数値がデータと一致、(2) グラフが描画、(3) シミュレーターが合成入力に対し期待どおりの値を返す、ことを検査。
合成入力: 保育定員+100%、効果 低0/中4.5/高9 → 追加出生 = 基準×{0, 4.5%, 9%}。"""
import json, pathlib, re, shutil, subprocess, sys, tempfile, html as H
root = pathlib.Path(__file__).resolve().parent.parent
chrome = next((c for c in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"] if shutil.which(c)), None)
if not chrome: sys.exit("Chrome not found")
src = (root / "site/index.html").read_text(encoding="utf-8")
d = json.loads((root / "site/data.json").read_text(encoding="utf-8"))
unit = "47211"
base = sum(r["births"] for r in d["series"][unit] if r["year"] >= 2020) / 5
probe = """
sel.value = "UNIT"; render();
sp.value = "childcare"; loadPolicy(); document.getElementById("s-cap").value = 100; simulate();
const cells = [...document.querySelectorAll("#t-sim tr")].map(tr => [...tr.cells].map(c => c.textContent));
document.getElementById("s-rep").click();
document.querySelector('nav.tabs button[data-tab="order"]').click();
const ord = {o1: document.getElementById("k-o1").textContent, svgs: document.querySelectorAll("#tab-order svg").length, rows: document.querySelectorAll("#t-ord tr").length};
document.body.setAttribute("data-e2e", JSON.stringify({kb: document.getElementById("k-b").textContent, svgs: document.querySelectorAll("svg").length,
  sim: cells, rep: document.getElementById("s-out").value.length, fail: document.body.innerText.includes("Failed to load"), ord}));
""".replace("UNIT", unit)
tmp = pathlib.Path(tempfile.mkdtemp()) / "e2e.html"
tmp.write_text(src.replace("render();\n</script>", "render();\n" + probe + "\n</script>", 1), encoding="utf-8")
out = subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=5000", "--dump-dom", tmp.as_uri()],
                     capture_output=True, text=True, timeout=120).stdout
m = re.search(r'data-e2e="([^"]*)"', out)
if not m: sys.exit("E2E FAILED: probe did not run (script error?)")
r = json.loads(H.unescape(m.group(1)))
errs = []
last = d["series"][unit][-1]["births"]
if r["kb"].replace(",", "") != str(int(last)): errs.append(f"KPI出生数 {r['kb']} ≠ {last}")
if r["svgs"] < 4: errs.append(f"グラフ数 {r['svgs']}")
if r["fail"]: errs.append("Failed to load が表示")
add = [c for c in r["sim"] if c and c[0].startswith("追加出生数")][0][1:]
exp = [base * 0, base * 0.045, base * 0.09]
for got, e in zip(add, exp):
    if abs(float(got.replace(",", "")) - e) > 0.06: errs.append(f"シミュレーター 追加出生 {got} ≠ {e:.1f}")
o1 = int(d["birth_order"]["series"][-1]["births_第1子"])
if r["ord"]["o1"].replace(",", "").replace("人", "") != str(o1): errs.append(f"出生順位KPI {r['ord']['o1']} ≠ {o1}")
if r["ord"]["svgs"] < 2: errs.append(f"出生順位タブのグラフ数 {r['ord']['svgs']}")
if r["ord"]["rows"] != 4: errs.append(f"出生順位の表の行数 {r['ord']['rows']}")
if r["rep"] < 500: errs.append("提言レポートが生成されない")
print("\n".join(errs) or f"E2E passed (unit {unit}, base {base:.1f}, sim {add})"); sys.exit(1 if errs else 0)
