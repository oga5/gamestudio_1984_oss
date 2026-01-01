# GameStudio 1984 OSS版
AI駆動型アーケードゲーム開発システム

## 概要
GameStudio 1984は、1984年のゲーム開発スタジオを現代に再現することを目的としたAIエージェントシステムです。
テキストプロンプトを入力するだけで、デザイン、プログラミング、グラフィック、サウンドの各エージェントが協調して動作し、プレイ可能なHTML5ゲームを生成します。

## 機能
- **マルチエージェントシステム**: Designer、Programmer、Graphic Artist、Sound Artist、Tester、Managerの6つのエージェントが協調してゲームを開発

## ツール
- **doteditor**: AIが生成したドット絵データをPNG画像に変換するツール
- **synthesizer**: 指定された周波数とエンベロープからWAV形式のサウンドを生成するツール
- **firefoxtester**: Firefoxブラウザを使用してゲームを自動実行し、動作検証を行うツール

## ゲームライブラリ (gamelib.js)
- **gamelib.js**: スプライト、タイルマップ、カメラ、衝突検出、パーティクル、サウンド管理など、ゲーム開発に必要な基本機能を提供するJavaScriptライブラリ

## 環境構築

### 必要条件

- Python 3.10以上
- Google AI API キー（Geminiモデル用）
- Firefox（テスト用、オプション）

### インストール手順

1. **リポジトリのクローン**

```bash
git clone <repository-url>
cd oss
```

2. **Python仮想環境の作成（推奨）**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows
```

3. **依存パッケージのインストール**

```bash
pip install langgraph google-generativeai Pillow numpy

# WebUI用（オプション）
pip install -r webui/requirements.txt
```

4. **API キーの設定**

環境変数に Google AI API キーを設定:

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

または、config.jsonで設定することも可能です。

5. **config.jsonの確認**

`config.json`を確認し、必要に応じてモデル設定やパスを調整してください。

## 使い方

### コマンドライン

```bash
# 基本的な使い方
python gamestudio_1984.py "シンプルなシューティングゲームを作成"

# プロジェクト名を指定
python gamestudio_1984.py "パズルゲームを作成" -p my_puzzle_game

# モデルを指定
python gamestudio_1984.py "アクションゲームを作成" -m gemini-2.5-flash-preview-09-2025
```

### WebUI（Web インターフェース）

1. WebUIサーバーを起動:

```bash
cd webui
python backend.py
```

2. ブラウザで `http://localhost:8087` にアクセス

3. ゲームのプロンプトを入力して「Start Agent」をクリック

4. リアルタイムでログを確認し、完了後はゲームをプレイ

## ディレクトリ構造

```
oss/
├── gamestudio_1984.py      # メインエントリーポイント
├── middleware.py           # ミドルウェア
├── workflow_engine.py      # ワークフローエンジン
├── asset_tracker.py        # アセット追跡
├── config.json             # 設定ファイル
├── system_prompt/          # システムプロンプト
│   ├── roles/              # ロール定義
│   │   ├── common.md
│   │   ├── designer.md
│   │   ├── programmer.md
│   │   ├── graphic_artist.md
│   │   ├── sound_artist.md
│   │   ├── tester.md
│   │   └── manager.md
│   └── tasks/              # タスク定義
│       ├── designer/
│       ├── programmer/
│       ├── graphic_artist/
│       ├── sound_artist/
│       ├── tester/
│       └── manager/
├── templates/              # ゲームテンプレート
│   ├── game_template/
│   └── game_template_advanced/
├── tools/                  # ツール群
│   ├── doteditor/          # ドット絵生成ツール
│   ├── synthesizer/        # サウンド生成ツール
│   ├── file_tools.py
│   └── permissions.py
├── webui/                  # WebUI
│   ├── backend.py
│   ├── requirements.txt
│   └── README.md
└── workspace/              # 生成されたゲームの出力先
```

## 生成されるゲームの構造

```
workspace/<project_name>/
├── public/
│   ├── index.html          # HTMLファイル
│   ├── style.css           # スタイルシート
│   ├── game.js             # ゲームロジック
│   ├── gamelib.js          # ゲームライブラリ
│   └── assets/
│       ├── images/         # PNG画像
│       └── sounds/         # WAVサウンド
├── work/
│   ├── design.json         # ゲームデザイン
│   ├── workflow.json       # ワークフロー状態
│   └── ...
└── logs/                   # 実行ログ
```

## トラブルシューティング

### API キーエラー

- 環境変数 `GOOGLE_API_KEY` が正しく設定されているか確認
- API キーに有効なクォータがあるか確認

### 依存パッケージのエラー

```bash
pip install --upgrade langgraph google-generativeai
```

### ゲームが表示されない
- workspace/<project>/public/index.html をブラウザで直接開く
- ブラウザのコンソールでエラーを確認

## ライセンス
Apache 2.0 License
