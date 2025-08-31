[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/tomoya-asdf/ReadOnlyViewer/blob/main/LICENSE)

# 読み取り専用ファイルビューア

このアプリケーションは、指定されたディレクトリ内の様々なファイルを読み取り専用で表示するためのデスクトップアプリケーションです。PyQt6で構築されており、PDF、Microsoft Officeドキュメント（.docx, .xlsx, .pptx）、CSV、および一般的なテキストファイルの内容をプレビューできます。

## 機能

- **ファイルシステムナビゲーション**: 直感的なツリービューでファイルシステムを閲覧できます。
- **ファイルプレビュー**:
    - **PDF**: ページごとのプレビューとページナビゲーションをサポートします。
    - **Microsoft Office**: Word (.docx), Excel (.xlsx), PowerPoint (.pptx) ファイルのテキストコンテンツを抽出して表示します。
    - **CSV**: CSVファイルのコンテンツを表示します。
    - **テキストファイル**: .txt, .md, .json, .xml, コードファイルなど、様々なテキストベースのファイルをサポートします。
- **検索機能**:
    - **ファイル/フォルダ名検索**: ファイル名やフォルダ名を正規表現で検索し、ツリービューをフィルタリングします。
    - **コンテンツ検索**: プレビュー表示されているテキストコンテンツ内を検索し、一致する箇所をハイライト表示します。
- **一時ファイル処理**: プレビューのために一時的に作成されたファイルは、アプリケーション終了時に自動的にクリーンアップされます。

## インストール

1. **リポジリのクローン**:
   ```bash
   git clone https://github.com/tomoya-asdf/ReadOnlyViewer.git 
   cd read_only_viewer
   ```

2. **仮想環境の作成とアクティベート**:
   ```bash
   python -m venv env
   # Windowsの場合
   .\env\Scripts\activate
   # macOS/Linuxの場合
   source env/bin/activate
   ```

3. **依存関係のインストール**:
   `requestments.txt` に記載されているライブラリをインストールします。
   ```bash
   pip install -r requestments.txt
   ```

## 実行方法

仮想環境がアクティブな状態で、以下のコマンドを実行します。

```bash
python src/main.py
```

## 使用技術

- Python 3
- PyQt6
- PyMuPDF (fitz)
- openpyxl
- python-docx
- python-pptx
- その他、`requestments.txt` に記載のライブラリ

## 貢献

このプロジェクトへの貢献を歓迎します。バグ報告や機能提案は、GitHubのIssueトラッカーをご利用ください。

## ライセンス

MIT License