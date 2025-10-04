# -*- coding: utf-8 -*-
"""
generate_index_with_search.py
- data/kifu_list.json から検索UI付き index.html を生成
- フィルタ: タイトル / 対局者名 / 分類(dir)
- リンク: viewer.html?kifu=<file>&kifudir=<dir>
- 既存の拡張:
  * 分類セルクリックで即フィルタ
  * 検索条件をURLハッシュ #t=...&p=...&d=... に保存/復元
  * マッチ箇所ハイライト (<mark>)
  * 名前の正規化強化（さん/君/先生/プロ等の除去、かな⇄カナ、段位/称号/括弧の除去、末尾「五段」など連結も除去）
  * スペース区切り AND 検索
  * 列ヘッダクリックでソート（日時/タイトル/分類、昇降切替）  ※初期は「日時：降順」
  * 件数ゼロ時に「該当する項目がありません」行を表示
- 追加：
  * 「条件クリア」押下でソートも既定（日時降順）にリセット
  * 棋譜リンククリック時に現在の検索ハッシュ(#t,#p,#d)を viewer.html に ret= として引き渡す
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
    """対局者名から検索ノイズ（括弧/段位/称号/敬称など）を除去"""
    if not s:
        return ""
    t = str(s).replace("　", " ").strip()
    t = re.sub(r"[（(][^）)]*[）)]", "", t)                    # 括弧内
    t = re.sub(rf"^(?:{TITLE_RE})+", "", t)                   # 先頭連結
    t = re.sub(rf"(?:{TITLE_RE})+$", "", t)                   # 末尾連結
    t = re.sub(r"(?:十|九|八|七|六|五|四|三|二|初)?段$", "", t)  # 末尾 段
    t = re.sub(r"(?:\d+)?級$", "", t)                         # 末尾 級
    t = re.sub(rf"(?:(?<=\s)|^){TITLE_RE}(?=\s|$)", " ", t)   # 独立トークン
    t = re.sub(r"(さん|君|くん|ちゃん|様|氏|殿|先生|師匠|プロ)$", "", t)  # 敬称
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

def date_to_sortkey(s: str) -> str:
    """'YYYY-MM-DD' → 'YYYYMMDD' / 不明は '00000000'"""
    if not s:
        return "00000000"
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.strftime("%Y%m%d")
    except Exception:
        return "00000000"

def render_players_links(players_text: str) -> str:
    """'A vs B' / 'A 対 B' をそれぞれクリック可能リンクに（data-player はクリーン名）"""
    if not players_text:
        return ""
    s = players_text.replace("　", " ").strip()
    for token in ["ＶＳ", "ｖｓ", "VS", "Vs", "vS", "－", "—", "ー"]:
        s = s.replace(token, " vs ")
    parts = [p.strip() for p in s.split(" vs ") if p.strip()]
    if len(parts) == 2:
        a, b = parts
        a_clean = clean_player_name(a); b_clean = clean_player_name(b)
        return (f'<a class="plink" href="#" data-raw="{a}" data-player="{a_clean}">{a}</a> '
                f'vs <a class="plink" href="#" data-raw="{b}" data-player="{b_clean}">{b}</a>')
    if "対" in s:
        p2 = [p.strip() for p in s.split("対") if p.strip()]
        if len(p2) == 2:
            a, b = p2
            a_clean = clean_player_name(a); b_clean = clean_player_name(b)
            return (f'<a class="plink" href="#" data-raw="{a}" data-player="{a_clean}">{a}</a> '
                    f'対 <a class="plink" href="#" data-raw="{b}" data-player="{b_clean}">{b}</a>')
    return (f'<a class="plink" href="#" data-raw="{players_text}" '
            f'data-player="{clean_player_name(players_text)}">{players_text}</a>')

def build_html(items):
    # 分類セレクト
    dir_options_html = '<option value="">（すべて）</option>' + ''.join(
        f'<option value="{d}">{d or "（未分類）"}</option>' for d in unique_dirs(items)
    )

    # 行HTML
    rows = []
    for it in items:
        href = f'viewer.html?kifu={it["file"]}&kifudir={it["dir"]}'
        date_disp = it["date"]
        try:
            date_disp = datetime.strptime(it["date"], "%Y-%m-%d").strftime("%Y/%m/%d")
        except Exception:
            pass
        players_html = render_players_links(it["players"])
        dir_txt = it["dir"] or "（未分類）"
        dir_link = f'<a href="#" class="dirlink" data-dir="{it["dir"] or ""}">{dir_txt}</a>'
        sortkey = date_to_sortkey(it["date"])
        rows.append(
            f'<tr class="row" data-title="{it["title"]}" data-players="{it["players"]}" '
            f'data-dir="{it["dir"]}" data-date="{sortkey}">'
            f'<td>{date_disp or "----/--/--"}</td>'
            f'<td><a class="kifu-link" href="{href}" data-raw="{it["title"]}">{it["title"]}</a></td>'
            f'<td>{players_html}</td>'
            f'<td>{dir_link}</td>'
            f'</tr>'
        )
    rows_html = "\n".join(rows)

    HTML_TMPL = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>棋譜一覧（検索フィルタ付き）</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP&display=swap" rel="stylesheet">
<style>
  body {
    background-color: #f0f0d8;
    font-family: 'Noto Sans JP', sans-serif;
    color: #2a2a2a;
    margin: 0; padding: 0; font-size: 16px;
  }
  main {
    max-width: 900px; width: 900px; margin: 2rem auto; padding: 2rem;
    background-color: #fff; border: 1px solid #ccc; border-radius: 4px;
    box-shadow: 0 0 8px rgba(0,0,0,0.05); box-sizing: border-box;
  }
  #content-wrapper { transform-origin: top center; }
  h1, h2 { margin: 0 0 0.6rem 0; }
  .lead { margin: 0 0 1rem 0; color:#555; font-size: 0.95rem; }

  .toolbar {
    display: grid; grid-template-columns: 1fr 1fr 220px 120px;
    gap: 8px; align-items: end; margin: 0.5rem 0;
  }
  .toolbar label {
    display: block; font-size: 0.9rem; color: #555; margin-bottom: 4px;
  }
  .toolbar input, .toolbar select, .toolbar button {
    width: 100%; padding: 0.5rem 0.6rem; border: 1px solid #ccc; border-radius: 4px;
    background: #fff; font-size: 16px; box-sizing: border-box;
  }
  .toolbar button { cursor: pointer; background:#fff; }
  .count { text-align:right; color:#444; font-size:0.95rem; margin: 0.4rem 0; }

  table { width: 100%; border-collapse: collapse; margin-top: 0.6rem; }
  th, td { border: 1px solid #ccc; padding: 0.8rem; text-align: left; vertical-align: top; }
  th { background-color: #e2e2c5; position: sticky; top: 0; z-index: 1; }
  tr:nth-child(even) { background-color: #f9f9f9; }

  a.kifu-link, a.plink, a.dirlink { color: #006633; text-decoration: none; }
  a.kifu-link { font-weight: bold; }
  a.kifu-link:hover, a.plink:hover, a.dirlink:hover { text-decoration: underline; }
  .plink, .dirlink { cursor: pointer; }

  mark { background: #ffef76; padding: 0 .15em; border-radius: 2px; }

  /* ソートUI */
  th.sortable { cursor: pointer; user-select: none; }
  .sort-label { display:inline-flex; align-items:center; gap:.25em; }
  .sort-indicator { width: 1em; display:inline-block; text-align:center; color:#333; }

  /* 該当なし */
  tr.nohit td { text-align:center; color:#666; font-style:italic; }

  @media (max-width: 660px) {
    body { font-size: 1rem; }
    main { width: 600px; margin: 0.5rem auto; padding: 1rem; }
    #content-wrapper select, #content-wrapper p { font-size: 1rem; }
    header { width: 600px; margin: 0 auto; font-size: 1.4rem; padding: 1.2rem 0; }
    h1, h2 { font-size: 1.2rem; }
    .toolbar { grid-template-columns: 1fr; }
  }
  @media (min-width: 661px) and (max-width: 1200px) {
    body { font-size: 16px; }
    main { width: 660px; margin: 16px auto; padding: 16px; }
    #content-wrapper select { font-size: 16px; }
  }
</style>
</head>
<body>
<main>
  <div id="content-wrapper">
    <h2>岩手日報掲載棋譜・岩手県関連棋譜</h2>
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
          __DIR_OPTIONS__
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
          <th class="sortable" data-sort="date"><span class="sort-label">日付 <span class="sort-indicator" id="ind-date"></span></span></th>
          <th class="sortable" data-sort="title"><span class="sort-label">棋戦名 <span class="sort-indicator" id="ind-title"></span></span></th>
          <th>対局者</th>
          <th class="sortable" data-sort="dir"><span class="sort-label">分類 <span class="sort-indicator" id="ind-dir"></span></span></th>
        </tr>
      </thead>
      <tbody id="tbody">
        __ROWS__
        <tr id="nohit" class="nohit" style="display:none;"><td colspan="4">該当する項目がありません</td></tr>
      </tbody>
    </table>
  </div>
</main>

<script>
// === 検索 & ソート ユーティリティ ===
(function(){
  const $  = (s)=>document.querySelector(s);
  const $$ = (s)=>Array.from(document.querySelectorAll(s));

  const qTitle   = $("#q-title");
  const qPlayers = $("#q-players");
  const qDir     = $("#q-dir");
  const btnClear = $("#btn-clear");
  const tbody    = $("#tbody");
  const count    = $("#count");
  const nohitRow = $("#nohit");

  // 基本正規化
  function nfkcLower(s){ return (s||"").normalize('NFKC').toLowerCase(); }
  function toKatakana(s){ return (s||"").replace(/[ぁ-ゖ]/g, ch => String.fromCharCode(ch.charCodeAt(0) + 0x60)); }

  function normTitle(s){ return nfkcLower(s); }

  function cleanNameForSearch(s){
    if(!s) return "";
    let t = nfkcLower(s).replace(/\u3000/g," ").trim();
    t = t.replace(/[（(][^）)]*[）)]/g, " ");  // 括弧
    const tokens = ["十段","九段","八段","七段","六段","五段","四段","三段","二段","初段",
                    "名人","竜王","王位","王座","王将","棋王","叡王","棋聖","女流","アマ"];
    tokens.forEach(w=>{ t = t.replace(new RegExp(w,"g"), " "); });
    t = t.replace(/(?:十|九|八|七|六|五|四|三|二|初)?段$/g, " ");
    t = t.replace(/(?:\d+)?級$/g, " ");
    t = t.replace(/(さん|君|くん|ちゃん|様|氏|殿|先生|師匠|プロ)$/g, " ");
    t = t.replace(/\s+/g, " ").trim();
    return t;
  }
  function normPlayers(s){ return toKatakana(cleanNameForSearch(s)).replace(/\s+/g,""); }

  function tokensFromTitleInput(s){
    s = nfkcLower(s).replace(/\u3000/g," ").trim();
    if(!s) return [];
    return s.split(/\s+/).filter(Boolean);
  }
  function tokensFromPlayersInput(s){
    s = cleanNameForSearch(s);
    s = toKatakana(s).replace(/\u3000/g," ").trim();
    if(!s) return [];
    return s.split(/\s+/).filter(Boolean).map(x=>x.replace(/\s+/g,""));
  }

  // ハイライト
  function highlightText(rawText, tokens){
    if(!rawText || !tokens.length) return rawText;
    let html = rawText;
    const uniq = Array.from(new Set(tokens.filter(Boolean))).sort((a,b)=>b.length-a.length);
    for(const tk of uniq){
      const escaped = tk.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const re = new RegExp(escaped, "gi");
      html = html.replace(re, m=>`<mark>${m}</mark>`);
    }
    return html;
  }

  // ハッシュ保存/復元
  function updateHash(){
    const t = encodeURIComponent(qTitle.value||"");
    const p = encodeURIComponent(qPlayers.value||"");
    const d = encodeURIComponent(qDir.value||"");
    const newHash = `#t=${t}&p=${p}&d=${d}`;
    const url = location.pathname + location.search + newHash;
    history.replaceState(null, "", url);
  }
  function parseHash(){
    const h = (location.hash||"").replace(/^#/,"");
    const params = new URLSearchParams(h);
    return {
      t: params.get("t")? decodeURIComponent(params.get("t")) : "",
      p: params.get("p")? decodeURIComponent(params.get("p")) : "",
      d: params.get("d")? decodeURIComponent(params.get("d")) : ""
    };
  }

  // ソート状態
  let sortKey = "date";   // "date" | "title" | "dir"
  let sortAsc = false;    // 初期は日付 降順（最新が上）
  const indDate  = $("#ind-date");
  const indTitle = $("#ind-title");
  const indDir   = $("#ind-dir");

  function setSortIndicator(){
    indDate.textContent  = "";
    indTitle.textContent = "";
    indDir.textContent   = "";
    const arrow = sortAsc ? "▲" : "▼";
    if(sortKey === "date")  indDate.textContent  = arrow;
    if(sortKey === "title") indTitle.textContent = arrow;
    if(sortKey === "dir")   indDir.textContent   = arrow;
  }

  function rowValue(row, key){
    if(key === "date"){
      const v = row.dataset.date || "00000000";
      return parseInt(v, 10) || 0;
    }
    if(key === "title"){
      return normTitle(row.dataset.title || "");
    }
    if(key === "dir"){
      return normTitle(row.dataset.dir || "");
    }
    return "";
  }

  function sortRows(){
    const rows = Array.from(tbody.querySelectorAll(".row"));
    rows.sort((a,b)=>{
      const va = rowValue(a, sortKey);
      const vb = rowValue(b, sortKey);
      if(sortKey === "date"){
        return sortAsc ? (va - vb) : (vb - va);
      }else{
        if(va < vb) return sortAsc ? -1 : 1;
        if(va > vb) return sortAsc ? 1 : -1;
        // tie-breaker: date desc
        const da = rowValue(a, "date"), db = rowValue(b, "date");
        return db - da;
      }
    });
    // 再配置
    for(const r of rows){ tbody.appendChild(r); }
    // nohit 行は常に末尾
    tbody.appendChild(nohitRow);
    setSortIndicator();
  }

  // メイン適用
  function apply({skipHashUpdate=false}={}){
    const rows = Array.from(tbody.querySelectorAll(".row"));
    const tTokens = tokensFromTitleInput(qTitle.value);
    const pTokens = tokensFromPlayersInput(qPlayers.value);
    const dirVal  = qDir.value;

    let shown = 0;
    rows.forEach(tr=>{
      const titleNorm   = normTitle(tr.dataset.title);
      const playersNorm = normPlayers(tr.dataset.players);
      const dir         = tr.dataset.dir || "";

      const okTitle   = tTokens.every(tok => titleNorm.includes(tok));
      const okPlayers = pTokens.every(tok => playersNorm.includes(tok));
      const okDir     = !dirVal || dir === dirVal;

      const visible = okTitle && okPlayers && okDir;
      tr.style.display = visible ? "" : "none";
      if(visible) shown++;

      // --- ハイライト ---
      const tAnchor = tr.children[1].querySelector("a.kifu-link");
      const tRaw = tAnchor.getAttribute("data-raw") || tAnchor.textContent;
      tAnchor.innerHTML = highlightText(tRaw, qTitle.value.trim()? tTokens: []);
      const pCell = tr.children[2];
      for(const a of pCell.querySelectorAll("a.plink")){
        const pRaw = a.getAttribute("data-raw") || a.textContent;
        a.innerHTML = highlightText(pRaw, qPlayers.value.trim()? (qPlayers.value.normalize('NFKC').split(/\s+/).filter(Boolean)) : []);
      }
    });
    count.textContent = shown;
    nohitRow.style.display = shown ? "none" : "";
    if(!skipHashUpdate) updateHash();
  }

  function clearAll(){
    // 入力条件をクリア
    qTitle.value = ""; qPlayers.value = ""; qDir.value = "";
    // ★ ソートを既定（日時降順）にリセット
    sortKey = "date";
    sortAsc = false;
    sortRows();
    // 再適用
    apply();
  }

  // イベント
  qTitle.addEventListener("input", ()=>apply());
  qPlayers.addEventListener("input", ()=>apply());
  qDir.addEventListener("change", ()=>apply());
  btnClear.addEventListener("click", clearAll);

  // 分類セルクリックで即フィルタ
  document.addEventListener("click", (e)=>{
    const a = e.target.closest(".dirlink");
    if(!a) return;
    e.preventDefault();
    const val = a.getAttribute("data-dir") || "";
    qDir.value = val;
    apply();
  });

  // 対局者名クリックでクリーン名を適用
  document.addEventListener("click", (e)=>{
    const a = e.target.closest(".plink");
    if(!a) return;
    e.preventDefault();
    const name = a.getAttribute("data-player") || "";
    qPlayers.value = name;
    apply();
    try{ qPlayers.focus(); qPlayers.select(); }catch(_){}
  });

// ★ 棋譜リンククリック時：#t,#p,#d のいずれかが入っている時だけ ret= を付ける
document.addEventListener("click", (e)=>{
  const a = e.target.closest("a.kifu-link");
  if(!a) return;
  e.preventDefault();

  const h = location.hash || "";
  const params = new URLSearchParams(h.replace(/^#/,""));
  const t = params.get("t") || "";
  const p = params.get("p") || "";
  const d = params.get("d") || "";
  const hasAny = (t !== "" || p !== "" || d !== "");

  const ret = hasAny ? "&ret=" + encodeURIComponent(`#t=${t}&p=${p}&d=${d}`) : "";
  location.href = a.href + ret;
});

  // ヘッダクリックでソート
  document.querySelectorAll("th.sortable").forEach(th=>{
    th.addEventListener("click", ()=>{
      const key = th.getAttribute("data-sort");
      if(sortKey === key){
        sortAsc = !sortAsc;
      }else{
        sortKey = key;
        // 新キーの初期向き：dateは降順、その他は昇順に
        sortAsc = (key !== "date");
      }
      sortRows();
    });
  });

  // 初期化: ハッシュ復元 → ソート → 適用
  (function init(){
    const {t,p,d} = parseHash();
    if(t) qTitle.value = t;
    if(p) qPlayers.value = p;
    if(d) qDir.value = d;
    sortKey = "date"; sortAsc = false;
    sortRows();                 // 初期は日付降順
    apply({skipHashUpdate:true});
    window.addEventListener("hashchange", ()=>{
      const {t,p,d} = parseHash();
      qTitle.value = t || "";
      qPlayers.value = p || "";
      qDir.value = d || "";
      apply({skipHashUpdate:true});
    });
  })();
})();
</script>
</body>
</html>
"""
    html = (HTML_TMPL
            .replace("__DIR_OPTIONS__", dir_options_html)
            .replace("__ROWS__", rows_html))
    return html

def main():
    if not DATA_JSON.exists():
        raise SystemExit(f"ERROR: {DATA_JSON} が見つかりません。")
    items = load_items(DATA_JSON)

    # 生成時は日付降順にしておく（初期表示を安定化）
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
     