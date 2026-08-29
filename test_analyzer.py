import sys
import os
from dotenv import load_dotenv

load_dotenv()

from services.youtube_service import get_youtube_video_info
from services.gemini_service import analyze_novel_info

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = "https://youtu.be/6S_C1tA_Ljs"
        
    print("=" * 60)
    print(f"🚀 開始測試 YouTube 小說名稱解析邏輯")
    print(f"🔗 測試網址: {test_url}")
    print("=" * 60)

    print("\n[Step 1] 抓取 YouTube 影片資訊與字幕...")
    video_data = get_youtube_video_info(test_url)
    
    if "error" in video_data:
        print(f"❌ 錯誤: {video_data['error']}")
        return

    print(f"✅ 標題: {video_data.get('title')}")
    print(f"✅ 上傳者: {video_data.get('uploader')}")
    print(f"✅ 說明欄字數: {len(video_data.get('description', ''))} 字")
    print(f"✅ 字幕字數: {len(video_data.get('transcript', ''))} 字")

    print("\n[Step 2] 傳送給 Google Gemini AI 進行分析...")
    print("-" * 60)
    
    analysis_result = analyze_novel_info(video_data)
    
    print("\n【Gemini 分析結果】:")
    print(analysis_result)
    print("=" * 60)

if __name__ == "__main__":
    main()
