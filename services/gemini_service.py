import os
import logging

logger = logging.getLogger(__name__)

def analyze_novel_info(video_data: dict) -> str:
    """
    使用 Google Gemini API 從影片標題、說明欄與字幕中解析小說名稱與詳細資訊
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        return "❌ 尚未設定 GEMINI_API_KEY，請先在 .env 檔案中填入有效的 Gemini API 金鑰。"
        
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
            # 備用 fallback 使用 google.generativeai
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=api_key)
            model = genai_legacy.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text.strip()
            
    except Exception as e:
        logger.error(f"Gemini API 呼叫失敗: {e}")
        return f"⚠️ AI 解析過程發生錯誤：{str(e)}"
