import json
import os
import requests
from selectolax.parser import HTMLParser
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import urlopen
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.proxies import WebshareProxyConfig
except ImportError:
    raise ImportError(
        "`youtube_transcript_api` not installed. Please install using `pip install youtube_transcript_api`"
    )

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
    def get_video_data(url: str) -> dict:
        """Function to get video data from a YouTube URL."""
        if not url:
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            video_id = YouTubeTools.get_youtube_video_id(url)
            if not video_id:
                raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        except Exception:
            raise HTTPException(status_code=400, detail="Error getting video ID from URL")
        
        try:
            params = {"format": "json", "url": f"https://www.youtube.com/watch?v={video_id}"}
            oembed_url = "https://www.youtube.com/oembed"
            query_string = urlencode(params)
            full_url = oembed_url + "?" + query_string
           
            with urlopen(full_url) as response:
                response_text = response.read()
                video_data = json.loads(response_text.decode())
                clean_data = {
                    "title": video_data.get("title"),
                    "author_name": video_data.get("author_name"),
                    "author_url": video_data.get("author_url"),
                    "type": video_data.get("type"),
                    "height": video_data.get("height"),
                    "width": video_data.get("width"),
                    "version": video_data.get("version"),
                    "provider_name": video_data.get("provider_name"),
                    "provider_url": video_data.get("provider_url"),
                    "thumbnail_url": video_data.get("thumbnail_url"),
                }
                return clean_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting video data: {str(e)}")

    @staticmethod
    def get_video_captions(url: str, languages: Optional[List[str]] = None) -> str:
        """Get captions from a YouTube video."""
        if not url:
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            video_id = YouTubeTools.get_youtube_video_id(url)
            if not video_id:
                raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        except Exception:
            raise HTTPException(status_code=400, detail="Error getting video ID from URL")

        try:
            captions = None
            if languages:
                # ytt_api = YouTubeTranscriptApi(
                #     proxy_config=WebshareProxyConfig(
                #            proxy_username=os.getenv("PROXY_USERNAME"),
                #            proxy_password=os.getenv("PROXY_PASSWORD"),
                #     )
                # )
                # print(ytt_api , "ytt_api")
                # captions = ytt_api.get_transcript(video_id, languages=languages)
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
        """Generate timestamps for a YouTube video based on captions."""
        if not url:
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            video_id = YouTubeTools.get_youtube_video_id(url)
            if not video_id:
                raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        except Exception:
            raise HTTPException(status_code=400, detail="Error getting video ID from URL")

        try:
            captions = YouTubeTranscriptApi.get_transcript(video_id, languages=languages or ["en"])
            timestamps = []
            for line in captions:
                start = int(line["start"])
                minutes, seconds = divmod(start, 60)
                timestamps.append(f"{minutes}:{seconds:02d} - {line['text']}")
            return timestamps
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating timestamps: {str(e)}")

class YouTubeRequest(BaseModel):
    url: str
    languages: Optional[List[str]] = None

@app.post("/video-data")
async def get_video_data(request: YouTubeRequest):
    """Endpoint to get video metadata"""
    return YouTubeTools.get_video_data(request.url)

@app.post("/video-captions")
async def get_video_captions(request: YouTubeRequest):
    """Endpoint to get video captions"""
    return YouTubeTools.get_video_captions(request.url, request.languages)

@app.post("/video-timestamps")
async def get_video_timestamps(request: YouTubeRequest):
    """Endpoint to get video timestamps"""
    return YouTubeTools.get_video_timestamps(request.url, request.languages)

class TelegramTools:
    @staticmethod
    def get_channel_posts(channel_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Function to get posts from multiple Telegram channels."""
        if not channel_names:
            raise HTTPException(status_code=400, detail="No channel names provided")
        
        result = {}
        
        for channel_name in channel_names:
            try:
                url = f"https://t.me/s/{channel_name}"
                response = requests.post(url)
                
                if response.status_code != 200:
                    result[channel_name] = {"error": f"Failed to fetch channel: {response.status_code}"}
                    continue
                
                posts = []
                parser = HTMLParser(response.text)
                
                for message_bubble in parser.css('div.tgme_widget_message_bubble'):
                    try:
                        post_data = {}
                        
                        # Get text content if available
                        text_element = message_bubble.css_first('div.tgme_widget_message_text')
                        if text_element:
                            post_data["text"] = text_element.text()
                        
                        # Get image if available
                        image_element = message_bubble.css_first('.tgme_widget_message_photo_wrap')
                        if image_element:
                            style = image_element.attributes.get('style', '')
                            url_start = style.find('url(')
                            url_end = style.find(')', url_start)
                            if url_start != -1 and url_end != -1:
                                post_data["image_url"] = style[url_start + 5:url_end - 1]
                        
                        # Get video if available
                        video_element = message_bubble.css_first('video')
                        if video_element:
                            post_data["video_url"] = video_element.attrs.get('src')
                        
                        # Get metadata
                        date_element = message_bubble.css_first('a.tgme_widget_message_date')
                        if date_element:
                            post_data["post_id"] = date_element.attrs.get('href').replace(f'https://t.me/{channel_name}/', '')
                            
                        time_element = message_bubble.css_first('time')
                        if time_element:
                            post_data["datetime"] = time_element.attrs.get('datetime')
                        
                        posts.append(post_data)
                    except Exception as e:
                        # Skip posts that cause errors
                        continue
                
                # معکوس کردن ترتیب پست‌ها قبل از ذخیره در نتیجه
                result[channel_name] = posts[::-1]
                
            except Exception as e:
                result[channel_name] = {"error": str(e)}
        
        return result

class TelegramRequest(BaseModel):
    channel_names: List[str]

@app.post("/telegram-channel-posts")
async def get_telegram_channel_posts(request: TelegramRequest):
    """Endpoint to get posts from multiple Telegram channels"""
    return TelegramTools.get_channel_posts(request.channel_names)

if __name__ == "__main__":
    # Use environment variable for port, default to 8000 if not set
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)