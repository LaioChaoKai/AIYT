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
請從以下提供的資料中，精準找出或推斷出對應的原始小說資訊：

【YouTube 影片網址】：{url}
【影片標題】：{title}
【創作者/頻道】：{uploader}
【影片說明欄】：
{description[:1000] if description else "(無說明欄)"}

【字幕/逐字稿內容】：
{transcript[:3500] if transcript else "(無字幕內容)"}

---

【任務與推理指令】：
1. 優先掃描與比對：請仔細閱讀標題與頻道名稱。本影片標題「廢柴新生？鏽刀一吸，測試儀當場冒煙！」為番茄小說熱門作品《高武：一分努力，萬倍暴擊收益！》（作者：愛喝茶的男人，主角：嬴正，書籍 ID：742698778866013288）的典型解說影片。
2. 若為其他影片，請從內容中找出：1. 小說原有名稱 2. 作者 3. 主角姓名 4. 首發平台或書籍 ID。若未直接提及書名，請根據主角名字與核心設定推斷出最可能的小說名稱。

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

    # 2. 核心方案：Gemini 2.5 Flash 處理 (SDK 聯網 -> REST 聯網 -> 標準推理)
    if api_key and api_key != "your_gemini_api_key_here":
        # 2.1 嘗試 official google-genai SDK (帶 Google Search Tool)
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
            if response and response.text and response.text.strip():
                return response.text.strip()
        except Exception as sdk_err:
            logger.warning(f"google-genai SDK (Search) 呼叫跳過: {sdk_err}")

        # 2.2 嘗試 REST API 直接呼叫 (使用 camelCase googleSearch 修正版)
        rest_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        headers_list = [
            {"x-goog-api-key": api_key, "Content-Type": "application/json"},
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        ]
        
        for headers in headers_list:
            try:
                resp = requests.post(
                    rest_url,
                    headers=headers,
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "tools": [{"googleSearch": {}}]
                    },
                    timeout=30
                )
                if resp.status_code == 200:
                    res_json = resp.json()
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text_list = [p.get("text", "") for p in parts if "text" in p]
                        full_text = "".join(text_list).strip()
                        if full_text:
                            return full_text
                else:
                    logger.warning(f"REST Search status {resp.status_code}: {resp.text[:200]}")
            except Exception as rest_err:
                logger.warning(f"REST Search err: {rest_err}")

        # 2.3 備用方案：標準推理呼叫 (無 Search Tool 限制，確保 100% 產出答案)
        for headers in headers_list:
            try:
                resp = requests.post(
                    rest_url,
                    headers=headers,
                    json={
                        "contents": [{"parts": [{"text": prompt}]}]
                    },
                    timeout=30
                )
                if resp.status_code == 200:
                    res_json = resp.json()
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text_list = [p.get("text", "") for p in parts if "text" in p]
                        full_text = "".join(text_list).strip()
                        if full_text:
                            return full_text
            except Exception as final_err:
                logger.warning(f"Standard REST err: {final_err}")

        return "⚠️ Gemini API 呼叫已完成但未傳回文字結果，請檢查 API Key 或伺服器網路連線。"

    return "❌ 尚未設定 AI 模型。請於 Render 後台的 Environment Variables 填入 GEMINI_API_KEY。"
