import os
import logging
import requests

logger = logging.getLogger(__name__)

def analyze_novel_info(video_data: dict) -> str:
    """
    從影片標題、說明欄與字幕中解析小說名稱與詳細資訊。
    透過 Google Search Grounding 聯網搜尋工具，比對番茄小說、起點中文網等資料庫，
    精準找出原著小說名稱、作者、首發平台與書籍 ID。
    """
    title = video_data.get("title", "")
    description = video_data.get("description", "")
    transcript = video_data.get("transcript", "")
    uploader = video_data.get("uploader", "")
    
    if not title and not transcript and not description:
        return "❌ 無法取得影片的標題、說明欄或字幕內容，無法分析。"

    prompt = f"""
你一位精通華文網路小說（起點、番茄小說、七貓、晉江等）、漫畫與動漫解說的資深專家。
請務必使用【 Google 聯網搜尋 (Google Search) 】工具搜尋網路資料庫（如番茄小說、起點中文網、百度等），精準比對出這部影片解說對應的【原始小說名稱】與【書籍資訊】。

【影片標題】：{title}
【創作者/頻道】：{uploader}
【影片說明欄】：
{description[:1000]}

【字幕/逐字稿內容】：
{transcript[:3000] if transcript else "(無字幕內容)"}

---

【搜尋與解析指令】：
1. 請搜尋影片標題中的完整對白或關鍵字（例如：「廢柴新生？鏽刀一吸，測試儀當場冒煙！」、「嬴正」、「天道酬勤系統」），在番茄小說或起點中文網上尋找 matches。
2. 自動修復語音轉文字的拼音與諧音錯字（例如：「迎正/銀正」校正為「嬴正」；「天道仇勤」校正為「天道酬勤」）。
3. 必須透過網路搜尋結果給出準確的原著小說名稱、作者、主角名字、首發平台（如番茄小說）及書籍 ID。

【請嚴格使用以下繁體中文格式回覆】：
📖 小說名稱：《[小說原名]》
✍️ 作者：[作者名稱]
👤 主角名稱：[主角正統姓名] (影片中諧音：[諧音/無])
🌐 首發平台：[如：番茄小說 / 起點中文網] (書籍 ID: [書籍 ID/無])
💡 故事核心與系統/天賦設定：[1-2 句話精簡說明主角金手指與背景]
🎯 識別信心度：[高 / 中 / 低]
"""

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5")

    # 1. 優先方案：若啟用 USE_OLLAMA，呼叫本地免費開源 LLM
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
            return f"❌ 本地 Ollama 未啟動，請先安裝並啟動 Ollama (ollama run {ollama_model})，或於 .env / Render 中設定 GEMINI_API_KEY。"

    # 2. 核心方案：使用 Gemini API 搭配 Google 聯網搜尋工具 (Google Search Grounding)
    if api_key and api_key != "your_gemini_api_key_here":
        try:
            # 優先使用最新官方 google-genai SDK
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                return response.text.strip()
            except Exception as genai_err:
                logger.warning(f"google-genai 聯網搜尋失敗，嘗試舊版 SDK: {genai_err}")
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=api_key)
                model = genai_legacy.GenerativeModel("gemini-1.5-flash", tools=['google_search_retrieval'])
                response = model.generate_content(prompt)
                return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API 呼叫失敗: {e}")
            return f"⚠️ Gemini API 解析發生錯誤：{str(e)}"

    return "❌ 尚未設定 AI 模型。請於 Render 後台的 Environment Variables 填入 GEMINI_API_KEY。"
