# TaskHub

Discord 用のタスク管理ボットです。

## 実行方法

### 1. 必要なもの

- **Python 3.12**
- **Discord ボットのトークン**（[Discord Developer Portal](https://discord.com/developers/applications) で作成）

### 2. Python 3.12 のインストール（未インストールの場合）

macOS で Homebrew を使う場合:

```bash
brew install python@3.12
```

インストール後、パスが通っていないときは次のように仮想環境を作成します。

```bash
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv   # Apple Silicon
# または
/usr/local/opt/python@3.12/bin/python3.12 -m venv .venv      # Intel Mac
```

### 3. 仮想環境の作成と依存関係のインストール

**必ずプロジェクトのフォルダ（TaskHub）に移動してから実行してください。**

```bash
cd /Users/natuki/Documents/Project/TaskHub

# 仮想環境を作成（まだない場合）
python3.12 -m venv .venv
# または上記で python3.12 が無い場合: パスを指定
# /opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv

# 仮想環境を有効化（有効化するとプロンプト先頭に (.venv) が出ます）
source .venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt
```

Windows の場合は `source .venv/bin/activate` の代わりに `.venv\Scripts\activate` を実行してください。

### 4. 環境変数の設定

### 3. 環境変数の設定

Discord のトークンを環境変数に設定します。

```bash
export DISCORD_TOKEN="あなたのボットトークン"
```

### 5. ボットの起動

プロジェクトのルート（TaskHub）で次を実行します。

```bash
python -m taskbot
```

または:

```bash
python -m taskbot.bot
```

起動に成功すると、コンソールに `Logged in as ボット名` と表示されます。Discord でボットをサーバーに追加し、タスク管理コマンドを利用できます。

## 締切入力

タスク追加/編集は2段階です。

1. フォームでタイトル・説明・優先度を入力
2. 次の画面で締切をプルダウン選択

締切選択の仕様:

- 日付: `1日後` から `7日後` まで（任意）
- 時: `00` から `23`（任意）
- 分: `00, 10, 20, 30, 40, 50`（任意）
- 日付を設定しない場合は締切なし
- 日付のみ設定した場合は `00:00` 扱い
