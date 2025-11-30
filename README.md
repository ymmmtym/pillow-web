# pillow-web

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

*   **`width`** (整数, デフォルト: 600): 生成する画像の幅 (ピクセル)。
*   **`height`** (整数, デフォルト: 200): 生成する画像の高さ (ピクセル)。
*   **`mode`** (文字列, デフォルト: `RGB`): 画像のモード (例: `RGB`, `RGBA`)。
*   **`color`** (文字列, デフォルト: `black`): 背景色 (例: `red`, `blue`, `#FF0000`など)。
    *   `mode=RGBA`の場合、`transparent`を指定すると透明な背景になります。
*   **`fill`** (文字列, デフォルト: `white`): テキストの色。
*   **`align`** (文字列, デフォルト: `center`): テキストの配置 (`left`, `center`, `right`)。
*   **`spacing`** (整数, デフォルト: 4): テキストの行間のスペース (ピクセル)。
*   **`font_size`** (整数, デフォルト: 120): テキストのフォントサイズ。
*   **`backgroundimage`** (URL): 背景として使用する画像のURL。指定された場合、`color`パラメータは無視されます。

### 使用例

ブラウザで以下のURLにアクセスして画像を生成できます。

*   **カスタムサイズ:** `http://127.0.0.1:5000/Custom_Size?width=800&height=300`
*   **背景色と文字色:** `http://127.0.0.1:5000/Colorful_Text?color=blue&fill=yellow`
*   **大きなフォント:** `http://127.0.0.1:5000/Large_Font?font_size=150`
*   **透明な背景:** `http://127.0.0.1:5000/Transparent_Background?mode=RGBA&color=transparent`
*   **画像背景:** `http://127.0.0.1:5000/With_Image_Background?backgroundimage=https://example.com/your_image.jpg`
    *(`https://example.com/your_image.jpg` を実際の画像のURLに置き換えてください。)*



## テストの実行

テストコードを実行するには以下のコマンドを使用してください：

```bash
uv run pytest
```

これにより、画像生成APIの各種機能（フォーマット指定など）がテストされます。

