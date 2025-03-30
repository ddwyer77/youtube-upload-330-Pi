# YouTube Shorts Uploader for Raspberry Pi

A headless YouTube Shorts uploader designed to run on a Raspberry Pi. This application allows you to schedule YouTube Shorts uploads and have them automatically uploaded at specified times, even when your main computer is off.

## Features

- Automated YouTube Shorts uploads on a schedule
- Runs as a systemd service on Raspberry Pi
- Easy file transfer from your main computer
- Authentication with YouTube API
- Upload status tracking and history
- No GUI required - perfect for headless operation

## System Requirements

- Raspberry Pi (tested on Raspberry Pi 5 with 8GB RAM)
- Raspberry Pi OS (64-bit recommended)
- Internet connection
- 50MB+ of free disk space (not including videos)
- Python 3.7+

## Setup Instructions

### 1. On Your Development Computer

1. Clone this repository:
   ```bash
   git clone https://github.com/ddwyer77/youtube-upload-330-Pi.git
   cd youtube-upload-330-Pi
   ```

2. Authenticate with YouTube (if you haven't already):
   ```bash
   python desktop_auth.py
   ```
   This will create a `token.pickle` file that stores your YouTube API credentials.

3. Make sure both `token.pickle` and `client_secrets.json` files are in the repository root.

### 2. On the Raspberry Pi

1. Clone the repository:
   ```bash
   git clone https://github.com/ddwyer77/youtube-upload-330-Pi.git
   cd youtube-upload-330-Pi
   ```

2. Run the setup script:
   ```bash
   chmod +x raspberry_pi_setup.sh
   ./raspberry_pi_setup.sh
   ```

3. Transfer authentication files from your development computer:
   ```bash
   # On your development computer:
   scp token.pickle pi@raspberrypi.local:~/youtube-upload-330-Pi/
   scp client_secrets.json pi@raspberrypi.local:~/youtube-upload-330-Pi/
   ```

4. Start and enable the service:
   ```bash
   sudo systemctl start youtube-uploader.service
   sudo systemctl enable youtube-uploader.service
   ```

## Usage

### Transferring Videos and Scheduling Uploads

Use the included transfer script to send videos to your Raspberry Pi and schedule them for upload:

```bash
# Transfer videos and schedule them
python transfer_to_pi.py --videos video1.mp4 video2.mp4 --schedule --interval 6

# Transfer videos with a specific start time and privacy setting
python transfer_to_pi.py --videos video1.mp4 video2.mp4 --schedule --time "2025-04-01T12:00:00" --privacy public

# Transfer authentication files 
python transfer_to_pi.py --auth

# Specify a different Raspberry Pi hostname or IP
python transfer_to_pi.py --host 192.168.1.100 --videos video1.mp4
```

### Manually Editing the Schedule

You can also manually edit the schedule on the Pi:

```bash
# On the Raspberry Pi
nano ~/.youtube_shorts_uploader/scheduled_uploads.json
```

The schedule format is:
```json
{
  "scheduled_uploads": [
    {
      "file_path": "/home/pi/videos/video1.mp4",
      "title": "Amazing YouTube Short #1",
      "description": "Check out this amazing YouTube short video!",
      "tags": ["shorts", "youtube", "viral"],
      "scheduled_time": "2025-04-01T12:00:00",
      "privacy": "public"
    }
  ]
}
```

### Monitoring Uploads

Check the service status and logs:

```bash
# Service status
sudo systemctl status youtube-uploader.service

# View logs
tail -f ~/youtube_uploader_logs.txt
```

## Development

### Adding New Features

1. Make your changes to the codebase
2. Push to GitHub
3. Pull the changes on your Raspberry Pi:
   ```bash
   cd ~/youtube-upload-330-Pi
   git pull
   ```
4. Restart the service:
   ```bash
   sudo systemctl restart youtube-uploader.service
   ```

### Troubleshooting

- **Authentication issues:** Re-run the authentication on your desktop and transfer the new `token.pickle` file.
- **Upload failures:** Check the logs for detailed error messages.
- **Service not starting:** Verify Python dependencies are installed on the Pi.
- **Connection issues:** Make sure your Raspberry Pi has a stable internet connection.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with Python and Google's YouTube Data API
- Thanks to the PyQt team for the original GUI version 