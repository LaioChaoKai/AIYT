import logging
import traceback
import requests
import urllib.parse
from flask import Blueprint, render_template, request, jsonify
from services.youtube_service import get_youtube_video_info, fetch_oembed_metadata, fetch_page_meta_description, fetch_transcript, extract_video_id, HEADERS
from services.gemini_service import analyze_novel_info

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)

@health_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@health_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "service": "YouTube Novel Finder",
        "version": "1.2.0"
    }), 200

@health_bp.route("/api/debug_raw", methods=["GET", "POST"])
def debug_raw():
    url = request.args.get("url") or (request.json or {}).get("url") or "https://youtu.be/6S_C1tA_Ljs"
    video_id = extract_video_id(url)
    clean_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
    
    debug_info = {}
    
    # 1. Test NoEmbed
    try:
        noembed_url = f"https://noembed.com/embed?url={clean_url}"
        r = requests.get(noembed_url, headers=HEADERS, timeout=5)
        debug_info["noembed_status"] = r.status_code
        debug_info["noembed_data"] = r.json() if r.status_code == 200 else r.text[:200]
    except Exception as e:
        debug_info["noembed_err"] = str(e)
        debug_info["noembed_trace"] = traceback.format_exc()

    # 2. Test oEmbed
    try:
        oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(clean_url, safe='')}&format=json"
        r = requests.get(oembed_url, headers=HEADERS, timeout=5)
        debug_info["youtube_oembed_status"] = r.status_code
        debug_info["youtube_oembed_data"] = r.json() if r.status_code == 200 else r.text[:200]
    except Exception as e:
        debug_info["youtube_oembed_err"] = str(e)

    # 3. Test Full Info
    try:
        full_info = get_youtube_video_info(url)
        debug_info["full_info"] = full_info
    except Exception as e:
        debug_info["full_info_err"] = str(e)

    return jsonify(debug_info), 200

@health_bp.route("/api/search", methods=["POST"])
def api_search():
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
