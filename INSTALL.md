# Installation and Setup Instructions

## Prerequisites

- macOS 11+ (Big Sur or newer)
- Python 3.9+
- pip (Python package installer)

## Installation Steps

1. **Clone or download this repository:**
   ```
   git clone https://github.com/yourusername/youtube-shorts-uploader.git
   cd youtube-shorts-uploader
   ```

2. **Create a virtual environment (recommended):**
   ```
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Set up your YouTube API credentials:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the YouTube Data API v3
   - Create OAuth 2.0 credentials (Web application type)
   - Set authorized redirect URIs to include `http://localhost:8080/`
   - Download the credentials JSON file and save it as `client_secrets.json` in the project root directory

5. **Get an OpenAI API key:**
   - Sign up or log in at [OpenAI's website](https://platform.openai.com/)
   - Create an API key from your account dashboard
   - You'll enter this in the application settings

## Running the Application

There are two ways to run the application:

### Option 1: Using the run script
```
./run.py
```

### Option 2: Using the module directly
```
python -m youtube_shorts_uploader.main
```

## First-Time Setup

When you first run the application:

1. Go to the Settings tab
2. Enter your OpenAI API key
3. Set your desired upload folder
4. Configure other settings as needed
5. Click "Save Settings"

## Building a Standalone Application

To create a standalone macOS application:

1. Install PyInstaller if you haven't already:
   ```
   pip install pyinstaller
   ```

2. Run the build command:
   ```
   pyinstaller --windowed --name "YouTube Shorts Uploader" --icon=youtube_shorts_uploader/resources/icon.png run.py
   ```

3. Find the generated application in the `dist` folder

## Troubleshooting

- **Authentication Issues**: If you encounter authentication problems, try removing the `token.pickle` file and restart the application to go through the authentication flow again.
- **API Key Issues**: Make sure your OpenAI API key has sufficient credits and permissions.
- **Video Processing Issues**: Ensure OpenCV and YOLO dependencies are installed correctly.

## Support

If you encounter any issues, please file a bug report on the GitHub repository. 