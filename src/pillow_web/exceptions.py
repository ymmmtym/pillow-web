class PillowWebError(Exception):
    """pillow-web の基本例外"""


class ValidationError(PillowWebError):
    """リクエストパラメータのバリデーション失敗"""

    status_code = 400


class BackgroundImageError(PillowWebError):
    """背景画像の取得・処理失敗"""

    status_code = 503
