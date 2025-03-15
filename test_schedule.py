#!/usr/bin/env python
"""
Test script for the YouTube Shorts Uploader scheduler.
This script demonstrates how to use the scheduler to import a folder of videos
and schedule them for upload at specified intervals.
"""

import os
import sys
import logging
import datetime
from pathlib import Path

from youtube_shorts_uploader.core.account_manager import AccountManager
from youtube_shorts_uploader.core.scheduler import UploadScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test_scheduler")

def main():
    """Main test function for scheduler"""
    try:
        # Initialize the account manager
        account_manager = AccountManager()
        
        # Get the available accounts
        accounts = account_manager.get_accounts()
        
        if not accounts:
            logger.error("No YouTube accounts configured. Please add and authenticate accounts first.")
            return 1
        
        # Print available accounts
        print("Available accounts:")
        for i, account in enumerate(accounts):
            print(f"{i+1}. {account.get('name', 'Unknown')} (ID: {account.get('id')})")
        
        # Let user select an account
        selection = input("Select account number to use for scheduling: ")
        try:
            index = int(selection) - 1
            if index < 0 or index >= len(accounts):
                logger.error("Invalid selection.")
                return 1
            account = accounts[index]
        except ValueError:
            logger.error("Please enter a valid number.")
            return 1
        
        # Initialize the scheduler
        scheduler = UploadScheduler(account_manager)
        
        # Let user select a folder
        default_folder = str(Path.home() / "Desktop")
        folder_path = input(f"Enter path to folder with videos [{default_folder}]: ") or default_folder
        
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            logger.error(f"Invalid folder path: {folder_path}")
            return 1
        
        # Set scheduling parameters
        interval_hours = input("Enter hours between uploads [1]: ") or "1"
        try:
            interval_hours = int(interval_hours)
            if interval_hours < 1:
                interval_hours = 1
        except ValueError:
            interval_hours = 1
        
        # Get start time
        now = datetime.datetime.now()
        start_time_str = input(f"Enter start time (YYYY-MM-DD HH:MM) [{now.strftime('%Y-%m-%d %H:%M')}]: ") or now.strftime("%Y-%m-%d %H:%M")
        
        try:
            start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            logger.error("Invalid date format. Using current time + 5 minutes.")
            start_time = now + datetime.timedelta(minutes=5)
        
        # Schedule the uploads
        count = scheduler.import_folder(
            folder_path=folder_path,
            account_id=account['id'],
            interval_hours=interval_hours,
            start_time=start_time
        )
        
        if count > 0:
            print(f"\nSuccessfully scheduled {count} videos for upload!")
            print(f"First upload will start at {start_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"Videos will be uploaded every {interval_hours} hour(s)")
            
            # Show scheduled videos
            videos = scheduler.get_scheduled_videos()
            print("\nScheduled videos:")
            for i, video in enumerate(videos):
                scheduled_time = datetime.datetime.fromisoformat(video.get('scheduled_time', ''))
                print(f"{i+1}. {video.get('title')} - {scheduled_time.strftime('%Y-%m-%d %H:%M')}")
            
            # Keep the scheduler running
            print("\nScheduler is now running. Press Ctrl+C to exit.")
            try:
                # This will keep the scheduler thread running
                while True:
                    cmd = input("\nEnter 'status' to check status, 'cancel <id>' to cancel upload, or 'exit' to quit: ")
                    
                    if cmd.lower() == 'exit':
                        break
                    elif cmd.lower() == 'status':
                        videos = scheduler.get_scheduled_videos()
                        print("\nCurrent scheduled videos:")
                        for i, video in enumerate(videos):
                            scheduled_time = datetime.datetime.fromisoformat(video.get('scheduled_time', ''))
                            status = "Pending"
                            if video.get('uploaded', False):
                                status = f"Uploaded (ID: {video.get('video_id', 'Unknown')})"
                            elif video.get('cancelled', False):
                                status = "Cancelled"
                            elif 'error' in video:
                                status = f"Error: {video['error']}"
                            
                            print(f"{i+1}. {video.get('title')} - {scheduled_time.strftime('%Y-%m-%d %H:%M')} - {status}")
                    elif cmd.lower().startswith('cancel '):
                        try:
                            video_index = int(cmd.split(' ')[1]) - 1
                            if video_index >= 0 and video_index < len(videos):
                                video_id = videos[video_index]['id']
                                if scheduler.cancel_scheduled_video(video_id):
                                    print(f"Cancelled upload for video {video_index + 1}")
                                else:
                                    print("Failed to cancel upload")
                            else:
                                print("Invalid video index")
                        except (ValueError, IndexError):
                            print("Invalid command format. Use 'cancel <number>'")
                    else:
                        print("Unknown command")
            except KeyboardInterrupt:
                print("\nExiting scheduler...")
            finally:
                # Stop the scheduler
                scheduler.stop()
        else:
            logger.error("No videos were found or scheduled.")
            return 1
        
        return 0
    
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 