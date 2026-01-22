# Indiegogo Scraper (GUI)

Indiegogoの検索結果から商品情報を自動収集する、GUIベースのスクレイピングツールです。
実務における「動的サイトへの対応」「ユーザーフレンドリーな操作性」「エラーハンドリング」を意識して開発しました。

## 主な機能

- **GUI操作**: Tkinterを採用し、非エンジニアでも直感的に「待機時間」や「スクロール回数」を設定可能
- **動的コンテンツ対応**: 
  - Seleniumを用いて「Load more」ボタンを自動クリック
  - 無限スクロールによるデータ読み込みの実装
- **非同期処理（マルチスレッド）**: スクレイピング実行中もGUIがフリーズせず、リアルタイムで進捗ログを確認可能
- **データ出力**: 収集データを整形し、BOM付きUTF-8のCSV形式で保存（Excelでの文字化けを防止）

## 使用技術

- **Language**: Python 3.x
- **Libraries**:
  - `Selenium`: ブラウザ自動操作
  - `BeautifulSoup4`: HTML解析
  - `Pandas`: データ整形・CSV出力
  - `Tkinter`: GUI実装
- **Driver Management**: `webdriver-manager` により、Chromeドライバーの自動更新に対応

## セットアップと実行方法 ##

1. リポジトリをクローン
  ```bash
   git clone https://github.com/tokotoko1818/scraping_sample.git
   cd scraping_sample
  ```

2. 仮想環境の作成と有効化
  ```bash
   python -m venv venv
   .\venv\Scripts\activate
  ```

3. 依存ライブラリのインストール
  ```bash
   pip install -r requirements.txt
  ```

4. 実行
  ```bash
   python main.py
  ```

