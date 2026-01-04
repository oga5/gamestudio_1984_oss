# GameStudio 1984 OSS WebUI

GameStudio 1984 OSS版のWebインターフェース

## 機能

- **リアルタイムログストリーミング**: SSE (Server-Sent Events) によるリアルタイムログ表示
- **バックグラウンド実行**: ブラウザを閉じてもエージェントは実行継続
- **アセット表示**: 生成された画像・サウンドをログ内にインライン表示
- **スクリーンショット表示**: テスターが撮影したスクリーンショットをインライン表示
- **プロセス制御**: 実行中のエージェントを停止可能
- **ワークスペース管理**: 生成されたゲームの一覧表示・プレイ
- **アセットライブラリ**: 再利用可能なアセットの管理

## インストール

```bash
cd webui
pip install -r requirements.txt
```

## 使い方

### サーバー起動

```bash
cd webui
python backend.py
```

サーバーは `http://localhost:8089` で起動します。

### Webインターフェース

1. **Agent Execution タブ**
   - ゲームのプロンプトを入力
   - 「Start Agent」ボタンでエージェント実行開始
   - リアルタイムでログを確認
   - 生成されたアセットをログ内で確認
   - 「Stop Agent」ボタンで実行停止
   - 完了後、リンクからゲームをプレイ

2. **Workspaces タブ**
   - 生成されたゲームの一覧表示
   - クリックでゲームをプレイ
   - ログの確認
   - ワークスペースの削除

3. **Assets タブ**
   - アセットライブラリの管理
   - ワークスペースからアセットをライブラリに追加
   - ライブラリからアセットを削除

## 技術詳細

### アーキテクチャ

- **バックエンド**: FastAPI + uvicorn
- **フロントエンド**: Vanilla HTML/CSS/JavaScript + SSE
- **プロセス管理**: subprocess.Popen
- **状態管理**: state.json ファイル
- **ログストリーミング**: Server-Sent Events (SSE)

### API エンドポイント

- `GET /` - メインWebインターフェース
- `GET /api/status` - 現在の実行状態
- `POST /api/start` - エージェント実行開始
- `POST /api/stop` - エージェント停止
- `GET /api/logs` - ログ取得
- `GET /api/logs/stream` - SSEログストリーム
- `GET /api/workspaces` - ワークスペース一覧
- `GET /game/{workspace}` - ゲームの提供
- `DELETE /api/workspaces/{workspace}` - ワークスペース削除

### デザイン

1984年風のレトロターミナルスタイル:

- **カラー**: 黒背景に緑テキスト (#00ff00 on #000)
- **フォント**: 等幅フォント (Courier New)
- **エフェクト**: テキストシャドウ、グロー効果

## ログファイル

実行ログは `workspace/webui_logs/` に保存されます。

## 注意事項

- 同時に実行できるエージェントは1つのみ
- バックグラウンド実行はブラウザを閉じても継続
- 完了後もログは保持されます
