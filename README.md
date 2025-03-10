# YouTube Tools API Server

A FastAPI-based server that provides convenient endpoints for extracting information from YouTube videos, including video metadata, captions, and timestamped transcripts.

## Features

- Get video metadata (title, author, thumbnails, etc.)
- Extract video captions/transcripts
- Generate timestamped transcripts
- Support for multiple languages in captions
- Clean and RESTful API design

## Prerequisites

- Python 3.7+
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/zaidmukaddam/youtube-api-server.git
cd youtube-api-server
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

Start the server using:

```bash
python main.py
```

By default, the server runs on:
- Host: 0.0.0.0
- Port: 8000

You can customize these using environment variables:
```bash
export PORT=8080
export HOST=127.0.0.1
python main.py
```

## API Endpoints

### 1. Get Video Metadata
```http
POST /video-data
```

**Request Body:**
```json
{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Response:** Video metadata including title, author, thumbnails, etc.

### 2. Get Video Captions
```http
POST /video-captions
```

**Request Body:**
```json
{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "languages": ["en", "es"]  // Optional
}
```

**Response:** Complete transcript text of the video.

### 3. Get Video Timestamps
```http
POST /video-timestamps
```

**Request Body:**
```json
{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "languages": ["en"]  // Optional
}
```

**Response:** List of timestamps with corresponding caption text.

## Example Usage

Using curl:

```bash
# Get video metadata
curl -X POST "http://localhost:8000/video-data" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'

# Get video captions
curl -X POST "http://localhost:8000/video-captions" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "languages": ["en"]}'
```

## Error Handling

The API includes comprehensive error handling for:
- Invalid YouTube URLs
- Missing or unavailable captions
- Network errors
- Invalid language codes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate. 