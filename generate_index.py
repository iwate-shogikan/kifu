import json
from pathlib import Path
from collections import defaultdict

base_dir = Path.cwd()
json_file = base_dir / "data" / "kifu_list.json"
output_index = base_dir / "index.html"
output_dir = base_dir / "data"

# JSON読み込み
with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# 日付で降順ソート
data.sort(key=lambda x: x["date"], reverse=True)

# 分類別に分ける
grouped = defaultdict(list)
for item in data:
    grouped[item["dir"]].append(item)

# 共通HTMLテンプレート
def make_html(rows_html: str, title: str, show_back: bool = False) -> str:
    back_link = '<p><a href="../index.html">← 一覧に戻る</a></p>' if show_back else ''
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP&display=swap" rel="stylesheet">
<style>
  body {{
    background-color: #f0f0d8;
    font-family: 'Noto Sans JP', sans-serif;
    color: #2a2a2a;
    margin: 0;
    padding: 0;
    font-size: 16px;
  }}
  main {{
    max-width: 900px;
    width: 900px;
    margin: 2rem auto;
    padding: 2rem;
    background-color: #fff;
    border: 1px solid #ccc;
    border-radius: 4px;
    box-shadow: 0 0 8px rgba(0,0,0,0.05);
    box-sizing: border-box;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
  }}
  th, td {{
    border: 1px solid #ccc;
    padding: 0.8rem;
    text-align: left;
  }}
  th {{
    background-color: #e2e2c5;
  }}
  tr:nth-child(even) {{
    background-color: #f9f9f9;
  }}
  a.kifu-link {{
    color: #006633;
    text-decoration: none;
    font-weight: bold;
  }}
  a.kifu-link:hover {{
    text-decoration: underline;
  }}

  @media (max-width: 660px) {{
    body {{ font-size: 1rem; }}
    main {{
      width: 600px;
      margin: 0.5rem auto;
      padding: 1rem;
    }}
    #content-wrapper {{
      transform: scale(1.00);
      transform-origin: top center;
    }}
    #content-wrapper select,
    #content-wrapper p {{
      font-size: 1rem;
    }}
    header {{
      width: 600px;
      margin: 0 auto;
      font-size: 1.4rem;
      padding: 1.2rem 0;
    }}
    h1 {{
      font-size: 1.2rem;
    }}
  }}

  @media (min-width: 661px) and (max-width: 1200px) {{
    body {{ font-size: 16px; }}
    main {{
      width: 660px;
      margin: 16px auto;
      padding: 16px;
    }}
    #content-wrapper {{
      transform: scale(1.00);
      transform-origin: top center;
    }}
    #content-wrapper select {{
      font-size: 16px;
    }}
  }}
</style>
</head>
<body>
<main>
  <div id="content-wrapper">
    <h2>{title}</h2>
    柿木棋譜ビューアで再生されます
    {back_link}
    <table>
      <thead>
        <tr>
          <th>日付</th>
          <th>棋戦名</th>
          <th>対局者</th>
          {'' if show_back else '<th>分類</th>'}
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>
</main>
</body>
</html>
"""


# 行生成(分岐あり) 
def build_row(item, include_dir_link=True):
    viewer_path = "viewer.html" if include_dir_link else "../viewer.html"
    link = f"{viewer_path}?kifu={item['file']}&kifudir={item['dir']}"
    dir_cell = (
        f'<td><a class="kifu-link" href="data/{item["dir"]}.html">{item["dir"]}</a></td>'
        if include_dir_link else ''
    )
    return f"""
      <tr>
        <td>{item['date'] or '----/--/--'}</td>
        <td><a class="kifu-link" href="{link}">{item['title']}</a></td>
        <td>{item['players']}</td>
        {dir_cell}
      </tr>
    """

# index.html（全体）
all_rows = [build_row(item, include_dir_link=True) for item in data]
html_index = make_html("".join(all_rows), "棋譜一覧（最新棋譜から表示）")
output_index.write_text(html_index, encoding="utf-8")
print(f"✅ index.html を出力しました。")

# 各分類ページ（分類名.html）
for dir_name, items in grouped.items():
    rows = [build_row(item, include_dir_link=False) for item in items]
    html = make_html("".join(rows), f"分類：{dir_name}", show_back=True)
    output_file = output_dir / f"{dir_name}.html"
    output_file.write_text(html, encoding="utf-8")
    print(f"✅ {output_file.name} を data フォルダに出力しました。")
