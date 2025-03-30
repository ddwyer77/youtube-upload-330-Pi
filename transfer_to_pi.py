#!/usr/bin/env python3
"""
Transfer Tool for YouTube Shorts Uploader

This script helps transfer videos and scheduled uploads from your computer to the Raspberry Pi.
"""

import os
import sys
import json
import argparse
import subprocess
import datetime

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Transfer videos and scheduled uploads to Raspberry Pi')
    
    parser.add_argument('--host', type=str, default='raspberrypi.local',
                        help='Hostname or IP address of the Raspberry Pi (default: raspberrypi.local)')
    
    parser.add_argument('--user', type=str, default='pi',
                        help='Username for SSH connection (default: pi)')
    
    parser.add_argument('--dir', type=str, default='~/youtube-upload-330-Pi',
                        help='Directory on the Raspberry Pi where the app is installed (default: ~/youtube-upload-330-Pi)')
    
    parser.add_argument('--videos', type=str, nargs='+',
                        help='Path(s) to video file(s) to transfer')
    
    parser.add_argument('--schedule', action='store_true',
                        help='Schedule the transferred videos for upload')
    
    parser.add_argument('--time', type=str,
                        help='Schedule time for uploads (format: YYYY-MM-DDThh:mm:ss)')
    
    parser.add_argument('--interval', type=int, default=6, 
                        help='Hours between scheduled uploads (default: 6)')
    
    parser.add_argument('--privacy', type=str, default='unlisted',
                        choices=['public', 'unlisted', 'private'],
                        help='Privacy status for uploaded videos (default: unlisted)')
    
    parser.add_argument('--auth', action='store_true',
                        help='Transfer authentication files (token.pickle and client_secrets.json)')
    
    return parser.parse_args()

def run_command(command):
    """Run a shell command and return the output."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        universal_newlines=True
    )
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        print(f"Error executing command: {command}")
        print(f"Error message: {stderr}")
        return None
    
    return stdout.strip()

def check_connection(host, user):
    """Check if the Raspberry Pi is reachable."""
    print(f"Checking connection to {host}...")
    
    result = run_command(f"ssh {user}@{host} 'echo Connected successfully'")
    
    if result == "Connected successfully":
        print(f"Connection to {host} successful")
        return True
    else:
        print(f"Failed to connect to {host}")
        print("Please make sure the Raspberry Pi is powered on and connected to the network.")
        print("You may need to set up SSH key authentication or enter the password when prompted.")
        return False

def transfer_videos(videos, host, user, remote_dir):
    """Transfer video files to the Raspberry Pi."""
    # Create the videos directory if it doesn't exist
    run_command(f"ssh {user}@{host} 'mkdir -p ~/videos'")
    
    transferred = []
    
    for video in videos:
        if not os.path.exists(video):
            print(f"Video file not found: {video}")
            continue
        
        video_name = os.path.basename(video)
        remote_path = f"~/videos/{video_name}"
        
        print(f"Transferring {video} to {host}:{remote_path}...")
        
        result = run_command(f"scp '{video}' {user}@{host}:'{remote_path}'")
        
        if result is not None:
            print(f"Successfully transferred {video}")
            transferred.append({"local_path": video, "remote_path": f"/home/{user}/videos/{video_name}"})
        else:
            print(f"Failed to transfer {video}")
    
    return transferred

def transfer_auth_files(host, user, remote_dir):
    """Transfer authentication files to the Raspberry Pi."""
    auth_files = ["token.pickle", "client_secrets.json"]
    
    for auth_file in auth_files:
        if not os.path.exists(auth_file):
            print(f"Auth file not found: {auth_file}")
            continue
        
        print(f"Transferring {auth_file} to {host}:{remote_dir}...")
        
        result = run_command(f"scp '{auth_file}' {user}@{host}:'{remote_dir}/{auth_file}'")
        
        if result is not None:
            print(f"Successfully transferred {auth_file}")
        else:
            print(f"Failed to transfer {auth_file}")

def generate_titles(videos):
    """Generate simple titles for videos based on filenames."""
    titles = []
    
    for video in videos:
        basename = os.path.basename(video["local_path"])
        name, _ = os.path.splitext(basename)
        
        # Format the name nicely
        formatted_name = name.replace("_", " ").replace("-", " ")
        formatted_name = ' '.join(word.capitalize() for word in formatted_name.split())
        
        # Add a catchy prefix
        prefixes = ["Amazing", "Incredible", "Awesome", "Must-See", "Epic", "Stunning"]
        import random
        prefix = random.choice(prefixes)
        
        title = f"{prefix} {formatted_name} #Shorts"
        titles.append(title)
    
    return titles

def generate_descriptions(videos):
    """Generate simple descriptions for videos."""
    descriptions = []
    
    templates = [
        "Check out this amazing video! Don't forget to like and subscribe for more content like this.",
        "Watch until the end for a surprise! Like and subscribe for more awesome content.",
        "You won't believe what happens in this video! Like and subscribe for more amazing content.",
        "This is one of our best videos yet! Don't forget to like and subscribe for more.",
        "Incredibly satisfying to watch! Like and subscribe for more content like this."
    ]
    
    import random
    
    for _ in videos:
        description = random.choice(templates)
        descriptions.append(description)
    
    return descriptions

def schedule_uploads(videos, host, user, start_time=None, interval=6, privacy="unlisted"):
    """Schedule the transferred videos for upload on the Raspberry Pi."""
    # Set default start time if not provided
    if start_time is None:
        # Default: Start tomorrow at 12:00 PM
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        start_time = tomorrow.replace(hour=12, minute=0, second=0, microsecond=0)
    elif isinstance(start_time, str):
        start_time = datetime.datetime.fromisoformat(start_time)
    
    # Get the current schedule
    result = run_command(f"ssh {user}@{host} 'cat ~/.youtube_shorts_uploader/scheduled_uploads.json'")
    
    if result is None:
        print("Failed to get current schedule")
        result = '{"scheduled_uploads": []}'
    
    try:
        schedule = json.loads(result)
    except json.JSONDecodeError:
        print("Invalid schedule format, creating new schedule")
        schedule = {"scheduled_uploads": []}
    
    titles = generate_titles(videos)
    descriptions = generate_descriptions(videos)
    
    # Schedule each video
    current_time = start_time
    
    for i, video in enumerate(videos):
        upload = {
            "file_path": video["remote_path"],
            "title": titles[i],
            "description": descriptions[i],
            "tags": ["shorts", "youtube", "viral", "trending"],
            "scheduled_time": current_time.isoformat(),
            "privacy": privacy
        }
        
        schedule["scheduled_uploads"].append(upload)
        
        # Set the next upload time
        current_time += datetime.timedelta(hours=interval)
    
    # Save the updated schedule
    schedule_file = "/tmp/scheduled_uploads.json"
    with open(schedule_file, "w") as f:
        json.dump(schedule, f, indent=2)
    
    print(f"Transferring updated schedule to {host}...")
    result = run_command(f"scp '{schedule_file}' {user}@{host}:'~/.youtube_shorts_uploader/scheduled_uploads.json'")
    
    if result is not None:
        print(f"Successfully updated schedule on {host}")
        print(f"Scheduled {len(videos)} videos for upload, starting at {start_time.isoformat()}")
        print(f"Videos will be uploaded every {interval} hours")
    else:
        print("Failed to update schedule")

def main():
    """Main entry point for the transfer tool."""
    args = parse_arguments()
    
    # Check connection to the Raspberry Pi
    if not check_connection(args.host, args.user):
        return 1
    
    # Fix remote directory path
    remote_dir = args.dir.replace("~", f"/home/{args.user}")
    
    # Transfer authentication files if requested
    if args.auth:
        transfer_auth_files(args.host, args.user, remote_dir)
    
    # Transfer videos if provided
    transferred_videos = []
    if args.videos:
        transferred_videos = transfer_videos(args.videos, args.host, args.user, remote_dir)
    
    # Schedule uploads if requested
    if args.schedule and transferred_videos:
        schedule_uploads(transferred_videos, args.host, args.user, 
                        start_time=args.time, interval=args.interval, 
                        privacy=args.privacy)
    
    print("\nTransfer completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 