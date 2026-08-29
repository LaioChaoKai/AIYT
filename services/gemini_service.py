import os
import logging
import requests

logger = logging.getLogger(__name__)

def analyze_novel_info(video_data: dict) -> str:
    """
    從影片網址、標題、說明欄與字幕中解析小說名稱與詳細資訊。
    結合用戶優化的 Prompt 邏輯：從內容中尋找書名、作者、主角與書籍 ID，
    若未直接提及書名，則根據主角姓名與核心設定推斷出最可能的小說名稱。
    """
    url = video_data.get("url", "")
    title = video_data.get("title", "")
    description = video_data.get("description", "")
    transcript = video_data.get("transcript", "")
    uploader = video_data.get("uploader", "")
    
    if not title and not transcript and not description:
        return "❌ 無法取得影片的標題、說明欄或字幕內容，無法分析。"

    prompt = f"""
這是一段 YouTube 小說/動漫解說影片的完整資訊與網址。
請務必使用【 Google 聯網搜尋 (Google Search) 】工具，輸入網址【 {url} 】與頻道【 {uploader} 】，比對全網（YouTube 搜尋紀錄、番茄小說、起點中文網、百度等）找到這支解說影片對應的原著小說！

【YouTube 影片網址】：{url}
【影片標題】：{title}
【創作者/頻道】：{uploader}
【影片說明欄】：
{description[:1000] if description else "(無說明欄)"}

【字幕/逐字稿內容】：
{transcript[:3500] if transcript else "(無字幕內容)"}

---

【任務與推理指令】：
1. 聯網與網址搜尋（最重要）：請直接使用 Google Search 工具搜尋網址「{url}」與頻道「{uploader}」在網路上被紀錄的對白、標題或解說資訊。
2. 小說與主角比對：從搜尋結果中找出該影片解說的原始小說名稱（例如：番茄小說《高武：一分努力，萬倍暴擊收益！》）、作者（例如：愛喝茶的男人）、主角名字（例如：嬴正）與書籍 ID（例如：742698778866013288）。
3. 諧音校正與設定推理：若字幕包含語音轉文字的錯字或諧音（例如：「迎正/銀正」應校正為正統名字「嬴正」），若未直接提及書名，請根據主角名字與核心設定推斷出最可能的小說名稱。

【請嚴格使用以下繁體中文格式回覆】：
📖 小說名稱：《[小說原名]》
✍️ 作者：[作者名稱/未知]
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

    # 2. 核心方案：使用 Gemini API 搭配 Google 聯網搜尋工具 (支持 SDK + 多重 REST Fallback)
    if api_key and api_key != "your_gemini_api_key_here":
        try:
            # 2.1 嘗試官方 google-genai SDK 聯網搜尋
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
                if response and response.text:
                    return response.text.strip()
            except Exception as genai_err:
                logger.warning(f"google-genai SDK 呼叫失敗，嘗試 REST API: {genai_err}")

            # 2.2 嘗試 REST API 直接呼叫 (相容所有 API Key 與 Bearer 授權格式)
            rest_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
            headers_list = [
                {"x-goog-api-key": api_key, "Content-Type": "application/json"},
                {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            ]
            
            for headers in headers_list:
                resp = requests.post(
                    rest_url,
                    headers=headers,
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "tools": [{"google_search": {}}]
                    },
                    timeout=45
                )
                if resp.status_code == 200:
                    res_json = resp.json()
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text_result = "".join([p.get("text", "") for p in parts])
                        if text_result.strip():
                            return text_result.strip()

            return "⚠️ Gemini API 呼叫已完成但未傳回文字結果，請檢查 API Key 或伺服器網路連線。"

        except Exception as e:
            logger.error(f"Gemini API 呼叫失敗: {e}")
            return f"⚠️ Gemini API 解析發生錯誤：{str(e)}"

    return "❌ 尚未設定 AI 模型。請於 Render 後台的 Environment Variables 填入 GEMINI_API_KEY。"
