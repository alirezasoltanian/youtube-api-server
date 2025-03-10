import json
import os
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import urlopen
from typing import Optional, List, Dict, Any
import tempfile

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import yt_dlp

# Keep the youtube-transcript-api as a fallback
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None
    print("Warning: youtube_transcript_api not installed. Using yt-dlp for captions.")

app = FastAPI(title="YouTube Tools API")

class YouTubeTools:
    @staticmethod
    def get_youtube_video_id(url: str) -> Optional[str]:
        """Function to get the video ID from a YouTube URL."""
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname

        if hostname == "youtu.be":
            return parsed_url.path[1:]
        if hostname in ("www.youtube.com", "youtube.com"):
            if parsed_url.path == "/watch":
                query_params = parse_qs(parsed_url.query)
                return query_params.get("v", [None])[0]
            if parsed_url.path.startswith("/embed/"):
                return parsed_url.path.split("/")[2]
            if parsed_url.path.startswith("/v/"):
                return parsed_url.path.split("/")[2]
        return None

    @staticmethod
    def get_video_data(url: str, browser: Optional[str] = None) -> dict:
        """Function to get video data from a YouTube URL using yt-dlp."""
        if not url:
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            # Configure yt-dlp options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'format': 'best',
            }
            
            # Add cookies from browser if specified
            if browser:
                ydl_opts['cookiesfrombrowser'] = (browser, None, None, None)
            
            # Use yt-dlp to extract info
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Create a clean data structure
                clean_data = {
                    "title": info.get("title"),
                    "channel": info.get("channel"),
                    "channel_url": info.get("channel_url"),
                    "upload_date": info.get("upload_date"),
                    "duration": info.get("duration"),
                    "view_count": info.get("view_count"),
                    "like_count": info.get("like_count"),
                    "thumbnail": info.get("thumbnail"),
                    "description": info.get("description"),
                    "categories": info.get("categories"),
                    "tags": info.get("tags"),
                }
                return clean_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting video data: {str(e)}")

    @staticmethod
    def get_video_captions(url: str, languages: Optional[List[str]] = None) -> str:
        """Get captions from a YouTube video using yt-dlp."""
        if not url:
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            # Configure yt-dlp options for subtitles
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': languages if languages else ['en'],
                'subtitlesformat': 'json3',
            }
            
            with tempfile.TemporaryDirectory() as temp_dir:
                ydl_opts['paths'] = {'home': temp_dir}
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Try to get subtitles from the downloaded info
                    if info.get('requested_subtitles'):
                        captions_text = ""
                        for lang, subtitle_info in info['requested_subtitles'].items():
                            if subtitle_info.get('data'):
                                # Parse the JSON3 format subtitles
                                try:
                                    subtitle_data = json.loads(subtitle_info['data'])
                                    for event in subtitle_data.get('events', []):
                                        if 'segs' in event:
                                            for seg in event['segs']:
                                                if 'utf8' in seg:
                                                    captions_text += seg['utf8'] + " "
                                except Exception as e:
                                    print(f"Error parsing subtitle data: {e}")
                        
                        if captions_text:
                            return captions_text.strip()
            
            # Fallback to YouTubeTranscriptApi if yt-dlp didn't work
            if YouTubeTranscriptApi:
                video_id = YouTubeTools.get_youtube_video_id(url)
                if not video_id:
                    raise HTTPException(status_code=400, detail="Invalid YouTube URL")
                
                captions = None
                if languages:
                    captions = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
                else:
                    captions = YouTubeTranscriptApi.get_transcript(video_id)
                
                if captions:
                    return " ".join(line["text"] for line in captions)
            
            return "No captions found for video"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting captions for video: {str(e)}")

    @staticmethod
    def get_video_timestamps(url: str, languages: Optional[List[str]] = None) -> List[str]:
        """Generate timestamps for a YouTube video based on captions using yt-dlp."""
        if not url:
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            # Configure yt-dlp options for subtitles
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': languages if languages else ['en'],
                'subtitlesformat': 'json3',
            }
            
            timestamps = []
            
            with tempfile.TemporaryDirectory() as temp_dir:
                ydl_opts['paths'] = {'home': temp_dir}
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Try to get subtitles from the downloaded info
                    if info.get('requested_subtitles'):
                        for lang, subtitle_info in info['requested_subtitles'].items():
                            if subtitle_info.get('data'):
                                # Parse the JSON3 format subtitles
                                try:
                                    subtitle_data = json.loads(subtitle_info['data'])
                                    for event in subtitle_data.get('events', []):
                                        if 'tStartMs' in event and 'segs' in event:
                                            start_ms = event['tStartMs']
                                            start_seconds = start_ms / 1000
                                            minutes, seconds = divmod(int(start_seconds), 60)
                                            
                                            text = ""
                                            for seg in event['segs']:
                                                if 'utf8' in seg:
                                                    text += seg['utf8'] + " "
                                            
                                            if text.strip():
                                                timestamps.append(f"{minutes}:{seconds:02d} - {text.strip()}")
                                except Exception as e:
                                    print(f"Error parsing subtitle data: {e}")
            
            # Fallback to YouTubeTranscriptApi if yt-dlp didn't work or no timestamps found
            if not timestamps and YouTubeTranscriptApi:
                video_id = YouTubeTools.get_youtube_video_id(url)
                if not video_id:
                    raise HTTPException(status_code=400, detail="Invalid YouTube URL")
                
                captions = YouTubeTranscriptApi.get_transcript(video_id, languages=languages or ["en"])
                for line in captions:
                    start = int(line["start"])
                    minutes, seconds = divmod(start, 60)
                    timestamps.append(f"{minutes}:{seconds:02d} - {line['text']}")
            
            return timestamps
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating timestamps: {str(e)}")

    @staticmethod
    def get_available_subtitles(url: str) -> Dict[str, Any]:
        """Get a list of available subtitle languages for a video using yt-dlp."""
        if not url:
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            # Configure yt-dlp options for subtitles
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'listsubtitles': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Get available subtitles
                available_subs = {}
                if info.get('subtitles'):
                    available_subs['manual'] = list(info['subtitles'].keys())
                
                if info.get('automatic_captions'):
                    available_subs['automatic'] = list(info['automatic_captions'].keys())
                
                return available_subs
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting available subtitles: {str(e)}")

class YouTubeRequest(BaseModel):
    url: str
    languages: Optional[List[str]] = None
    browser: Optional[str] = None

@app.post("/video-data")
async def get_video_data(request: YouTubeRequest):
    """Endpoint to get video metadata"""
    return YouTubeTools.get_video_data(request.url, request.browser)

@app.post("/video-captions")
async def get_video_captions(request: YouTubeRequest):
    """Endpoint to get video captions"""
    return YouTubeTools.get_video_captions(request.url, request.languages)

@app.post("/video-timestamps")
async def get_video_timestamps(request: YouTubeRequest):
    """Endpoint to get video timestamps"""
    return YouTubeTools.get_video_timestamps(request.url, request.languages)

# Add a new endpoint to get available subtitle languages
@app.post("/available-subtitles")
async def get_available_subtitles(request: YouTubeRequest):
    """Endpoint to get available subtitle languages for a video"""
    return YouTubeTools.get_available_subtitles(request.url)

if __name__ == "__main__":
    # Use environment variable for port, default to 8000 if not set
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)