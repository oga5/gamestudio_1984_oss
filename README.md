# GameStudio 1984 OSS版
AI駆動型アーケードゲーム開発システム

## 概要
GameStudio 1984は、1984年のゲーム開発スタジオを現代に再現することを目的としたAIエージェントシステムです。
テキストプロンプトを入力するだけで、デザイン、プログラミング、グラフィック、サウンドの各エージェントが協調して動作し、プレイ可能なHTML5ゲームを生成します。

## 機能
- **マルチエージェントシステム**: Designer、Programmer、Graphic Artist、Sound Artist、Tester、Managerの6つのエージェントが協調してゲームを開発
- **アセットファースト設計**: グラフィック・サウンドアセットを先に生成し、プログラミングフェーズで確実に利用可能にするワークフロー
- **マルチモデル対応**: ロールごとに異なるLLMモデルを指定可能（Gemini、OpenAI互換モデル / LiteLLMプロキシ経由）
- **ワークフロー再開**: 中断したワークフローを途中から再開可能
- **自動テスト**: Firefoxヘッドレスブラウザによる自動動作検証と修正ループ

## ツール

### 画像生成
- **generate_image (doteditor)**: JSONピクセルパターン定義からPNG画像を生成するドット絵ツール。RLEエンコーディング対応、最大32色。小さなスプライト（64x64以下）に最適
- **generate_svg**: SVGマークアップからPNG画像をレンダリングするツール。resvg_pyライブラリを使用。大きなグラフィック、ベクタースタイルのデザイン、複雑な形状に最適

### サウンド生成
- **generate_sfx**: プリセットベースの効果音生成ツール。explosion、laser、hit、powerup、coin、jump、gameover、victory、damage、select、blipの11種類に対応。intensity（low/medium/high）とpitch（low/mid/high）で調整可能
- **generate_sound (synthesizer)**: JSON定義による高度なサウンド生成ツール。ドラムトラック、オシレーター、FM合成、コードトラックをサポート。BGMや複雑な効果音に対応

### テスト・検証
- **test_game (firefoxtester)**: Firefoxヘッドレスブラウザを使用してゲームを自動実行し、スクリーンショット撮影・動作検証を行うツール
- **check_syntax**: JavaScript/HTML/Pythonの構文チェックツール
- **validate_asset / validate_all_assets**: PNG/WAVファイルの整合性検証ツール

### ファイル操作
- **read_file / write_file / file_edit / replace_file**: ファイルの読み書き・編集
- **inspect_image / inspect_audio**: 画像・音声ファイルのメタデータ取得
- **mv_file / copy_file / copy_dir**: ファイル・ディレクトリ操作
- **get_json_item / edit_json_item**: JSONファイルのセレクタベース読み書き

## ゲームライブラリ (gamelib.js)
- **gamelib.js**: スプライト、タイルマップ、カメラ、衝突検出、パーティクル、サウンド管理など、ゲーム開発に必要な基本機能を提供するJavaScriptライブラリ

## 環境構築

### 必要条件

- Python 3.10以上
- Google AI API キー（Geminiモデル用）、またはLiteLLMプロキシ経由でOpenAI互換API
- Firefox + geckodriver（テスト用、オプション）

(*)APIキーを秘匿するため、LiteLLM経由の実行を推奨

### インストール手順

1. **リポジトリのクローン**

```bash
git clone <repository-url>
cd gamestudio_1984_oss
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
pip install -r requirements.txt
```

4. **API キーの設定**

環境変数に Google AI API キーを設定:

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

または、`config.json`の`api_base`でLiteLLMプロキシ等のOpenAI互換エンドポイントを指定することも可能です。

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
python gamestudio_1984.py "アクションゲームを作成" -m gemini-2.5-flash

# ロールごとにモデルを指定
python gamestudio_1984.py "RPGを作成" --programmer-model gemini-2.5-pro --designer-model gemini-2.5-flash

# 推論モードを有効化
python gamestudio_1984.py "複雑なゲームを作成" --reasoning

# 特定ロールのみ推論モードを有効化
python gamestudio_1984.py "ゲームを作成" --programmer-reasoning
```

### WebUI（Web インターフェース）

1. WebUIサーバーを起動:

```bash
cd webui
python backend.py
```

2. ブラウザで `http://localhost:8089` にアクセス

3. ゲームのプロンプトを入力して「Start Agent」をクリック

4. リアルタイムでログを確認し、完了後はゲームをプレイ

## ワークフロー

ゲーム生成は以下のフェーズで進行します:

1. **デザインフェーズ** — Designerがゲームコンセプト・アセット仕様を作成
2. **アセットフェーズ** — Graphic Artistが画像を、Sound Artistがサウンドを個別に生成
3. **実装フェーズ** — Programmerがgame.jsを実装
4. **テストフェーズ** — TesterがFirefoxで自動テストを実行
5. **修正ループ** — テスト失敗時、Programmerが修正（最大3回）

## ディレクトリ構造

```
gamestudio_1984_oss/
├── gamestudio_1984.py      # メインエントリーポイント
├── middleware.py           # ミドルウェア（ロギング、レート制限）
├── workflow_engine.py      # ワークフローエンジン
├── asset_tracker.py        # アセットライフサイクル追跡
├── config.json             # 設定ファイル
├── requirements.txt        # Python依存パッケージ
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
│   ├── game_template_advanced/
│   └── design_schema_enhanced.json
├── tools/                  # ツール群
│   ├── asset_tools.py      # アセット生成（doteditor, svg, sfx, synthesizer）
│   ├── asset_validator.py  # アセット検証
│   ├── file_tools.py       # ファイル操作定義
│   ├── file_tools_impl.py  # ファイル操作実装
│   ├── json_tools.py       # JSON操作
│   ├── test_tools.py       # テストツール
│   ├── permissions.py      # ファイル権限管理
│   ├── doteditor/          # ドット絵生成エンジン
│   ├── synthesizer/        # サウンド合成エンジン（FM合成, SFXジェネレータ）
│   ├── firefoxtester/      # Firefoxテストランナー
│   └── utils/              # JSON操作ユーティリティ
├── webui/                  # WebUI
│   ├── backend.py
│   └── requirements.txt
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
│   ├── design.json         # ゲームデザイン仕様
│   ├── image_asset.json    # 画像アセット仕様
│   ├── sound_asset.json    # サウンドアセット仕様
│   ├── workflow.json       # ワークフロー状態
│   ├── sprite/             # スプライトJSONパターン
│   ├── svg/                # SVGソースコード
│   └── test/               # テスト結果（001/, 002/, ...）
└── logs/                   # 実行ログ（JSONL形式）
```

## トラブルシューティング

### API キーエラー

- 環境変数 `GOOGLE_API_KEY` が正しく設定されているか確認
- API キーに有効なクォータがあるか確認
- LiteLLMプロキシ使用時は`config.json`の`api_base`を確認

### 依存パッケージのエラー

```bash
pip install -r requirements.txt
```

### ゲームが表示されない
- workspace/<project>/public/index.html をブラウザで直接開く
- ブラウザのコンソールでエラーを確認

## ライセンス
Apache 2.0 License
