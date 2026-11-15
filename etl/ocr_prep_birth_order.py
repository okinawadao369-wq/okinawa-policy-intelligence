#!/usr/bin/env python3
"""2022年（画像PDF）出生第4表の OCR テキストを、parse_pref_birth_order.py が読める形に整える。
ページ順に引数で渡す: A列（総数・第1子～第3子）ページ2枚 → B列（第4子・第5子以上・不詳）ページ2枚。
年齢ラベルは OCR で「～」が崩れるため、先頭の数字で判定する。数値以外のトークン（。| など）は捨てる。"""
import re, sys
pages_a, pages_b = sys.argv[1:3], sys.argv[3:5]
AGE_BY_PREFIX = [("総数", "総数"), ("14", "１４歳以下"), ("15", "１５～１９歳"), ("20", "２０～２４歳"),
                 ("25", "２５～２９歳"), ("30", "３０～３４歳"), ("35", "３５～３９歳"), ("40", "４０～４４歳"),
                 ("45", "４５～４９歳"), ("50", "５０歳以上"), ("不詳", "不詳")]
HH = ["総数", "農家世帯", "自営業者世帯", "常用勤労者世帯Ⅰ", "常用勤労者世帯Ⅱ", "その他の世帯", "無職の世帯", "不詳"]
def hh_label(s):
    s = s.replace(" ", "")
    if "総数" in s: return "総数"
    if "農家" in s: return "農家世帯"
    if "自営" in s: return "自営業者世帯"
    if "常用" in s:
        return "常用勤労者世帯Ⅱ" if re.search(r"(Ⅱ|II|ll|Il|lI|11|2)\s*\)?$", s.rstrip(")）")) or s.count("I")>=2 else "常用勤労者世帯Ⅰ"
    if "その他" in s: return "その他の世帯"
    if "無職" in s: return "無職の世帯"
    if "不詳" in s: return "不詳"
    return None
out = ["第4表 出生順位"]
for group, header in ((pages_a, "総数 第1子 第2子 第3子"), (pages_b, "第4子 第5子以上 不詳")):
    for pi, p in enumerate(group):
        out.append("第4表 出生順位"); out.append(header); block = 0
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if re.match(r"^[\(（]", ln) and re.search(r"[\)）]$", ln):
                continue  # 世帯ラベルはOCRで崩れるため使わず、位置（各ページ4ブロック）で決める
            tok = ln.replace("。", " ").replace("|", " ").split()
            if not tok: continue
            age = None
            for pre, lab in AGE_BY_PREFIX:
                if tok[0].startswith(pre): age = lab; break
            if age is None: continue
            nums = [t for t in tok[1:] if re.fullmatch(r"[0-9.,]+|[ー\-—–‐]+", t)]
            if not re.search(r"[0-9]", " ".join(tok[1:])):
                # 数字を1つも含まない行は全セル「－」（OCRで記号が崩れる）。0 で埋め、
                # 年齢計=総数 の検算で取りこぼしがないことを保証する。
                nums = ["-"] * (12 if "第1子" in header else 9)
            # 年齢ラベルが「2529歳」のように数字を吸った場合も先頭トークンは捨てる
            if age == "総数":
                out.append(f"（ {HH[pi * 4 + block]} ）"); block += 1
            out.append(" ".join([age] + nums))
print("\n".join(out))
