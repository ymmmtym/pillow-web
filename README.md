# pillow-web

[![Test](https://github.com/ymmmtym/pillow-web/actions/workflows/test.yml/badge.svg)](https://github.com/ymmmtym/pillow-web/actions/workflows/test.yml)

このプロジェクトは、指定されたテキストと様々なオプションを使用して動的に画像を生成するシンプルなWeb APIです。

## 起動方法

1.  **依存関係のインストール:**
    ```bash
    uv sync
    ```
2.  **アプリケーションの実行:**
    ```bash
    uv run main.py
    ```
    アプリケーションは通常 `http://127.0.0.1:5000` で利用可能になります。

## APIエンドポイント

### `GET /<text>`

指定されたテキストを画像として生成します。

**例:** `http://127.0.0.1:5000/Hello_World`

### クエリパラメータ

以下のクエリパラメータを使用して、生成される画像の見た目をカスタマイズできます。

*   **`width`** (整数, デフォルト: 600): 生成する画像の幅 (ピクセル)。1～4096 の範囲で指定します。
*   **`height`** (整数, デフォルト: 200): 生成する画像の高さ (ピクセル)。1～4096 の範囲で指定します。
*   **`mode`** (文字列, デフォルト: `RGB`): 画像のモード (例: `RGB`, `RGBA`)。
*   **`color`** (文字列, デフォルト: `black`): 背景色 (例: `red`, `blue`, `#FF0000`など)。
    *   `mode=RGBA`の場合、`transparent`を指定すると透明な背景になります。
*   **`fill`** (文字列, デフォルト: `white`): テキストの色。
*   **`align`** (文字列, デフォルト: `center`): テキストの配置 (`left`, `center`, `right`)。
*   **`spacing`** (整数, デフォルト: 4): テキストの行間のスペース (ピクセル)。
*   **`font_size`** (整数, デフォルト: 120): テキストのフォントサイズ。
*   **`format`** (文字列, デフォルト: `png`): 出力画像のフォーマット (`png`, `jpg`, `jpeg`)。
*   **`backgroundimage`** (URL): 背景として使用する画像のURL。指定された場合、`color`パラメータは無視されます。

### 使用例

ブラウザで以下のURLにアクセスして画像を生成できます。

*   **カスタムサイズ:** `http://127.0.0.1:5000/Custom_Size?width=800&height=300`
*   **背景色と文字色:** `http://127.0.0.1:5000/Colorful_Text?color=blue&fill=yellow`
*   **大きなフォント:** `http://127.0.0.1:5000/Large_Font?font_size=150`
*   **透明な背景:** `http://127.0.0.1:5000/Transparent_Background?mode=RGBA&color=transparent`
*   **画像背景:** `http://127.0.0.1:5000/With_Image_Background?backgroundimage=https://example.com/your_image.jpg`
    *(`https://example.com/your_image.jpg` を実際の画像のURLに置き換えてください。)*



### インタラクティブAPIドキュメント

`/docs` エンドポイントでSwagger UIベースのインタラクティブなAPIドキュメントを参照できます。

```bash
# サーバー起動後、ブラウザで以下にアクセス
open http://127.0.0.1:5000/docs
```

OpenAPI 3.0仕様書は `/openapi.yaml` からも直接取得できます。

## フォント設定

日本語テキストを正しく表示するには、日本語対応フォントが必要です。
以下の優先順位でフォントを探索します。

1. **環境変数** `PILLOW_WEB_FONT_PATH` で指定されたパス
2. `fonts/` ディレクトリ内のフォントファイル
3. システムフォント（例: `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`）
4. `arial.ttf`
5. Pillowのデフォルトフォント

### セットアップ例（Noto Sans CJK）

```bash
# Debian/Ubuntu
sudo apt install fonts-noto-cjk

# 環境変数で明示的に指定
export PILLOW_WEB_FONT_PATH=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc

# またはプロジェクト内に配置
# cp NotoSansJP-Regular.otf fonts/
```

## デプロイガイド

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
EXPOSE 5000
CMD ["uv", "run", "main.py"]
```

```bash
docker build -t pillow-web .
docker run -p 5000:5000 pillow-web
```

### Render

1. [Render](https://render.com) にログイン
2. "New Web Service" を選択
3. リポジトリを連携し、以下を設定:
   - **Build Command:** `uv sync`
   - **Start Command:** `uv run main.py`
4. デプロイ

### Heroku

```bash
# heroku.yml
echo 'build:
  languages:
    - python
run:
  web: uv run main.py' > heroku.yml

heroku create pillow-web
git push heroku main
```

### AWS/GCP/Azure

各クラウドプラットフォームではDockerイメージをビルドしてコンテナサービス（ECS, Cloud Run, ACIなど）にデプロイしてください。

```bash
# 例: Google Cloud Run
gcloud builds submit --tag gcr.io/PROJECT/pillow-web
gcloud run deploy pillow-web --image gcr.io/PROJECT/pillow-web --port 5000
```

## トラブルシューティング

| 問題 | 原因と対策 |
|---|---|
| 画像が表示されない | ブラウザが画像を直接表示しているか確認。`Ctrl+F5` でハードリロード。 |
| `width must not exceed 4096` | 画像サイズは1～4096ピクセルの範囲に制限されています。 |
| `backgroundimage` が読み込めない | URLが有効か確認。プライベートIPアドレスへのリクエストはセキュリティのためブロックされます。 |
| `Unsupported format` | `format` パラメータには `png`, `jpg`, `jpeg` のいずれかを指定してください。 |
| サーバーが起動しない | `uv sync` で依存関係が正しくインストールされているか確認。`localhost:5000` が他のプロセスに使用されていないか確認。 |
| `エラーが発生しました` | パラメータの値が正しいか確認（数値が必要な箇所に文字列を指定していないかなど）。 |

## テストの実行

テストコードを実行するには以下のコマンドを使用してください：

```bash
uv run python -m pytest
```

これにより、画像生成APIの各種機能（フォーマット指定など）がテストされます。

カバレッジレポートを表示するには：

```bash
uv run python -m pytest --cov=pillow_web --cov-report=term
```
