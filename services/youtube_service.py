import re
import logging
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import yt_dlp

logger = logging.getLogger(__name__)

def extract_video_id(url: str) -> str | None:
    """從各種 YouTube URL 格式中解析出 11 位數的 Video ID"""
    if not url:
        return None
        
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[\&\?\/]|$)',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/shorts\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
            
    return None

def fetch_video_metadata(url: str) -> dict:
    """使用 yt-dlp 抓取影片標題、說明欄與作者"""
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False
    }
    
    metadata = {
        'title': '',
        'description': '',
        'uploader': '',
        'tags': []
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                metadata['title'] = info.get('title', '')
                metadata['description'] = info.get('description', '')
                metadata['uploader'] = info.get('uploader', '')
                metadata['tags'] = info.get('tags', []) or []
    except Exception as e:
        logger.error(f"yt-dlp 提取元數據失敗: {e}")
        
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
            # 拼接字幕內容，取前 500 句（涵蓋大部分影片精華）
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
        return {"error": "無法識別的 YouTube 網址格式"}
        
    clean_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # 抓取標題與說明
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
