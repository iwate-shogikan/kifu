# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path
from datetime import datetime

# ディレクトリ設定
base_dir = Path.cwd()
data_dir = base_dir / "data"
output_json = data_dir / "kifu_list.json"

# 既存構成そのまま
kifu_entries = []
encodings = ["utf-8", "shift_jis", "cp932"]

# -----------------------------
# 棋戦名から日付推定のためのユーティリティ
# -----------------------------
# 例: 2010.6.9 / 2010/6/9 / 2010-6-9 / 2010年6月9日
_Y4_PATTERN = re.compile(r'(?<!\d)(\d{4})[./\-年](\d{1,2})[./\-月](\d{1,2})(?:日)?(?!\d)')
# 例: 23.9.28 / 05/4/3 / 02-12-01 / 23年9月28日（※二桁年 → 平成年と解釈）
_R2_PATTERN = re.compile(r'(?<!\d)(\d{2})[./\-年](\d{1,2})[./\-月](\d{1,2})(?:日)?(?!\d)')
# 明示的な「平成」表記にも対応（例: 平成23年9月28日 / 平成23.9.28）
_HEISEI_LABEL_PATTERN = re.compile(r'平成\s*(\d{1,2})[./\-年](\d{1,2})[./\-月](\d{1,2})(?:日)?')

def _pad(y, m, d) -> str:
    """YYYY-MM-DD 文字列に整形"""
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

def _heisei_to_gregorian(h: int) -> int:
    """平成年 → 西暦（平成1年=1989 → 1988+h）"""
    return 1988 + int(h)

def parse_date_from_title(title: str) -> str | None:
    """
    棋戦名に含まれる日付を推定し、YYYY-MM-DD で返す。
      1) 4桁年を優先: 2010.6.9 → 2010-06-09
      2) 二桁年は「平成」として解釈: 23.9.28 → 平成23年 → 西暦(1988+23)=2011-09-28
      3) 「平成23年9月28日」等の明示表記にも対応
    """
    if not title:
        return None
    t = str(title)

    # 4桁西暦を優先
    m = _Y4_PATTERN.search(t)
    if m:
        y, mm, dd = m.groups()
        return _pad(y, mm, dd)

    # 明示「平成」表記
    m = _HEISEI_LABEL_PATTERN.search(t)
    if m:
        hy, mm, dd = m.groups()
        return _pad(_heisei_to_gregorian(hy), mm, dd)

    # 先頭が二桁年 → 平成として読む
    m = _R2_PATTERN.search(t)
    if m:
        hy, mm, dd = m.groups()
        return _pad(_heisei_to_gregorian(hy), mm, dd)

    return None

# -----------------------------
# メイン処理
# -----------------------------
for subdir in sorted(data_dir.iterdir()):
    if subdir.is_dir():
        dir_name = subdir.name
        for kif_file in sorted(subdir.glob("*.kif")):
            fname = kif_file.name
            name_wo_ext = fname[:-4]

            # 1) ファイル名先頭8桁 (YYYYMMDD) から日付抽出
            try:
                date_part = fname[:8]
                parsed_date = datetime.strptime(date_part, "%Y%m%d").strftime("%Y-%m-%d")
            except Exception:
                parsed_date = ""

            # 2) KIF本文から棋戦/先手/後手を取得（既存ロジック）
            sente, gote, title = "", "", ""
            for enc in encodings:
                try:
                    with open(kif_file, "r", encoding=enc) as f:
                        for line in f:
                            if not title and line.startswith("棋戦："):
                                title = line.strip().split("：", 1)[1]
                            elif line.startswith("先手："):
                                sente = line.strip().split("：", 1)[1]
                            elif line.startswith("後手："):
                                gote = line.strip().split("：", 1)[1]
                            if title and sente and gote:
                                break
                    break
                except Exception:
                    continue

            if not title:
                title = name_wo_ext

            players = f"{sente} vs {gote}" if sente and gote else ""

            # 3) 左端日付が空なら、棋戦名から補完（上記の平成/西暦ルール）
            date_str = parsed_date
            if not date_str or date_str in ("", "----/--/--", "--", "不明"):
                guessed = parse_date_from_title(title)
                if guessed:
                    date_str = guessed

            entry = {
                "file": fname,
                "title": title,
                "players": players,
                "date": date_str,   # JSONは YYYY-MM-DD で統一
                "dir": dir_name
            }
            kifu_entries.append(entry)

# JSON 出力
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(kifu_entries, f, ensure_ascii=False, indent=2)

print(f"✅ {output_json} に {len(kifu_entries)} 件出力しました。")
