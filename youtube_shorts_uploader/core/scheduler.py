import os
import time
import json
import logging
import threading
import datetime
import queue
from pathlib import Path
import glob
import uuid

from .video_processor import VideoProcessor
from .youtube_api import YouTubeAPI
from ..utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class UploadScheduler:
    """
    Manages scheduled uploads of videos at specified intervals.
    Supports importing a folder of videos and scheduling them for upload.
    """
    
    def __init__(self, account_manager, config_dir=None):
        """
        Initialize the upload scheduler.
        
        Args:
            account_manager: The account manager for handling YouTube accounts
            config_dir (str, optional): Directory for storing schedule data
        """
        self.account_manager = account_manager
        self.config_dir = config_dir or os.path.join(str(Path.home()), '.youtube_shorts_uploader')
        self.schedule_file = os.path.join(self.config_dir, 'schedule.json')
        
        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Queue for scheduled uploads
        self.upload_queue = queue.PriorityQueue()
        
        # Threading controls
        self.scheduler_thread = None
        self.running = False
        self.lock = threading.Lock()
        
        # Load any existing schedule
        self.scheduled_videos = []
        self._load_schedule()
        
        logger.info("Upload scheduler initialized")
    
    def _load_schedule(self):
        """Load scheduled videos from file"""
        try:
            if os.path.exists(self.schedule_file):
                with open(self.schedule_file, 'r') as f:
                    data = json.load(f)
                    self.scheduled_videos = data.get('videos', [])
                    
                    # Add items to queue
                    for video in self.scheduled_videos:
                        if not video.get('uploaded', False):
                            # Calculate priority based on scheduled time
                            scheduled_time = datetime.datetime.fromisoformat(video.get('scheduled_time'))
                            priority = scheduled_time.timestamp()
                            self.upload_queue.put((priority, video))
                
                logger.info(f"Loaded {len(self.scheduled_videos)} scheduled videos")
            else:
                logger.info("No schedule file found, starting with empty schedule")
        except Exception as e:
            logger.error(f"Failed to load schedule: {str(e)}")
    
    def _save_schedule(self):
        """Save scheduled videos to file"""
        try:
            with open(self.schedule_file, 'w') as f:
                json.dump({'videos': self.scheduled_videos}, f, indent=2)
            logger.info(f"Saved {len(self.scheduled_videos)} scheduled videos")
            return True
        except Exception as e:
            logger.error(f"Failed to save schedule: {str(e)}")
            return False
    
    def import_folder(self, folder_path, account_id, interval_hours=1, start_time=None):
        """
        Import videos from a folder and schedule them for upload.
        
        Args:
            folder_path (str): Path to folder containing videos
            account_id (str): ID of the account to use for uploads
            interval_hours (int): Hours between uploads
            start_time (datetime): Starting time for first upload
            
        Returns:
            int: Number of videos imported and scheduled
        """
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            logger.error(f"Invalid folder path: {folder_path}")
            return 0
            
        # Initialize ConfigManager to get settings
        config_manager = ConfigManager()
        
        # Get style prompt from settings
        style_prompt = config_manager.get("style_prompt", "")
        if style_prompt:
            logger.info(f"Using style prompt for scheduled uploads: {style_prompt}")
            
        # Get video extensions from settings or use defaults
        valid_extensions = config_manager.get(
            "video_extensions", 
            [".mp4", ".mov", ".avi", ".mkv", ".webm"]
        )
        
        # Find all videos in the folder
        video_files = []
        for ext in valid_extensions:
            video_files.extend(glob.glob(os.path.join(folder_path, f"*{ext}")))
            video_files.extend(glob.glob(os.path.join(folder_path, f"*{ext.upper()}")))
        
        if not video_files:
            logger.warning(f"No video files found in {folder_path}")
            return 0
            
        # Sort files by name
        video_files.sort()
        
        # Initialize VideoProcessor
        video_processor = VideoProcessor()
        
        # Use current time if start_time not specified
        if start_time is None:
            start_time = datetime.datetime.now() + datetime.timedelta(minutes=5)
            
        # Process each video
        count = 0
        current_time = start_time
        
        for file_path in video_files:
            try:
                # Skip if not a file
                if not os.path.isfile(file_path):
                    continue
                    
                # Process video with style prompt
                logger.info(f"Processing {file_path} for scheduled upload")
                video_data = video_processor.process_video(
                    file_path,
                    sample_interval=5,
                    max_title_length=100,
                    style_prompt=style_prompt
                )
                
                # Create a scheduled upload entry
                upload_id = str(uuid.uuid4())
                upload_data = {
                    "id": upload_id,
                    "file_path": file_path,
                    "account_id": account_id,
                    "scheduled_time": current_time.isoformat(),
                    "title": video_data.get('title', os.path.basename(file_path)),
                    "description": video_data.get('description', ""),
                    "tags": video_data.get('hashtags', []),
                    "uploaded": False,
                    "cancelled": False
                }
                
                # Add to queue and schedule
                self.scheduled_videos.append(upload_data)
                self.upload_queue.put((current_time.timestamp(), upload_data))
                logger.info(f"Scheduled upload for {os.path.basename(file_path)} at {current_time.isoformat()}")
                
                # Move to next time slot
                current_time += datetime.timedelta(hours=interval_hours)
                count += 1
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
        
        # Save the schedule
        self._save_schedule()
        
        # Make sure the upload thread is running
        self._ensure_scheduler_running()
            
        return count
    
    def get_scheduled_videos(self):
        """
        Get list of all scheduled videos.
        
        Returns:
            list: Scheduled videos with status
        """
        with self.lock:
            return self.scheduled_videos.copy()
    
    def cancel_scheduled_video(self, video_id):
        """
        Cancel a scheduled video upload.
        
        Args:
            video_id (str): ID of the scheduled video to cancel
            
        Returns:
            bool: True if video was cancelled, False otherwise
        """
        with self.lock:
            for i, video in enumerate(self.scheduled_videos):
                if video['id'] == video_id and not video['uploaded']:
                    # Mark as cancelled but keep in history
                    self.scheduled_videos[i]['cancelled'] = True
                    self._save_schedule()
                    logger.info(f"Cancelled scheduled upload for {video['file_path']}")
                    return True
            
            logger.warning(f"No scheduled video found with ID {video_id}")
            return False
    
    def _ensure_scheduler_running(self):
        """Make sure the scheduler thread is running"""
        if not self.running or (self.scheduler_thread and not self.scheduler_thread.is_alive()):
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            logger.info("Scheduler thread started")
    
    def _scheduler_loop(self):
        """Main scheduler loop that processes the upload queue"""
        logger.info("Scheduler loop starting")
        
        while self.running:
            try:
                # Check if there's a video ready to upload
                now = datetime.datetime.now().timestamp()
                
                # Peek at the queue without removing
                if not self.upload_queue.empty():
                    priority, video = self.upload_queue.queue[0]
                    
                    # Is it time to upload?
                    if priority <= now:
                        # Get the item from the queue
                        priority, video = self.upload_queue.get()
                        
                        # Double-check it hasn't been cancelled
                        cancelled = False
                        for scheduled_video in self.scheduled_videos:
                            if scheduled_video['id'] == video['id']:
                                if scheduled_video.get('cancelled', False):
                                    cancelled = True
                                break
                        
                        if not cancelled:
                            # Process the upload
                            self._process_upload(video)
                        
                        # Mark task as done
                        self.upload_queue.task_done()
                    
                # Sleep for a while
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(30)  # Longer sleep after error
    
    def _process_upload(self, video):
        """
        Process a video upload.
        
        Args:
            video (dict): Video data including file path, title, etc.
            
        Returns:
            bool, str: Success status and video ID or error message
        """
        file_path = video.get('file_path')
        account_id = video.get('account_id')
        
        logger.info(f"Processing upload for {file_path}")
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False, "File not found"
            
            # Get account from account manager
            account = None
            for acc in self.account_manager.get_accounts():
                if acc.get('id') == account_id:
                    account = acc
                    break
            
            if not account:
                logger.error(f"Account {account_id} not found")
                return False, "Account not found"
            
            # Create YouTube API instance for this account
            from .auth_manager import AuthManager
            auth_manager = AuthManager(account_id)
            youtube_api = YouTubeAPI(auth_manager)
            
            # Get style prompt from settings
            config_manager = ConfigManager()
            style_prompt = config_manager.get("style_prompt", "")
            
            # Get title and description from video data or generate if not present
            title = video.get('title')
            description = video.get('description')
            tags = video.get('tags', [])
            
            # If title or description is missing, try to generate them
            if not title or not description:
                logger.info(f"Generating metadata for {file_path}")
                video_processor = VideoProcessor()
                
                # Process video with style prompt to generate metadata
                video_data = video_processor.process_video(
                    file_path,
                    sample_interval=5,
                    max_title_length=100,
                    style_prompt=style_prompt
                )
                
                title = title or video_data.get('title', os.path.basename(file_path))
                description = description or video_data.get('description', "")
                tags = tags or video_data.get('hashtags', [])
            
            # Upload the video
            response = youtube_api.upload_video(
                file_path,
                title,
                description,
                tags=tags,
                privacy_status=account.get('default_privacy', 'unlisted')
            )
            
            if response and 'id' in response:
                video_id = response['id']
                logger.info(f"Successfully uploaded {file_path} as {video_id}")
                return True, video_id
            else:
                logger.error(f"Upload failed for {file_path}, no video ID returned")
                return False, "No video ID returned"
                
        except Exception as e:
            logger.error(f"Error during upload process: {str(e)}")
            return False, str(e)
    
    def stop(self):
        """Stop the scheduler thread"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=2.0)
        logger.info("Scheduler stopped") 