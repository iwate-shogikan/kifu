# -*- coding: utf-8 -*-
"""
generate_index_with_search.py
- kifu_list.json から、検索UI付き index.html を生成
- フィルタ: タイトル / 対局者名 / 分類(dir)
- リンク形式: viewer.html?kifu=<file>&kifudir=<dir>
"""

import json
from pathlib import Path
from datetime import datetime

DATA_JSON = Path("data/kifu_list.json")
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

        # 表示用フォールバック
        if not title:
            title = "（無題）"
        if not players:
            # 先手/後手の別フィールドがあれば結合（想定拡張）
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

def build_html(items):
    # 分類セレクトの選択肢
    def unique_dirs(items):
        seen = set(); out = []
        for it in items:
            d = it["dir"] or ""
            if d not in seen:
                seen.add(d); out.append(d)
        return out

    dir_options = ['<option value="">（すべて）</option>'] + [
        f'<option value="{d}">{d or "（未分類）"}</option>' for d in unique_dirs(items)
    ]

    # 1行表示（kifuサイトの書式に寄せる）
    def line(it):
        href = f'viewer.html?kifu={it["file"]}&kifudir={it["dir"]}'
        date_disp = it["date"]
        try:
            date_disp = datetime.strptime(it["date"], "%Y-%m-%d").strftime("%Y-%m-%d")
        except Exception:
            pass
        # 分類はページ遷移ではなく「ワンクリックで分類フィルタ」が便利
        dir_txt = it["dir"] or "（未分類）"
        dir_link = (f"<a href='#' class='dirlink' data-dir='{it['dir']}'>{dir_txt}</a>")

        return f'''
<li class="item"
    data-title="{it["title"]}"
    data-players="{it["players"]}"
    data-dir="{it["dir"]}">
  <span class="date">{date_disp}</span>
  <span class="title">【<a href="{href}">{it["title"]}</a>】</span>
  <span class="players">{it["players"]}</span>
  <span class="dir"></span>
</li>
'''

    list_html = "\n".join(line(it) for it in items)

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>棋譜一覧（最新棋譜から表示）</title>
<style>
  :root{{--fg:#111;--muted:#666;--line:#eee}}
  body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,'Noto Sans JP','Hiragino Kaku Gothic ProN','Yu Gothic UI',sans-serif;margin:16px;color:var(--fg)}}
  h1{{margin:0 0 8px 0;font-size:20px}}
  .sub{{color:var(--muted);margin:0 0 12px 0;font-size:14px}}
  .toolbar{{display:grid;grid-template-columns:1fr 1fr 220px 110px;gap:8px;margin:12px 0 8px;align-items:end}}
  .toolbar label{{font-size:12px;color:#555}}
  input,select,button{{width:100%;padding:8px;border:1px solid #ddd;border-radius:8px;background:#fff}}
  .count{{font-size:12px;color:#444;text-align:right;margin-bottom:6px}}
  ul.list{{list-style:none;margin:0;padding:0}}
  .item{{display:flex;flex-wrap:wrap;gap:8px 12px;padding:10px 0;border-bottom:1px solid var(--line)}}
  .item .date{{min-width:105px}}
  .item .title a{{text-decoration:none}}
  .item .dir a{{text-decoration:none}}
  .dirlink{{cursor:pointer}}
  @media (max-width:720px){{.toolbar{{grid-template-columns:1fr}} .item .players{{flex-basis:100%}}}}
</style>
</head>
<body>
  <h1>棋譜一覧（最新棋譜から表示）</h1>
  <p class="sub">柿木棋譜ビューアで再生されます　日付　棋戦名　対局者　分類</p>

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

  <ul id="list" class="list">
    {list_html}
  </ul>

<script>
(function(){{
  const $ = s=>document.querySelector(s);
  const $$ = s=>Array.from(document.querySelectorAll(s));
  const qTitle=$("#q-title"), qPlayers=$("#q-players"), qDir=$("#q-dir");
  const btnClear=$("#btn-clear"), rows=$$("#list .item"), count=$("#count");

  function norm(s){{return (s||"").toLowerCase().replace(/\\s+/g,"").normalize('NFKC');}}

  function apply(){{
    const t=norm(qTitle.value), p=norm(qPlayers.value), d=qDir.value;
    let shown=0;
    rows.forEach(li=>{{
      const okTitle=!t||norm(li.dataset.title).includes(t);
      const okPlayers=!p||norm(li.dataset.players).includes(p);
      const okDir=!d||li.dataset.dir===d;
      const on= okTitle && okPlayers && okDir;
      li.style.display = on ? "" : "none";
      if(on) shown++;
    }});
    count.textContent=shown;
  }}

  function clearAll(){{ qTitle.value=""; qPlayers.value=""; qDir.value=""; apply(); }}

  qTitle.addEventListener("input", apply);
  qPlayers.addEventListener("input", apply);
  qDir.addEventListener("change", apply);
  btnClear.addEventListener("click", clearAll);

  // 分類文字のクリックでその分類に絞り込み
  document.addEventListener("click", (e)=>{{
    const a = e.target.closest(".dirlink");
    if(!a) return;
    e.preventDefault();
    const val = a.getAttribute("data-dir")||"";
    qDir.value = val;
    qDir.dispatchEvent(new Event("change"));
  }});

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

    # 日付降順に並べ替え（あれば）
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
