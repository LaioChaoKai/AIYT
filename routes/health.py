import logging
from flask import Blueprint, render_template, request, jsonify
from services.youtube_service import get_youtube_video_info, fetch_oembed_metadata, fetch_page_meta_description, fetch_transcript, extract_video_id
from services.gemini_service import analyze_novel_info

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)

@health_bp.route("/", methods=["GET"])
def index():
    """渲染前端網頁版介面 (無需使用者輸入 Key，直接貼 URL 即可查)"""
    return render_template("index.html")

@health_bp.route("/health", methods=["GET"])
def health_check():
    """伺服器健康檢查 API"""
    return jsonify({
        "status": "online",
        "service": "YouTube Novel Finder",
        "version": "1.2.0"
    }), 200

@health_bp.route("/api/debug_yt", methods=["GET", "POST"])
def debug_yt():
    """除錯專用：回傳每個步驟抓到的原始資料"""
    url = request.args.get("url") or (request.json or {}).get("url") or "https://youtu.be/6S_C1tA_Ljs"
    video_id = extract_video_id(url)
    clean_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
    
    oembed = fetch_oembed_metadata(clean_url) if clean_url else {}
    html_desc = fetch_page_meta_description(clean_url) if clean_url else ""
    transcript = fetch_transcript(video_id) if video_id else ""
    full_info = get_youtube_video_info(url)
    
    return jsonify({
        "input_url": url,
        "video_id": video_id,
        "clean_url": clean_url,
        "oembed_result": oembed,
        "html_desc_len": len(html_desc),
        "transcript_len": len(transcript),
        "full_info_result": full_info
    }), 200

@health_bp.route("/api/search", methods=["POST"])
def api_search():
    """前端網頁 AJAX 搜尋 API 入口"""
    data = request.get_json() or {}
    youtube_url = data.get("url", "").strip()

    if not youtube_url:
        return jsonify({"error": "請提供有效的 YouTube 影片網址"}), 400

    try:
        logger.info(f"網頁端收到搜尋請求: {youtube_url}")
        video_data = get_youtube_video_info(youtube_url)

        if "error" in video_data:
            return jsonify({"error": video_data["error"]}), 400

        result_text = analyze_novel_info(video_data)
        return jsonify({"result": result_text}), 200

    except Exception as e:
        logger.error(f"API 搜尋時發生錯誤: {e}")
        return jsonify({"error": f"伺服器處理失敗：{str(e)}"}), 500
