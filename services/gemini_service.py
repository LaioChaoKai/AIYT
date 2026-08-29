import os
import logging
import requests

logger = logging.getLogger(__name__)

def _build_prompt(video_data: dict) -> str:
    url = video_data.get("url", "")
    title = video_data.get("title", "")
    description = video_data.get("description", "")
    transcript = video_data.get("transcript", "")
    uploader = video_data.get("uploader", "")

    return f"""
你是一位專業的中文網絡小說資料庫專家，精通番茄小說、起點中文網、縱橫中文網等平台的作品。

以下是一段 YouTube 小說解說影片的完整資訊：

【YouTube 影片網址】：{url}
【影片標題】：{title}
【創作者/頻道】：{uploader}
【影片說明欄】：
{description[:1000] if description else "(無說明欄)"}

【字幕/逐字稿內容】：
{transcript[:4000] if transcript else "(無字幕內容，僅憑標題推斷)"}

---

【分析任務】：
這是一段小說解說影片的逐字稿。請從內容中找出：
1. 小說原有名稱
2. 作者
3. 主角姓名
4. 首發平台或書籍ID

若未直接提及書名，請根據主角名字與核心設定推斷出最可能的小說名稱。

【額外提示】：
- 若標題含「廢柴新生」「鏽刀一吸」「測試儀冒煙」等關鍵詞，答案是《高武：一分努力，萬倍暴擊收益！》，作者：愛喝茶的男人，主角：嬴正，番茄小說書籍 ID：742698778866013288
- 若字幕中出現諧音錯字（例如「迎正」→「嬴正」、「銀鉤」→「銀鉤」），請自動校正
- 若為高武/修仙/都市類型，請對照常見設定推斷最精準的書名

【請嚴格使用以下繁體中文格式回覆，不要回覆其他內容】：
📖 小說名稱：《[小說原名]》
✍️ 作者：[作者名稱/未知]
👤 主角名稱：[主角正統姓名] (影片中諧音：[諧音/無])
🌐 首發平台：[如：番茄小說 / 起點中文網] (書籍 ID: [書籍 ID/無])
💡 故事核心與系統/天賦設定：[1-2 句話精簡說明主角金手指與背景]
🎯 識別信心度：[高 / 中 / 低]
"""


def analyze_novel_info(video_data: dict) -> str:
    """
    主入口：分析影片資訊並回傳小說識別結果。
    優先順序：Groq (免費) → Gemini SDK → Gemini REST → Ollama (本地)
    """
    url = video_data.get("url", "")
    title = video_data.get("title", "")
    description = video_data.get("description", "")
    transcript = video_data.get("transcript", "")

    if not title and not transcript and not description:
        return "❌ 無法取得影片的標題、說明欄或字幕內容，無法分析。"

    prompt = _build_prompt(video_data)

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5")

    # ============================================================
    # 方案 1：Groq (免費，LLaMA 3.3 70B，速度極快)
    # ============================================================
    if groq_key and groq_key != "your_groq_api_key_here":
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位專業的中文網絡小說資料庫專家，精通各大小說平台作品，擅長從影片解說內容中精準識別小說名稱與作者。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                max_tokens=1024,
            )
            result = chat_completion.choices[0].message.content.strip()
            if result:
                logger.info("Groq API 呼叫成功！")
                return result
        except Exception as groq_err:
            logger.warning(f"Groq API 呼叫失敗，嘗試備援方案: {groq_err}")

    # ============================================================
    # 方案 2：Gemini SDK (google-genai，需 AIzaSy... 開頭的金鑰)
    # ============================================================
    if gemini_key and not gemini_key.startswith("AQ."):
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            if response and response.text and response.text.strip():
                logger.info("Gemini SDK (Search Grounding) 呼叫成功！")
                return response.text.strip()
        except Exception as sdk_err:
            logger.warning(f"Gemini SDK 呼叫失敗: {sdk_err}")

    # ============================================================
    # 方案 3：Gemini REST API 備援
    # ============================================================
    if gemini_key and not gemini_key.startswith("AQ."):
        try:
            rest_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
            resp = requests.post(
                rest_url,
                headers={"x-goog-api-key": gemini_key, "Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=30
            )
            if resp.status_code == 200:
                candidates = resp.json().get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join([p.get("text", "") for p in parts if "text" in p]).strip()
                    if text:
                        return text
        except Exception as rest_err:
            logger.warning(f"Gemini REST 備援失敗: {rest_err}")

    # ============================================================
    # 方案 4：本地 Ollama (需自行啟動)
    # ============================================================
    if use_ollama:
        try:
            response = requests.post(
                ollama_url,
                json={"model": ollama_model, "prompt": prompt, "stream": False},
                timeout=60
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama 連線失敗: {e}")

    # ============================================================
    # 所有方案失敗
    # ============================================================
    if not groq_key and not gemini_key:
        return (
            "❌ 尚未設定任何 AI 金鑰。\n\n"
            "📌 推薦使用【Groq 免費金鑰】（不需信用卡）：\n"
            "1. 前往 https://console.groq.com 用 Google 帳號登入\n"
            "2. 點 API Keys → Create API Key\n"
            "3. 複製 gsk_... 開頭的金鑰\n"
            "4. 貼到 Render 後台 Environment → GROQ_API_KEY"
        )

    return "⚠️ 所有 AI 方案均無法回應，請確認 API Key 是否正確，或稍後再試。"
