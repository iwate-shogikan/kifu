import json
from pathlib import Path
from datetime import datetime

base_dir = Path.cwd()
data_dir = base_dir / "data"
output_json = data_dir / "kifu_list.json"

kifu_entries = []
encodings = ["utf-8", "shift_jis", "cp932"]

for subdir in sorted(data_dir.iterdir()):
    if subdir.is_dir():
        dir_name = subdir.name
        for kif_file in sorted(subdir.glob("*.kif")):
            fname = kif_file.name
            name_wo_ext = fname[:-4]
            # 日付抽出
            try:
                date_part = fname[:8]
                parsed_date = datetime.strptime(date_part, "%Y%m%d").strftime("%Y-%m-%d")
            except Exception:
                parsed_date = ""

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

            entry = {
                "file": fname,
                "title": title,
                "players": players,
                "date": parsed_date,
                "dir": dir_name
            }
            kifu_entries.append(entry)

# JSON 出力
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(kifu_entries, f, ensure_ascii=False, indent=2)

print(f"✅ {output_json} に {len(kifu_entries)} 件出力しました。" )  
