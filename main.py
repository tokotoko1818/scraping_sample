import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import pandas as pd
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# 固定設定
TARGET_URL = "https://www.indiegogo.com/en/projects/search?SortType=MostPopular&Source=Filtered"
DEFAULT_PAUSE_TIME = 3.0
DEFAULT_MAX_SCROLLS = 50

class ScraperApp(tk.Tk):
    
    def __init__(self):
        super().__init__()
        self.title("Indiegogo Scraper (GUI)")
        self.geometry("600x450") 
        
        self.is_running = False
        
        self.create_widgets()

    def create_widgets(self):
        """UI部品の作成と配置"""
        
        settings_frame = ttk.LabelFrame(self, text="設定", padding="10 10 10 10")
        settings_frame.pack(pady=10, padx=10, fill='x')

        # スクロール待機時間 (秒)
        self.pause_time_frame = ttk.Frame(settings_frame)
        self.pause_time_frame.pack(pady=5, anchor='w')
        ttk.Label(self.pause_time_frame, text="スクロール待機時間 (秒):").pack(side=tk.LEFT, padx=5)
        
        self.pause_time_var = tk.DoubleVar(value=DEFAULT_PAUSE_TIME)
        self.pause_time_entry = ttk.Spinbox(
            self.pause_time_frame, 
            from_=1.0, to=60.0, increment=0.5, 
            textvariable=self.pause_time_var, width=5, 
            justify=tk.RIGHT
        )
        self.pause_time_entry.pack(side=tk.LEFT)

        # スクロール回数上限
        self.max_scrolls_frame = ttk.Frame(settings_frame)
        self.max_scrolls_frame.pack(pady=5, anchor='w')
        ttk.Label(self.max_scrolls_frame, text="スクロール回数上限:").pack(side=tk.LEFT, padx=5)
        
        self.max_scrolls_var = tk.IntVar(value=DEFAULT_MAX_SCROLLS) 
        self.max_scrolls_entry = ttk.Spinbox(
            self.max_scrolls_frame, 
            from_=1, to=1000, increment=1, 
            textvariable=self.max_scrolls_var, width=5, 
            justify=tk.RIGHT
        )
        self.max_scrolls_entry.pack(side=tk.LEFT)
        
        # --- 実行ステータスとボタン ---
        self.status_label = ttk.Label(self, text="準備完了", font=("Arial", 12, "bold"))
        self.status_label.pack(pady=5)

        self.start_button = ttk.Button(self, text="スクレイピング開始", command=self.start_scraping_thread)
        self.start_button.pack(pady=5)
        
        # --- ログ表示エリア ---
        self.log_text = scrolledtext.ScrolledText(self, width=70, height=10, state=tk.DISABLED)
        self.log_text.pack(pady=10, padx=10, fill='both', expand=True)

    def update_status(self, message):
        """GUIのステータスラベルとログを更新する (スレッドセーフ)"""
        self.status_label.config(text=message)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{time.strftime('[%H:%M:%S]')} {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start_scraping_thread(self):
        """スクレイピング処理を別スレッドで開始する前に、設定をバリデーションする"""
        if self.is_running:
            self.update_status("⚠️ 既に実行中です。")
            return

        # パラメータの取得とバリデーション
        try:
            scroll_pause_time = float(self.pause_time_var.get())
            max_scrolls = int(self.max_scrolls_var.get())
        except ValueError:
            messagebox.showerror("入力エラー", "待機時間とループ数には数値を入力してください。")
            self.update_status("🔴 エラー: 設定値が無効です。")
            return

        if scroll_pause_time < 1.0:
            messagebox.showerror("入力エラー", "スクロール待機時間は最小1.0秒です。")
            self.update_status("🔴 エラー: 設定値が無効です。")
            return
        
        if max_scrolls < 1:
            messagebox.showerror("入力エラー", "スクロール回数上限は最小1回です。")
            self.update_status("🔴 エラー: 設定値が無効です。")
            return

        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.update_status("▶️ スクレイピング処理を開始しました...")
        
        self.scraper_thread = threading.Thread(
            target=self.run_scraper, 
            args=(scroll_pause_time, max_scrolls)
        )
        self.scraper_thread.start()

    def run_scraper(self, SCROLL_PAUSE_TIME, MAX_SCROLLS):
        """Seleniumを使った実際のスクレイピング処理 (別スレッドで実行)"""
        driver = None
        try:
            self.update_status(" Chrome WebDriverを初期化中...")
            driver = self.initialize_driver()
            
            self.update_status(f" ターゲットURLへ移動中: {TARGET_URL}")
            driver.get(TARGET_URL)
            time.sleep(SCROLL_PAUSE_TIME) 
            
            self.scroll_to_load_all_content(driver, SCROLL_PAUSE_TIME, MAX_SCROLLS)
            
            self.update_status(" 読み込んだHTMLからデータを抽出中...")
            projects_data = self.parse_and_extract(driver)
            
            if projects_data:
                # ★ process_and_save にプロジェクトデータのみを渡すように変更
                self.process_and_save(projects_data) 
            else:
                self.update_status("❌ 抽出データが0件でした。")

        except Exception as e:
            self.update_status(f"🔴 致命的なエラーが発生しました: {e}")
            print(f"Exception: {e}") 

        finally:
            if driver:
                driver.quit()
                self.update_status("✅ 処理完了。WebDriverを終了しました。")
            
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            
    # --- Selenium Helper Functions ---
    def initialize_driver(self):
        """Chromeドライバーを初期化し、WebDriverを返す"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        options.add_argument("--no-sandbox")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    
    def scroll_to_load_all_content(self, driver, SCROLL_PAUSE_TIME, MAX_SCROLLS):
        """最初にLoad moreボタンをクリックし、その後ページをスクロールして全コンテンツを読み込む"""
        self.update_status("--- コンテンツ読み込み処理開始 ---")
        try:
            self.update_status(" 'Load more' ボタンを検索中...")
            load_more_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[span[contains(text(), 'Load more')]]"))
            )
            load_more_button.click()
            self.update_status(" 'Load more' ボタンをクリックしました。")
            time.sleep(SCROLL_PAUSE_TIME) 
        except Exception:
            self.update_status(" 'Load more' ボタンが見つからないか、クリックに失敗しました。無限スクロールに進みます。")

        self.update_status("無限スクロールで追加コンテンツを読み込み中...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        load_count = 0
        
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE_TIME)
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height or load_count >= MAX_SCROLLS:
                self.update_status(f"スクロール終了。合計 {load_count} 回の追加読み込みを行いました。")
                break
            
            last_height = new_height
            load_count += 1
            self.update_status(f"スクロール {load_count}/{MAX_SCROLLS} 回目...")

    def parse_and_extract(self, driver):
        """WebDriverで取得したHTMLからデータを抽出する"""
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        project_cards = soup.select('div[data-qa^="search-result-project:"]')
        self.update_status(f" HTMLから {len(project_cards)} 件のプロジェクトを検出。")
        
        extracted_data = []
        for card in project_cards:
            name_element = card.select_one('h3[data-qa="project-card:ProjectName"] a')
            item_name = name_element.text.strip() if name_element else "N/A"
            
            creator_element = card.find('span', class_='_tc--lighter', string=lambda t: t and 'by' in t)
            creator_name = creator_element.text.strip().replace('by ', '') if creator_element else "N/A"
            
            funds_element = card.select_one('[data-qa="project-card:FundsGathered"]')
            funds_gathered = funds_element.text.strip() if funds_element else "N/A"
            
            extracted_data.append({
                "商品名": item_name,
                "販売元": creator_name,
                "金額": funds_gathered,
            })
        return extracted_data

    # --- 保存処理を修正 ---
    def process_and_save(self, projects):
        """抽出したデータをDataFrameに変換し、日付付きのCSVファイルに保存する"""
        df = pd.DataFrame(projects)
        
        # 実行日の取得とファイル名の生成 (indiegogo_YYYYMMDD.csv)
        today_str = datetime.datetime.now().strftime("%Y%m%d")
        dynamic_output_file = f"indiegogo_{today_str}.csv"
        
        # CSVとして保存
        df.to_csv(dynamic_output_file, index=False, encoding='utf-8-sig') 
        
        self.update_status(f" データは正常に {dynamic_output_file} に保存されました。合計 {len(df)} 件。")


if __name__ == "__main__":
    app = ScraperApp()
    app.mainloop()