# -*- coding: utf-8 -*-
"""
generate_index_with_search.py
- data/kifu_list.json から検索UI付き index.html を生成
- フィルタ: タイトル / 対局者名 / 分類(dir)
- リンク: viewer.html?kifu=<file>&kifudir=<dir>
- CSSは従前indexのテイストに寄せる
- 追加: 対局者名をクリックすると、その名前で曖昧検索を即適用
"""

import json
from pathlib import Path
from datetime import datetime

DATA_JSON = Path("data/kifu_list.json")
OUTPUT_HTML = Path("index.html")

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
    seen = set(); out = []
    for it in items:
        d = it["dir"] or ""
        if d not in seen:
            seen.add(d); out.append(d)
    return out

def render_players_links(players_text: str) -> str:
    """
    対局者セル用： 'A vs B' なら A / B をそれぞれクリック可能リンクに。
    区切り検出に失敗したら全文クリック可能にする。
    """
    if not players_text:
        return ""
    s = players_text.replace("　", " ").strip()
    # よくある表記を ' vs ' に正規化
    for token in ["ＶＳ", "ｖｓ", "VS", "Vs", "vS", "－", "—", "ー"]:
        s = s.replace(token, " vs ")
    parts = [p.strip() for p in s.split(" vs ") if p.strip()]
    if len(parts) == 2:
        a, b = parts
        return (f'<a class="plink" href="#" data-player="{a}">{a}</a> '
                f'vs <a class="plink" href="#" data-player="{b}">{b}</a>')
    # 和文「対」を試す
    if "対" in s:
        p2 = [p.strip() for p in s.split("対") if p.strip()]
        if len(p2) == 2:
            a, b = p2
            return (f'<a class="plink" href="#" data-player="{a}">{a}</a> '
                    f'対 <a class="plink" href="#" data-player="{b}">{b}</a>')
    # 分割不可：全文を1リンク
    return f'<a class="plink" href="#" data-player="{players_text}">{players_text}</a>'

def build_html(items):
    dir_options = ['<option value="">（すべて）</option>'] + [
        f'<option value="{d}">{d or "（未分類）"}</option>' for d in unique_dirs(items)
    ]

    def row(it):
        href = f'viewer.html?kifu={it["file"]}&kifudir={it["dir"]}'
        date_disp = it["date"]
        try:
            date_disp = datetime.strptime(it["date"], "%Y-%m-%d").strftime("%Y/%m/%d")
        except Exception:
            pass
        players_html = render_players_links(it["players"])

        return f"""
        <tr class="row"
            data-title="{it["title"]}"
            data-players="{it["players"]}"
            data-dir="{it["dir"]}">
          <td>{date_disp or '----/--/--'}</td>
          <td><a class="kifu-link" href="{href}">{it["title"]}</a></td>
          <td>{players_html}</td>
          <td>{it["dir"] or "（未分類）"}</td>
        </tr>
        """

    rows_html = "\n".join(row(it) for it in items)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>棋譜一覧（検索フィルタ付き）</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP&display=swap" rel="stylesheet">
<style>
  body {{
    background-color: #f0f0d8;
    font-family: 'Noto Sans JP', sans-serif;
    color: #2a2a2a;
    margin: 0; padding: 0; font-size: 16px;
  }}
  main {{
    max-width: 900px; width: 900px; margin: 2rem auto; padding: 2rem;
    background-color: #fff; border: 1px solid #ccc; border-radius: 4px;
    box-shadow: 0 0 8px rgba(0,0,0,0.05); box-sizing: border-box;
  }}
  #content-wrapper {{ transform-origin: top center; }}
  h1, h2 {{ margin: 0 0 0.6rem 0; }}
  .lead {{ margin: 0 0 1rem 0; color:#555; font-size: 0.95rem; }}

  .toolbar {{
    display: grid; grid-template-columns: 1fr 1fr 220px 120px;
    gap: 8px; align-items: end; margin: 0.5rem 0;
  }}
  .toolbar label {{
    display: block; font-size: 0.9rem; color: #555; margin-bottom: 4px;
  }}
  .toolbar input, .toolbar select, .toolbar button {{
    width: 100%; padding: 0.5rem 0.6rem; border: 1px solid #ccc; border-radius: 4px;
    background: #fff; font-size: 16px; box-sizing: border-box;
  }}
  .toolbar button {{ cursor: pointer; background:#fff; }}
  .count {{ text-align:right; color:#444; font-size:0.95rem; margin: 0.4rem 0; }}

  table {{ width: 100%; border-collapse: collapse; margin-top: 0.6rem; }}
  th, td {{ border: 1px solid #ccc; padding: 0.8rem; text-align: left; vertical-align: top; }}
  th {{ background-color: #e2e2c5; position: sticky; top: 0; z-index: 1; }}
  tr:nth-child(even) {{ background-color: #f9f9f9; }}

  a.kifu-link {{ color: #006633; text-decoration: none; font-weight: bold; }}
  a.kifu-link:hover {{ text-decoration: underline; }}
  a.plink {{ color: #006633; text-decoration: none; }}
  a.plink:hover {{ text-decoration: underline; }}
  .plink {{ cursor: pointer; }}
  @media (max-width: 660px) {{
    body {{ font-size: 1rem; }}
    main {{ width: 600px; margin: 0.5rem auto; padding: 1rem; }}
    #content-wrapper select, #content-wrapper p {{ font-size: 1rem; }}
    header {{ width: 600px; margin: 0 auto; font-size: 1.4rem; padding: 1.2rem 0; }}
    h1, h2 {{ font-size: 1.2rem; }}
    .toolbar {{ grid-template-columns: 1fr; }}
  }}
  @media (min-width: 661px) and (max-width: 1200px) {{
    body {{ font-size: 16px; }}
    main {{ width: 660px; margin: 16px auto; padding: 16px; }}
    #content-wrapper select {{ font-size: 16px; }}
  }}
</style>
</head>
<body>
<main>
  <div id="content-wrapper">
    <h2>棋譜一覧（最新棋譜から表示）</h2>
    <p class="lead">柿木棋譜ビューアで再生されます</p>

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
          <th>棋戦名</th>
          <th>対局者</th>
          <th>分類</th>
        </tr>
      </thead>
      <tbody id="tbody">
        {rows_html}
      </tbody>
    </table>
  </div>
</main>

<script>
(function() {{
  const $  = (s)=>document.querySelector(s);
  const $$ = (s)=>Array.from(document.querySelectorAll(s));

  const qTitle   = $("#q-title");
  const qPlayers = $("#q-players");
  const qDir     = $("#q-dir");
  const btnClear = $("#btn-clear");
  const rows     = $$("#tbody .row");
  const count    = $("#count");

  function norm(s) {{
    return (s||"").toLowerCase().replace(/\\s+/g,"").normalize('NFKC');
  }}

  function apply() {{
    const t = norm(qTitle.value);
    const p = norm(qPlayers.value);
    const d = qDir.value;
    let shown = 0;

    rows.forEach(tr => {{
      const title   = norm(tr.dataset.title);
      const players = norm(tr.dataset.players);
      const dir     = tr.dataset.dir;

      const okTitle   = !t || title.includes(t);
      const okPlayers = !p || players.includes(p);
      const okDir     = !d || dir === d;

      const visible = okTitle && okPlayers && okDir;
      tr.style.display = visible ? "" : "none";
      if (visible) shown++;
    }});
    count.textContent = shown;
  }}

  function clearAll() {{
    qTitle.value = "";
    qPlayers.value = "";
    qDir.value = "";
    apply();
  }}

  qTitle.addEventListener("input", apply);
  qPlayers.addEventListener("input", apply);
  qDir.addEventListener("change", apply);
  btnClear.addEventListener("click", clearAll);

  // ★ 追加：対局者名クリックで曖昧検索を即適用
  document.addEventListener("click", (e) => {{
    const a = e.target.closest(".plink");
    if (!a) return;
    e.preventDefault();
    const name = a.getAttribute("data-player") || "";
    qPlayers.value = name;   // 入力欄に反映
    apply();                 // 同じロジックでフィルタ
    try {{ qPlayers.focus(); qPlayers.select(); }} catch(_) {{}}
  }});

  apply(); // 初期表示
}})();
</script>
</body>
</html>
"""

def main():
    if not DATA_JSON.exists():
        raise SystemExit(f"ERROR: {DATA_JSON} が見つかりません。")
    items = load_items(DATA_JSON)

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
