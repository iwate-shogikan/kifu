# -*- coding: utf-8 -*-
"""
generate_index_with_search.py
- data/kifu_list.json から検索UI付き index.html を生成
- フィルタ: タイトル / 対局者名 / 分類(dir)
- リンク: viewer.html?kifu=<file>&kifudir=<dir>
- 追加:
  * 分類セルクリックで即フィルタ
  * 検索条件をURLハッシュ #t=...&p=...&d=... に保存/復元
  * マッチ箇所ハイライト (<mark>)
  * 名前の正規化強化（さん/君/先生/プロ等の除去、かな⇄カナ、段位/称号/括弧の除去、末尾「五段」など連結も除去）
  * スペース区切り AND 検索
"""

import json
import re
from pathlib import Path
from datetime import datetime

DATA_JSON = Path("data/kifu_list.json")
OUTPUT_HTML = Path("index.html")

def pick(d, *candidates, default=""):
    for k in candidates:
        if k in d and d[k] is not None:
            return d[k]
    return default

TITLE_TOKENS = [
    "十段","九段","八段","七段","六段","五段","四段","三段","二段","初段",
    "名人","竜王","王位","王座","王将","棋王","叡王","棋聖","女流","アマ"
]
TITLE_RE = "(?:" + "|".join(map(re.escape, TITLE_TOKENS)) + ")"

def clean_player_name(s: str) -> str:
    """
    検索用に対局者名からノイズ除去:
      - 括弧内（() / 全角（ ））削除
      - 段位/称号を削除（先頭/末尾に連結していてもOK）
      - 末尾の「段」「級」だけ残っているケースも削除
      - 空白正規化
    """
    if not s:
        return ""
    t = str(s).replace("　", " ").strip()
    # 括弧内
    t = re.sub(r"[（(][^）)]*[）)]", "", t)
    # 先頭側に連結している称号群
    t = re.sub(rf"^(?:{TITLE_RE})+", "", t)
    # 末尾側に連結している称号群
    t = re.sub(rf"(?:{TITLE_RE})+$", "", t)
    # 末尾の 段/級
    t = re.sub(r"(?:十|九|八|七|六|五|四|三|二|初)?段$", "", t)
    t = re.sub(r"(?:\d+)?級$", "", t)
    # 独立トークンの称号
    t = re.sub(rf"(?:(?<=\s)|^){TITLE_RE}(?=\s|$)", " ", t)
    # 敬称など
    t = re.sub(r"(さん|君|くん|ちゃん|様|氏|殿|先生|師匠|プロ)$", "", t)
    # 空白
    t = re.sub(r"\s+", " ", t).strip()
    return t

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
    'A vs B' / 'A 対 B' 検出し、それぞれクリック可能に。
    data-player: クリーン名 / data-raw: 表示テキスト
    """
    if not players_text:
        return ""
    s = players_text.replace("　", " ").strip()
    # ' vs ' に統一
    for token in ["ＶＳ", "ｖｓ", "VS", "Vs", "vS", "－", "—", "ー"]:
        s = s.replace(token, " vs ")
    parts = [p.strip() for p in s.split(" vs ") if p.strip()]
    if len(parts) == 2:
        a, b = parts
        a_clean = clean_player_name(a); b_clean = clean_player_name(b)
        return (f'<a class="plink" href="#" data-raw="{a}" data-player="{a_clean}">{a}</a> '
                f'vs <a class="plink" href="#" data-raw="{b}" data-player="{b_clean}">{b}</a>')
    # 和文「対」
    if "対" in s:
        p2 = [p.strip() for p in s.split("対") if p.strip()]
        if len(p2) == 2:
            a, b = p2
            a_clean = clean_player_name(a); b_clean = clean_player_name(b)
            return (f'<a class="plink" href="#" data-raw="{a}" data-player="{a_clean}">{a}</a> '
                    f'対 <a class="plink" href="#" data-raw="{b}" data-player="{b_clean}">{b}</a>')
    # 1リンク
    return (f'<a class="plink" href="#" data-raw="{players_text}" '
            f'data-player="{clean_player_name(players_text)}">{players_text}</a>')

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
        dir_txt = it["dir"] or "（未分類）"
        dir_link = f'<a href="#" class="dirlink" data-dir="{it["dir"] or ""}">{dir_txt}</a>'

        return f"""
        <tr class="row"
            data-title="{it["title"]}"
            data-players="{it["players"]}"
            data-dir="{it["dir"]}">
          <td>{date_disp or '----/--/--'}</td>
          <td><a class="kifu-link" href="{href}" data-raw="{it["title"]}">{it["title"]}</a></td>
          <td>{players_html}</td>
          <td>{dir_link}</td>
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

  a.kifu-link, a.plink, a.dirlink {{ color: #006633; text-decoration: none; }}
  a.kifu-link {{ font-weight: bold; }}
  a.kifu-link:hover, a.plink:hover, a.dirlink:hover {{ text-decoration: underline; }}
  .plink, .dirlink {{ cursor: pointer; }}

  mark {{ background: #ffef76; padding: 0 .15em; border-radius: 2px; }}

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
        <input id="q-players" type="text" placeholder="例：佐藤 / 渡辺（部分一致・AND可）">
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
// === 検索ユーティリティ ===
(function(){{
  const $  = (s)=>document.querySelector(s);
  const $$ = (s)=>Array.from(document.querySelectorAll(s));

  const qTitle   = $("#q-title");
  const qPlayers = $("#q-players");
  const qDir     = $("#q-dir");
  const btnClear = $("#btn-clear");
  const rows     = $$("#tbody .row");
  const count    = $("#count");

  // 基本正規化: NFKC + 小文字 + 全空白を半角に
  function nfkcLower(s){{ return (s||"").normalize('NFKC').toLowerCase(); }}
  // カタカナ化（ひらがな→カタカナ）
  function toKatakana(s){{ return (s||"").replace(/[ぁ-ゖ]/g, ch => String.fromCharCode(ch.charCodeAt(0) + 0x60)); }}
  // タイトル用の正規化
  function normTitle(s){{ return nfkcLower(s); }}
  // 敬称/称号、括弧などの除去（JS側）
  function cleanNameForSearch(s){{ 
    if(!s) return ""; 
    let t = nfkcLower(s).replace(/\\u3000/g," ").trim(); // 全角空白→半角
    // 括弧内
    t = t.replace(/[（(][^）)]*[）)]/g, " ");
    // 段位/称号
    const tokens = ["十段","九段","八段","七段","六段","五段","四段","三段","二段","初段",
                    "名人","竜王","王位","王座","王将","棋王","叡王","棋聖","女流","アマ"];
    tokens.forEach(w=>{{ t = t.replace(new RegExp(w,"g"), " "); }});
    // 末尾の 段/級
    t = t.replace(/(?:十|九|八|七|六|五|四|三|二|初)?段$/g, " ");
    t = t.replace(/(?:\\d+)?級$/g, " ");
    // 敬称等
    t = t.replace(/(さん|君|くん|ちゃん|様|氏|殿|先生|師匠|プロ)$/g, " ");
    // 空白縮約
    t = t.replace(/\\s+/g, " ").trim();
    return t;
  }}
  // プレイヤー名比較用の正規化（かな⇄カナ対応 + 空白除去）
  function normPlayers(s){{ return toKatakana(cleanNameForSearch(s)).replace(/\\s+/g,""); }}
  // クエリをトークン配列（AND）に
  function tokensFromTitleInput(s){{ 
    s = nfkcLower(s).replace(/\\u3000/g," ").trim();
    if(!s) return [];
    return s.split(/\\s+/).filter(Boolean);
  }}
  function tokensFromPlayersInput(s){{ 
    s = cleanNameForSearch(s);
    s = toKatakana(s).replace(/\\u3000/g," ").trim();
    if(!s) return [];
    return s.split(/\\s+/).filter(Boolean).map(x=>x.replace(/\\s+/g,""));
  }}

  // ハイライト: 指定トークン（配列）を <mark> で囲む
  function highlightText(rawText, tokens){{ 
    if(!rawText || !tokens.length) return rawText;
    let html = rawText;
    const uniq = Array.from(new Set(tokens.filter(Boolean))).sort((a,b)=>b.length-a.length);
    for(const tk of uniq){{ 
      const escaped = tk.replace(/[.*+?^${{}}()|[\\]\\\\]/g, "\\\\$&");
      const re = new RegExp(escaped, "gi");
      html = html.replace(re, m=>`<mark>${{m}}</mark>`);
    }}
    return html;
  }}

  // ハッシュ保存/復元
  function updateHash(){{ 
    const t = encodeURIComponent(qTitle.value||"");
    const p = encodeURIComponent(qPlayers.value||"");
    const d = encodeURIComponent(qDir.value||"");
    const newHash = `#t=${{t}}&p=${{p}}&d=${{d}}`;
    const url = location.pathname + location.search + newHash;
    history.replaceState(null, "", url);
  }}
  function parseHash(){{ 
    const h = (location.hash||"").replace(/^#/,"");
    const params = new URLSearchParams(h);
    return {{
      t: params.get("t")? decodeURIComponent(params.get("t")) : "",
      p: params.get("p")? decodeURIComponent(params.get("p")) : "",
      d: params.get("d")? decodeURIComponent(params.get("d")) : ""
    }};
  }}

  // メイン適用
  function apply({{skipHashUpdate=false}}={{}}){{ 
    const tTokens = tokensFromTitleInput(qTitle.value);        // AND
    const pTokens = tokensFromPlayersInput(qPlayers.value);    // AND（カナ化済）

    let shown = 0;
    rows.forEach(tr=>{{ 
      const titleNorm   = normTitle(tr.dataset.title);
      const playersNorm = normPlayers(tr.dataset.players);
      const dir         = tr.dataset.dir || "";

      const okTitle   = tTokens.every(tok => titleNorm.includes(tok));
      const okPlayers = pTokens.every(tok => playersNorm.includes(tok));
      const okDir     = !qDir.value || dir === qDir.value;

      const visible = okTitle && okPlayers && okDir;
      tr.style.display = visible ? "" : "none";
      if(visible) shown++;

      // --- ハイライト ---
      // タイトル
      const tAnchor = tr.children[1].querySelector("a.kifu-link");
      const tRaw = tAnchor.getAttribute("data-raw") || tAnchor.textContent;
      tAnchor.innerHTML = highlightText(tRaw, qTitle.value.trim()? tTokens: []);
      // 対局者（それぞれの a.plink）
      const pCell = tr.children[2];
      for(const a of pCell.querySelectorAll("a.plink")){{ 
        const pRaw = a.getAttribute("data-raw") || a.textContent;
        a.innerHTML = highlightText(pRaw, qPlayers.value.trim()? (qPlayers.value.normalize('NFKC').split(/\\s+/).filter(Boolean)) : []);
      }}
    }});
    count.textContent = shown;
    if(!skipHashUpdate) updateHash();
  }}

  function clearAll(){{ 
    qTitle.value = ""; qPlayers.value = ""; qDir.value = "";
    apply();
  }}

  qTitle.addEventListener("input", ()=>apply());
  qPlayers.addEventListener("input", ()=>apply());
  qDir.addEventListener("change", ()=>apply());
  btnClear.addEventListener("click", clearAll);

  // 分類セルクリックで即フィルタ
  document.addEventListener("click", (e)=>{{ 
    const a = e.target.closest(".dirlink");
    if(!a) return;
    e.preventDefault();
    const val = a.getAttribute("data-dir") || "";
    qDir.value = val;
    apply();
  }});

  // 対局者名クリックでクリーン名を適用
  document.addEventListener("click", (e)=>{{ 
    const a = e.target.closest(".plink");
    if(!a) return;
    e.preventDefault();
    const name = a.getAttribute("data-player") || "";
    qPlayers.value = name;
    apply();
    try{{ qPlayers.focus(); qPlayers.select(); }}catch(_){{
      /* noop */
    }}
  }});

  // 初期化: ハッシュ復元 → 適用
  (function init(){{ 
    const {{t,p,d}} = parseHash();
    if(t) qTitle.value = t;
    if(p) qPlayers.value = p;
    if(d) qDir.value = d;
    apply({{skipHashUpdate:true}});
    window.addEventListener("hashchange", ()=>{{ 
      const {{t,p,d}} = parseHash();
      qTitle.value = t || "";
      qPlayers.value = p || "";
      qDir.value = d || "";
      apply({{skipHashUpdate:true}});
    }});
  }})();
}})();
</script>
</body>
</html>
"""

def main():
    if not DATA_JSON.exists():
        raise SystemExit(f"ERROR: {DATA_JSON} が見つかりません。")
    items = load_items(DATA_JSON)

    # 日付降順
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
