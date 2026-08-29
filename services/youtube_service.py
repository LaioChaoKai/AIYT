import re
import logging
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7'
}

def extract_video_id(url: str) -> str | None:
    """從各種 YouTube URL 格式中解析出 Video ID (支援 8~12 字元，含 ?si= 帶追蹤參數網址)"""
    if not url:
        return None
        
    patterns = [
        r'(?:v=|/)([0-9A-Za-z_-]{8,12})(?:[&?/]|$)',
        r'youtu\.be/([0-9A-Za-z_-]{8,12})',
        r'youtube\.com/shorts/([0-9A-Za-z_-]{8,12})',
        r'youtube\.com/embed/([0-9A-Za-z_-]{8,12})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
            
    return None

def fetch_oembed_metadata(clean_url: str) -> dict:
    """NoEmbed & YouTube oEmbed API (免 Key、不封鎖 Cloud IP，100% 秒抓標題與作者)"""
    # 1. 優先試用 NoEmbed API (全網公認跨網域無阻擋提取服務)
    try:
        noembed_url = f"https://noembed.com/embed?url={clean_url}"
        resp = requests.get(noembed_url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("title"):
                return {
                    "title": data.get("title", ""),
                    "uploader": data.get("author_name", "")
                }
    except Exception as e:
        logger.warning(f"NoEmbed API 抓取失敗: {e}")

    # 2. 備援：YouTube 官方 oEmbed API
    oembed_url = f"https://www.youtube.com/oembed?url={clean_url}&format=json"
    try:
        resp = requests.get(oembed_url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "title": data.get("title", ""),
                "uploader": data.get("author_name", "")
            }
    except Exception as e:
        logger.warning(f"oEmbed API 抓取失敗: {e}")

    return {}

def fetch_page_meta_description(clean_url: str) -> str:
    """從 YouTube 網頁 HTML meta 標籤提取 Description"""
    try:
        resp = requests.get(clean_url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            html = resp.text
            match = re.search(r'<meta\s+(?:name|property)=["\']og:description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
            if not match:
                match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
            if match:
                return match.group(1)
    except Exception as e:
        logger.warning(f"HTML Description 提取失敗: {e}")
    return ""

def fetch_video_metadata(clean_url: str) -> dict:
    """整合提取：NoEmbed/oEmbed 優先 + yt-dlp + HTML Scraper 多重保險"""
    metadata = {
        'title': '',
        'description': '',
        'uploader': '',
        'tags': []
    }

    # 1. 優先使用無卡頓的 NoEmbed / oEmbed 抓取標題與創作者
    oembed = fetch_oembed_metadata(clean_url)
    if oembed.get('title'):
        metadata['title'] = oembed['title']
        metadata['uploader'] = oembed.get('uploader', '')

    # 2. 嘗試使用 yt-dlp 補全 description 與 tags
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'user_agent': HEADERS['User-Agent'],
        'nocheckcertificate': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            if info:
                if not metadata['title']:
                    metadata['title'] = info.get('title', '')
                metadata['description'] = info.get('description', '')
                if not metadata['uploader']:
                    metadata['uploader'] = info.get('uploader', '')
                metadata['tags'] = info.get('tags', []) or []
    except Exception as e:
        logger.warning(f"yt-dlp 補全資訊跳過: {e}")

    # 3. 備援：若說明欄仍為空，從 HTML Meta 標籤抓取
    if not metadata['description']:
        metadata['description'] = fetch_page_meta_description(clean_url)

    return metadata

def fetch_transcript(video_id: str) -> str:
    """使用 youtube-transcript-api 取得影片字幕 (優先繁體、簡體、自動生成字幕)"""
    try:
        transcript_list = None
        if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        else:
            try:
                api_inst = YouTubeTranscriptApi()
                if hasattr(api_inst, 'list'):
                    transcript_list = api_inst.list(video_id)
            except Exception:
                pass
                
        if not transcript_list:
            return ""

        languages = ['zh-TW', 'zh-CN', 'zh-Hant', 'zh-Hans', 'zh', 'en']
        transcript = None
        try:
            transcript = transcript_list.find_transcript(languages)
        except Exception:
            try:
                transcript = transcript_list.find_generated_transcript(languages)
            except Exception:
                for t in transcript_list:
                    transcript = t
                    break
                    
        if transcript:
            data = transcript.fetch()
            full_text = " ".join([item.get('text', '') for item in data[:500]])
            return full_text
            
    except Exception as e:
        logger.info(f"影片 {video_id} 無字幕或抓取失敗: {e}")
        
    return ""

def get_youtube_video_info(url: str) -> dict:
    """
    整合入口：解析 Video ID，抓取標題、說明欄與字幕
    """
    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "無法識別的 YouTube 網址格式，請提供正確的 YouTube 影片連結。"}
        
    clean_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # 抓取標題與說明 (多重備援)
    metadata = fetch_video_metadata(clean_url)
    
    # 抓取字幕
    transcript = fetch_transcript(video_id)
    
    return {
        "video_id": video_id,
        "url": clean_url,
        "title": metadata.get("title", ""),
        "description": metadata.get("description", ""),
        "uploader": metadata.get("uploader", ""),
        "tags": metadata.get("tags", []),
        "transcript": transcript
    }
