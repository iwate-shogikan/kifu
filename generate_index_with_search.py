# -*- coding: utf-8 -*-
"""
generate_index_with_search.py
- data/kifu_list.json から、検索UI付き index.html を生成
- フィルタ: タイトル / 対局者名 / 分類(dir)
- リンク形式: viewer.html?kifu=<file>&kifudir=<dir>
- レイアウトは最初版（テーブル）。CSSのみ落ち着いた配色・小さめフォントへ調整。
"""

import json
from pathlib import Path
from datetime import datetime

DATA_JSON = Path("data/kifu_list.json")   # ← data配下を参照
OUTPUT_HTML = Path("index.html")

# 柔軟にキーを拾うためのヘルパ
def pick(d, *candidates, default=""):
    for k in candidates:
        if k in d and d[k] is not None:
            return d[k]
    return default

def load_items(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = []
    for r in raw:
        date = pick(r, "date", "日付")
        title = pick(r, "title", "棋戦", "棋戦名")
        players = pick(r, "players", "対局者", "先手後手", "先手_vs_後手")
        dir_ = pick(r, "dir", "分類", "folder", "kifudir")
        file_ = pick(r, "file", "filename", "kifu", "name")

        if not title:
            title = "（無題）"
        if not players:
            sente = pick(r, "sente", "先手")
            gote  = pick(r, "gote", "後手")
            players = f"{sente} vs {gote}" if (sente or gote) else ""

        items.append({
            "date": date,
            "title": title,
            "players": players,
            "dir": dir_,
            "file": file_
        })
    return items

def unique_dirs(items):
    s = []
    seen = set()
    for it in items:
        d = it["dir"] or ""
        if d not in seen:
            seen.add(d); s.append(d)
    return s

def build_html(items):
    # 分類セレクトの選択肢
    dir_options = ['<option value="">（すべて）</option>'] + [
        f'<option value="{d}">{d or "（未分類）"}</option>' for d in unique_dirs(items)
    ]

    # 行テンプレ（データ属性はフィルタ用）
    def row(it):
        href = f'viewer.html?kifu={it["file"]}&kifudir={it["dir"]}'
        date_disp = it["date"]
        try:
            # YYYY-MM-DD -> YYYY/MM/DD 表示
            date_disp = datetime.strptime(it["date"], "%Y-%m-%d").strftime("%Y/%m/%d")
        except Exception:
            pass

        return f'''
        <tr class="row"
            data-title="{it["title"]}"
            data-players="{it["players"]}"
            data-dir="{it["dir"]}">
          <td class="col-date">{date_disp}</td>
          <td class="col-title"><a href="{href}">{it["title"]}</a></td>
          <td class="col-players">{it["players"]}</td>
          <td class="col-dir">{it["dir"] or "（未分類）"}</td>
        </tr>
        '''

    rows_html = "\n".join(row(it) for it in items)

    # ===== CSSを落ち着いた配色・小さめフォントに調整 =====
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>棋譜一覧（検索フィルタ付き）</title>
<style>
  :root {{
    --bg: #f5f6f7;
    --card: #ffffff;
    --text: #222;
    --muted: #6b7280;
    --line: #e5e7eb;
    --link: #1f6feb;
    --input-border: #d1d5db;
    --shadow: 0 8px 24px rgba(0,0,0,0.08);
    --radius: 10px;
    --fz: 14px;          /* ベース文字サイズ */
    --fz-small: 12px;    /* 補助文字 */
  }}

  html, body {{
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Noto Sans JP", "Hiragino Kaku Gothic ProN", "Yu Gothic UI", sans-serif;
    font-size: var(--fz);
    line-height: 1.6;
    margin: 0;
    padding: 0;
  }}

  .container {{
    max-width: 1100px;
    margin: 20px auto 40px;
    padding: 0 14px;
  }}

  .panel {{
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 14px;
  }}

  h1 {{
    font-size: 18px;
    margin: 0 0 4px 0;
  }}

  .sub {{
    margin: 0 0 10px 0;
    color: var(--muted);
    font-size: var(--fz-small);
  }}

  .toolbar {{
    display: grid;
    grid-template-columns: 1fr 1fr 220px 120px;
    gap: 8px;
    align-items: end;
    margin: 10px 0 8px;
  }}

  .toolbar label {{
    display: block;
    font-size: var(--fz-small);
    color: var(--muted);
    margin-bottom: 4px;
  }}

  input, select, button {{
    width: 100%;
    padding: 8px 10px;
    border: 1px solid var(--input-border);
    border-radius: 8px;
    background: #fff;
    font-size: var(--fz);
  }}

  button {{
    cursor: pointer;
  }}

  .count {{
    font-size: var(--fz-small);
    color: #444;
    text-align: right;
    margin: 6px 2px 10px;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    overflow: hidden;
  }}

  thead th {{
    background: #fafafa;
    color: #111;
    font-weight: 600;
    font-size: var(--fz);
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid var(--line);
    position: sticky;
    top: 0;
    z-index: 1;
  }}

  tbody td {{
    padding: 9px 12px;
    border-bottom: 1px solid var(--line);
    vertical-align: top;
  }}

  tbody tr:hover td {{
    background: #fcfcfc;
  }}

  a {{
    color: var(--link);
    text-decoration: none;
  }}
  a:hover {{ text-decoration: underline; }}

  /* カラム幅の微調整 */
  .col-date {{ width: 110px; white-space: nowrap; }}
  .col-players {{ width: 300px; }}
  .col-dir {{ width: 140px; white-space: nowrap; }}

  @media (max-width: 720px) {{
    .toolbar {{ grid-template-columns: 1fr; }}
    .col-players {{ width: auto; }}
    .col-dir {{ width: auto; }}
  }}
</style>
</head>
<body>
  <div class="container">
    <div class="panel">
      <h1>棋譜一覧</h1>
      <p class="sub">日付／タイトル／対局者／分類 で一覧。上部の検索UIで絞り込みできます。</p>

      <div class="toolbar">
        <div>
          <label>タイトルで検索</label>
          <input id="q-title" type="text" placeholder="例：王座戦・順位戦など">
        </div>
        <div>
          <label>対局者名で検索</label>
          <input id="q-players" type="text" placeholder="例：佐藤 / 渡辺（部分一致OK）">
        </div>
        <div>
          <label>分類を選択</label>
          <select id="q-dir">
            {''.join(dir_options)}
          </select>
        </div>
        <div>
          <button id="btn-clear">条件クリア</button>
        </div>
      </div>

      <div class="count"><span id="count"></span> 件表示</div>

      <table id="tbl">
        <thead>
          <tr>
            <th>日付</th>
            <th>タイトル</th>
            <th>対局者</th>
            <th>分類</th>
          </tr>
        </thead>
        <tbody id="tbody">
          {rows_html}
        </tbody>
      </table>
    </div>
  </div>

<script>
(function() {{
  const $ = (s)=>document.querySelector(s);
  const $$ = (s)=>Array.from(document.querySelectorAll(s));

  const qTitle = $("#q-title");
  const qPlayers = $("#q-players");
  const qDir = $("#q-dir");
  const btnClear = $("#btn-clear");
  const rows = $$("#tbody .row");
  const count = $("#count");

  function norm(s) {{
    return (s||"").toLowerCase().replace(/\\s+/g,"").normalize('NFKC');
  }}

  function apply() {{
    const t = norm(qTitle.value);
    const p = norm(qPlayers.value);
    const d = qDir.value;

    let shown = 0;
    rows.forEach(tr => {{
      const title = norm(tr.dataset.title);
      const players = norm(tr.dataset.players);
      const dir = tr.dataset.dir;

      const okTitle = !t || title.includes(t);
      const okPlayers = !p || players.includes(p);
      const okDir = !d || dir === d;

      const visible = okTitle && okPlayers && okDir;
      tr.style.display = visible ? "" : "none";
      if (visible) shown++;
    }});
    count.textContent = shown;
  }}

  function clearAll(){{
    qTitle.value = "";
    qPlayers.value = "";
    qDir.value = "";
    apply();
  }}

  // 入力イベント
  qTitle.addEventListener("input", apply);
  qPlayers.addEventListener("input", apply);
  qDir.addEventListener("change", apply);
  btnClear.addEventListener("click", clearAll);

  // 初期表示
  apply();
}})();
</script>
</body>
</html>
"""

def main():
    if not DATA_JSON.exists():
        raise SystemExit(f"ERROR: {DATA_JSON} が見つかりません。")
    items = load_items(DATA_JSON)

    # 日付降順に並べ替え（可能なものだけ優先）
    def date_key(it):
        try:
            return datetime.strptime(it["date"], "%Y-%m-%d")
        except Exception:
            return datetime.min
    items.sort(key=date_key, reverse=True)

    html = build_html(items)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"OK: {OUTPUT_HTML} を生成しました。（{len(items)}件）")

if __name__ == "__main__":
    main()
