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
*   **`format`** (文字列, デフォルト: `png`): 出力画像のフォーマット (`png`, `jpg`, `jpeg`, `webp`, `avif`)。
*   **`quality`** (整数, デフォルト: `70`): 出力画像の品質。1〜100の範囲で指定します。JPEG/WebP/AVIF形式で有効です。
*   **`backgroundimage`** (URL): 背景として使用する画像のURL。指定された場合、`color`パラメータは無視されます。
*   **`x`** (整数, オプション): テキストのX座標（ピクセル）。指定しない場合は中央配置。
*   **`y`** (整数, オプション): テキストのY座標（ピクセル）。指定しない場合は中央配置。
*   **`position`** (文字列, オプション): テキストの配置位置。`top-left`, `top-center`, `top-right`, `center-left`, `center`, `center-right`, `bottom-left`, `bottom-center`, `bottom-right` のいずれか。
*   **`offset_x`** (整数, デフォルト: 0): X方向の相対オフセット（ピクセル）。
*   **`offset_y`** (整数, デフォルト: 0): Y方向の相対オフセット（ピクセル）。
*   **`shadow_color`** (文字列, オプション): テキストの影の色。指定すると影が付きます。
*   **`shadow_offset_x`** (整数, デフォルト: 3): 影のX方向のオフセット（ピクセル）。
*   **`shadow_offset_y`** (整数, デフォルト: 3): 影のY方向のオフセット（ピクセル）。
*   **`stroke_width`** (整数, デフォルト: 0): テキストの縁取りの太さ（ピクセル）。0で縁取りなし。
*   **`stroke_color`** (文字列, デフォルト: `black`): テキストの縁取りの色。
*   **`gradient_from`** (文字列, オプション): グラデーションの開始色。`gradient_to`と併用。
*   **`gradient_to`** (文字列, オプション): グラデーションの終了色。`gradient_from`と併用。
*   **`rotation`** (数値, デフォルト: 0): テキストの回転角度（度）。
*   **`filter`** (文字列, オプション): 画像に適用するフィルター効果。`blur`, `sepia`, `grayscale`, `brightness`, `contour`, `emboss`, `sharpen`, `smooth`, `edge_enhance` のいずれか。
*   **`filter_strength`** (数値, オプション): フィルターの強度。blurの場合はぼかし半径、brightnessの場合は明度倍率、sepiaの場合はブレンド率（0〜1、1.0を超える値は1.0として扱われます）。デフォルトはフィルターごとに異なります。
*   **`qr`** (文字列, オプション): QRコードにエンコードする文字列。指定すると画像内にQRコードが埋め込まれます。
*   **`qr_size`** (整数, デフォルト: 10): QRコードのモジュールサイズ（ピクセル）。
*   **`qr_error_correction`** (文字列, デフォルト: `M`): QRコードの誤り訂正レベル。`L`（低）, `M`（中）, `Q`（やや高）, `H`（高）のいずれか。
*   **`qr_position`** (文字列, オプション): QRコードの配置位置。`top-left`, `top-center`, `top-right`, `center-left`, `center`, `center-right`, `bottom-left`, `bottom-center`, `bottom-right` のいずれか。
*   **`qr_x`** (整数, オプション): QRコードのX座標（ピクセル）。
*   **`qr_y`** (整数, オプション): QRコードのY座標（ピクセル）。
*   **`qr_offset_x`** (整数, デフォルト: 0): QRコードのX方向オフセット（ピクセル）。
*   **`qr_offset_y`** (整数, デフォルト: 0): QRコードのY方向オフセット（ピクセル）。

### 使用例

ブラウザで以下のURLにアクセスして画像を生成できます。

*   **カスタムサイズ:** `http://127.0.0.1:5000/Custom_Size?width=800&height=300`
*   **背景色と文字色:** `http://127.0.0.1:5000/Colorful_Text?color=blue&fill=yellow`
*   **大きなフォント:** `http://127.0.0.1:5000/Large_Font?font_size=150`
*   **透明な背景:** `http://127.0.0.1:5000/Transparent_Background?mode=RGBA&color=transparent`
*   **画像背景:** `http://127.0.0.1:5000/With_Image_Background?backgroundimage=https://example.com/your_image.jpg`
    *(`https://example.com/your_image.jpg` を実際の画像のURLに置き換えてください。)*
*   **テキスト位置指定:** `http://127.0.0.1:5000/Bottom_Right?position=bottom-right&offset_x=-10&offset_y=-10`
*   **QRコード埋め込み:** `http://127.0.0.1:5000/QR_Code?qr=https://example.com&qr_position=top-right&qr_size=15`
*   **ピクセル指定:** `http://127.0.0.1:5000/Exact_Position?x=50&y=50`
*   **テキストに影:** `http://127.0.0.1:5000/Shadow_Text?shadow_color=gray&shadow_offset_x=5&shadow_offset_y=5`
*   **テキストに縁取り:** `http://127.0.0.1:5000/Stroked_Text?stroke_width=3&stroke_color=blue`
*   **グラデーション文字:** `http://127.0.0.1:5000/Gradient_Text?gradient_from=red&gradient_to=blue`
*   **回転テキスト:** `http://127.0.0.1:5000/Rotated_Text?rotation=45`



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
| `Unsupported format` | `format` パラメータには `png`, `jpg`, `jpeg`, `webp`, `avif` のいずれかを指定してください。 |
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
