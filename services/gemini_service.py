import os
import logging
import requests

logger = logging.getLogger(__name__)

def analyze_novel_info(video_data: dict) -> str:
    """
    從影片標題、說明欄與字幕中解析小說名稱與詳細資訊。
    支援：
    1. 本地開源 AI 模型 (Ollama - Qwen / Llama / DeepSeek)，完全免 API Key！
    2. Google Gemini API (讀取本地 .env，金鑰無須透漏給任何人)
    """
    title = video_data.get("title", "")
    description = video_data.get("description", "")
    transcript = video_data.get("transcript", "")
    uploader = video_data.get("uploader", "")
    
    if not title and not transcript and not description:
        return "❌ 無法取得影片的標題、說明欄或字幕內容，無法分析。"

    prompt = f"""
你一位精通華文網路小說（起點、番茄小說、七貓、晉江等）、漫畫與動漫解說的資深專家。
請根據以下提供的 YouTube 影片資訊，推斷並識別出該影片解說所對應的原始小說資訊：

【影片標題】：{title}
【創作者/頻道】：{uploader}
【影片說明欄】：
{description[:1000]}

【字幕/逐字稿內容】：
{transcript[:3000] if transcript else "(無字幕內容)"}

---

【分析與識別要求】：
1. 自動修復語音轉文字的拼音與諧音錯字（例如：「迎正/銀正」應校正為正統名字「嬴正」；「天道仇勤」校正為「天道酬勤」）。
2. 若標題或說明欄中已有明確書名或 Hashtag，請優先結合字幕驗證。
3. 請務必給出準確的原著小說名稱、作者、主角名字、發表平台（如番茄小說、起點中文網等）及書籍 ID（若字幕/說明欄中有提及）。
4. 若無法確定具體書名，請根據劇情與主角名給出最可能的 1~2 本小說名稱，並註明信心度。

【請嚴格使用以下繁體中文格式回覆】：
📖 小說名稱：《[小說原名]》
✍️ 作者：[作者名稱/未知]
👤 主角名稱：[主角正統姓名] (影片中諧音：[諧音/無])
🌐 首發平台：[如：番茄小說 / 起點中文網 / 微信讀書] (書籍 ID: [若有則填，無則填無])
💡 故事核心與系統/天賦設定：[1-2 句話精簡說明主角金手指與背景]
🎯 識別信心度：[高 / 中 / 低]
"""

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5")

    # 1. 優先方案：若啟用 USE_OLLAMA，呼叫本地完全免費開源 LLM (免 API Key)
    if use_ollama:
        try:
            logger.info(f"正在呼叫本地開源 Ollama 模型 ({ollama_model})...")
            response = requests.post(
                ollama_url,
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            else:
                return f"⚠️ 本地 Ollama 回傳錯誤代碼: {response.status_code}"
        except Exception as e:
            logger.error(f"Ollama 連線失敗: {e}")
            return f"❌ 本地 Ollama 未啟動，請先安裝並啟動 Ollama (ollama run {ollama_model})，或於 .env 中設定 GEMINI_API_KEY。"

    # 2. 備用方案：若有 GEMINI_API_KEY (存在您電腦本地的 .env 中，不用透漏給任何人)
    if api_key and api_key != "your_gemini_api_key_here":
        try:
            # 優先試用最新官方 google-genai SDK
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                return response.text.strip()
            except ImportError:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=api_key)
                model = genai_legacy.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt)
                return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API 呼叫失敗: {e}")
            return f"⚠️ Gemini API 解析發生錯誤：{str(e)}"

    return "❌ 尚未設定 AI 模型。您可以：\n1. 直接在您電腦上的 .env 檔案中填入 GEMINI_API_KEY（自己貼即可，無需傳給任何人）。\n2. 或在 .env 設定 USE_OLLAMA=true 使用本地免費開源 AI。"
