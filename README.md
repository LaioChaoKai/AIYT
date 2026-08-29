# 📖 YouTube 小說名稱搜尋器 LINE Bot (AI 小說辨識助理)

這是一個能接收 YouTube 或 Shorts 影片連結，並自動從「影片標題、說明欄與字幕逐字稿」中，利用 **Google Gemini AI** 解析並精準找出原始華文網路小說名稱、作者、主角與發表平台的 LINE 機器人。

---

## 🌟 專案亮點與特色

1. **雙重資訊提取 (Metadata + Captions)**
   - 使用 `yt-dlp` 抓取影片標題、頻道名稱與說明欄（說明欄常含有簡介或標籤）。
   - 使用 `youtube-transcript-api` 自動抓取中文字幕（支援繁體、簡體與 AI 自動生成字幕）。

2. **Gemini AI 諧音與錯字智慧校正**
   - 自動修正語音轉文字 (ASR) 中的常見同音字錯字（例如將解說字幕中的「迎正 / 銀正」校正為正統名字「嬴正」）。
   - 給出詳細的《小說原名》、《作者》、《主角》、《首發平台/書籍ID》與故事簡介。

3. **防超時異步架構 (LINE Webhook Safe)**
   - 採用多執行緒非同步背景處理（`threading.Thread` + `push_message`），解決 LINE Webhook 5 秒超時限制問題。

4. **開箱即用的測試與部署設定**
   - 內建獨立 CLI 測試腳本 `test_analyzer.py`，免設定 LINE 機器人即可先測試 AI 解析結果。

---

## 📂 專案目錄結構

```text
AI幹片/
├── services/
│   ├── youtube_service.py # YouTube 標題、說明與字幕提取模組
│   └── gemini_service.py  # Google Gemini AI 分析模组
├── app.py                 # Flask LINE Bot Webhook 主程式
├── test_analyzer.py       # 獨立 CLI 測試腳本 (免 LINE 即可測試)
├── requirements.txt       # Python 依賴套件表
├── .env.example           # 環境變數範本
├── .env                   # 本機環境變數檔 (請填入金鑰)
└── README.md              # 專案說明文件
```

---

## 🚀 快速開始教學

### 1. 安裝與設定環境

請在終端機中開啟此專案目錄並執行：

```bash
# 建立 Python 虛擬環境
python -m venv venv

# 啟動虛擬環境 (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# 安裝所需套件
pip install -r requirements.txt
```

### 2. 設定環境變數 (`.env`)

複製 `.env.example` 並重新命名為 `.env`（或直接修改 `.env`）：

```ini
# LINE Messaging API 設定
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_CHANNEL_ACCESS_TOKEN
LINE_CHANNEL_SECRET=你的_LINE_CHANNEL_SECRET

# Google Gemini API 金鑰 (免費申請: https://aistudio.google.com/)
GEMINI_API_KEY=你的_GEMINI_API_KEY

PORT=5000
```

---

## 🧪 獨立 CLI 測試 (不用 LINE 機器人即可測試)

在填入 `GEMINI_API_KEY` 後，可以直接在終端機測試任何 YouTube 影片：

```bash
python test_analyzer.py https://youtu.be/6S_C1tA_Ljs
```

---

## 🤖 啟動 LINE Bot 與 本機 ngrok 測試

### 第一步：啟動 Flask Webhook 服務
```bash
python app.py
```
服務將會在 `http://localhost:5000` 啟動。

### 第二步：使用 ngrok 建立公網網址
下載並安裝 [ngrok](https://ngrok.com/)，在另一個終端機執行：
```bash
ngrok http 5000
```
ngrok 會產生一個 HTTPS 網址，例如：`https://xxxx-xx-xx.ngrok-free.app`

### 第三步：設定 LINE Developers Console
1. 前往 [LINE Developers Console](https://developers.line.biz/) 並登入。
2. 進入你的 Channel -> **Messaging API** 分頁。
3. 設定 **Webhook URL** 為：`https://xxxx-xx-xx.ngrok-free.app/callback`
4. 點擊 **Verify** 驗證連線。
5. 開啟 **Use webhook** 開關。
6. 開啟 LINE APP 掃瞄 QR Code 加入好友，發送 YouTube 網址即可開始測試！

---

## ☁️ 免費部署至雲端平台 (Render / Zeabur / Railway)

當您測試完成並想讓機器人 24 小時在線時，可以部署至免費/低價雲端平台：

1. **Render 部署**：
   - 建立 Web Service 並連結你的 GitHub 儲存庫。
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Environment Variables: 設定 `LINE_CHANNEL_ACCESS_TOKEN`、`LINE_CHANNEL_SECRET`、`GEMINI_API_KEY`。
   - 將 Render 產生的網址填入 LINE Webhook URL (`https://your-app.onrender.com/callback`)。

---

## 💡 創作者與維護
Created for AI Short Video & Novel Search Assistant.
