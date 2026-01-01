# Firefox Headless Game Tester

Firefoxヘッドレスモードでゲームの動作確認を行うツール。

## 機能

- ゲームのindex.htmlをヘッドレスブラウザで読み込み
- ゲームの初期化確認（Canvas要素、ゲームオブジェクト）
- 画面タップ（クリック）による起動テスト
- JavaScriptエラーの検出
- スクリーンショットの保存

## 必要条件

- Python 3.8+
- Firefox
- geckodriver
- selenium

## インストール

```bash
pip install selenium
```

## 設定

`config.json`に`geckodriver_path`を設定：

```json
{
  "geckodriver_path": "/home/gemini/firefox/geckodriver",
  ...
}
```

## 使用方法

### 基本的な使い方

```bash
python firefoxtester.py /path/to/public/index.html
```

### オプション

```bash
# geckodriverパスを直接指定
python firefoxtester.py index.html --geckodriver /path/to/geckodriver

# ルートディレクトリを指定（html_pathとoutputの基準パス）
python firefoxtester.py public/index.html --root_dir workspace/my-game

# ポート番号を変更
python firefoxtester.py index.html --port 9999

# 結果をJSONファイルに出力
python firefoxtester.py index.html --output results.json
```

### 例

```bash
# 直接パス指定
python tools/firefoxtester/firefoxtester.py workspace/crystal-caverns/public/index.html

# root_dirを使用（dotter.pyと同様の使い方）
python tools/firefoxtester/firefoxtester.py public/index.html --root_dir workspace/crystal-caverns
```

## 3段階ゲーム検証テスト（v0.3新機能）

ゲームが正常に動作しているか、3つのスクリーンショットを比較して自動検証します。

### 検証ステップ

1. **ステップ1: タイトル画面の確認**
   - ゲームを読み込んでタイトル画面をキャプチャ
   - 画面が正常にレンダリングされているか確認

2. **ステップ2: ゲーム開始の確認**
   - 画面中央をタップしてゲーム開始
   - タイトル画面との画像比較（≥20%の差分で成功）

3. **ステップ3: ゲーム操作の確認**
   - 仮想コントローラー（矢印キーなど）で操作
   - ゲーム開始画面との画像比較（≥20%の差分で成功）

### 使用方法

```bash
# デフォルトキーで検証テスト（UP,DOWN,LEFT,RIGHT）
python firefoxtester.py public/index.html --verification

# カスタムキーで検証テスト
python firefoxtester.py public/index.html --verification --control_keys 'Z,X,C,V'

# 結果をJSONに出力
python firefoxtester.py public/index.html --verification --output verification_result.json

# 出力ディレクトリを指定
python firefoxtester.py public/index.html --verification --output_dir ./test_results
```

### 出力ファイル

```
work/
├── 01_title_screen.png      # タイトル画面
├── 02_game_started.png      # ゲーム開始画面
└── 03_game_playing.png      # ゲーム実行画面
```

### 検証成功条件

- ✓ ゲーム初期化成功
- ✓ タイトル → ゲーム開始：20%以上のピクセル変化
- ✓ ゲーム開始 → ゲーム実行：20%以上のピクセル変化
- ✓ JavaScriptコンソールにエラーなし

## スクリプトモード

コマンド列を指定してゲーム操作を自動化できます。

### スクリプトオプション

```bash
# JSON文字列でスクリプトを直接指定
python firefoxtester.py index.html --script '[{"cmd": "tap"}, {"cmd": "sleep", "ms": 1000}, {"cmd": "keypress", "key": "D"}]'

# JSONファイルからスクリプトを読み込み
python firefoxtester.py index.html --script_file test_script.json
```

### 利用可能なコマンド

| コマンド | パラメータ | 説明 |
|---------|-----------|------|
| `tap` | `x`, `y` (optional) | 座標をタップ。座標省略時はキャンバス中央 |
| `keypress` | `key` | キーを押す（A-Z, 0-9, SPACE, ENTER, UP, DOWN, LEFT, RIGHT, ESCAPE等） |
| `sleep` | `ms` | 指定ミリ秒待機 |
| `swipe` | `x1`, `y1`, `x2`, `y2`, `duration` | スワイプ操作（ドラッグ） |
| `screenshot` | `filename` | スクリーンショットを保存 |
| `get_state` | なし | 現在のゲーム状態を取得 |

### スクリプト例

```json
[
    {"cmd": "tap"},
    {"cmd": "sleep", "ms": 1000},
    {"cmd": "keypress", "key": "D"},
    {"cmd": "keypress", "key": "D"},
    {"cmd": "swipe", "x1": 100, "y1": 200, "x2": 300, "y2": 200, "duration": 500},
    {"cmd": "sleep", "ms": 500},
    {"cmd": "screenshot", "filename": "test_result.png"},
    {"cmd": "get_state"}
]
```

## 出力

テスト結果には以下が含まれます：

- **initialization**: ゲームの初期化状態
- **post_tap_state**: タップ後のゲーム状態
- **errors**: 検出されたJavaScriptエラー
- **screenshot**: スクリーンショットのパス

## 終了コード

- `0`: すべてのチェックに成功
- `1`: エラーが検出された
