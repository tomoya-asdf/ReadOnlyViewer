from __future__ import annotations

from functools import lru_cache
from typing import Tuple

from utils.file_operations import extract_text_preview

# このキャッシュはプロセスごとに作成されます
@lru_cache(maxsize=128)
def get_cached_text_preview(file_path: str) -> str:
    """テキスト抽出の結果をキャッシュします。"""
    return extract_text_preview(file_path)

def search_file_worker(args: Tuple[str, str]):
    """
    multiprocessingのためのワーカー関数です。
    単一のファイル内でキーワードを検索します。
    処理したファイルパスと、キーワードが見つかったかどうかの真偽値を返します。
    """
    file_path, keyword = args
    try:
        # キャッシュされた関数を使用します
        text = get_cached_text_preview(file_path)
        if keyword.lower() in text.lower():
            return (file_path, True)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return (file_path, False)
