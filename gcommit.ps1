param([string]$Message = "update")

# リポジトリ直下へ
Set-Location (git rev-parse --show-toplevel)

# 1) 追跡/未追跡を一括ステージ（.gitignore尊重、フック自体は除外）
git add -A -- ':!githooks/**'

# 2) 生成（kifu_list.json / index.html）
python generate_kifu_list.py
python generate_index_with_search.py

# 3) 生成物を保険でステージ
git add -- data/kifu_list.json index.html

# 4) 何もステージされていなければ終了
if (git diff --cached --quiet) {
  Write-Warning "No staged changes. Abort."
  exit 1
}

# 5) pre-commit をスキップしてコミット
git commit --no-verify -m $Message

# 6) そのまま GitHub（追跡先）へ push
Write-Host "[INFO] pushing to remote..." -ForegroundColor Cyan
git push

