# YouTube Shorts Uploader

A desktop application for uploading shorts to YouTube with AI-generated metadata.

![YouTube Shorts Uploader Screenshot](docs/images/app_screenshot.png)

## Features

- Upload videos to YouTube as Shorts
- Automatically generate titles and descriptions using OpenAI
- Analyze video content to improve metadata generation
- Support for multiple YouTube accounts
- Secure credential storage using system keychain or encrypted file storage
- Video preview and basic editing functionality
- **Schedule uploads** - Schedule multiple videos to upload at specified intervals
- **Customizable AI style** - Use custom style prompts to control how AI generates titles and descriptions

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/youtube-shorts-uploader.git
cd youtube-shorts-uploader
```

2. Create a virtual environment:
```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

3. Install the dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python run.py
```

## Configuration

1. Set up YouTube API credentials:
   - Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the YouTube Data API v3
   - Create OAuth 2.0 credentials
   - Download the client secrets file and place it in the project directory

2. Add your OpenAI API key in the Settings tab for AI-powered metadata generation

3. Configure your YouTube accounts in the Accounts tab

## Scheduled Uploads

The application supports scheduled uploads, allowing you to:
- Import a folder of videos and schedule them for upload
- Specify the time interval between uploads
- Automatically generate titles for all videos
- Monitor and manage the upload queue

See [SCHEDULING.md](SCHEDULING.md) for detailed instructions on using this feature.

## Custom Style Prompts

You can customize how the AI generates titles and descriptions:
- Enter style instructions like "use a non-chalant manner" or "include slang terms"
- Control tone, vocabulary, and writing style
- Apply different styles for different types of content

## Requirements

- Python 3.8+
- PyQt6
- Google API Python Client
- OpenAI API key (for AI-powered metadata generation)
- YouTube Data API credentials

## License

This project is licensed under the MIT License - see the LICENSE file for details. 