import os
import cv2
import logging
import openai
import numpy as np
from ultralytics import YOLO
from collections import Counter
import tempfile
import subprocess
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Handles video processing, object detection, and metadata generation."""
    
    def __init__(self, openai_api_key=None, model_path=None):
        """
        Initialize the VideoProcessor.
        
        Args:
            openai_api_key (str): OpenAI API key. If None, it will be loaded from 
                                 environment variable OPENAI_API_KEY.
            model_path (str): Path to the YOLO model file. If None, it will use the default.
        """
        # Initialize OpenAI API key
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
            logger.info("OpenAI API key set successfully")
        else:
            logger.warning("OpenAI API key not provided or found in environment variables")
        
        # Initialize YOLO model
        self.model_path = model_path or "yolov8n.pt"
        self.model = None
        try:
            self.model = YOLO(self.model_path)
            logger.info(f"YOLO model loaded from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {str(e)}")
        
        # Store frame data for visualization and analysis
        self.extracted_frames = []
        self.last_video_thumbnail = None
    
    def set_openai_api_key(self, api_key):
        """
        Set the OpenAI API key.
        
        Args:
            api_key (str): The API key to use.
            
        Returns:
            bool: True if set successfully, False otherwise.
        """
        if not api_key:
            logger.warning("Empty API key provided")
            return False
            
        try:
            self.openai_api_key = api_key
            openai.api_key = api_key
            logger.info("OpenAI API key set successfully")
            return True
        except Exception as e:
            logger.error(f"Error setting OpenAI API key: {str(e)}")
            return False
    
    def detect_objects_in_video(self, video_path, sample_interval=5):
        """
        Detect objects in a video.
        
        Args:
            video_path (str): Path to the video file.
            sample_interval (int): Sample frames every N seconds for detection.
            
        Returns:
            list: List of detected objects (labels).
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return []
        
        if not self.model:
            logger.error("YOLO model not initialized")
            return []
        
        # Open the video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_path}")
            return []
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        logger.info(f"Video duration: {duration:.2f}s, FPS: {fps}")
        
        # Clear any previous frames
        self.extracted_frames = []
        
        frame_interval = int(fps * sample_interval)
        detected_labels = []
        
        try:
            frame_idx = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process only frames at specified intervals
                if frame_idx % frame_interval == 0:
                    # Store frame for thumbnail candidate
                    if frame_idx == int(frame_count / 2):  # Middle frame as thumbnail
                        self.last_video_thumbnail = frame.copy()
                    
                    # Store a copy of the frame
                    self.extracted_frames.append({
                        'frame': frame.copy(),
                        'time': frame_idx / fps,
                        'frame_idx': frame_idx
                    })
                    
                    # Detect objects in frame
                    results = self.model(frame)
                    
                    # Extract labels
                    for result in results:
                        for box in result.boxes:
                            label = result.names[int(box.cls[0])]
                            detected_labels.append(label)
                
                frame_idx += 1
        except Exception as e:
            logger.error(f"Error during object detection: {str(e)}")
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        logger.info(f"Detected {len(detected_labels)} objects in video")
        return detected_labels
    
    def extract_audio_transcript(self, video_path):
        """
        Extract audio transcript from a video using a simple speech-to-text approach.
        This is a placeholder that could be replaced with a proper speech recognition API.
        
        Args:
            video_path (str): Path to the video file.
            
        Returns:
            str: Extracted transcript or empty string if failed.
        """
        # This is a simplified version - in production you might want to use:
        # - Google Cloud Speech-to-Text
        # - OpenAI Whisper
        # - Mozilla DeepSpeech
        # For now, let's add a placeholder with mock transcript
        
        logger.info(f"Attempting to extract transcript from {video_path}")
        
        try:
            # Simplified approach - extract a few frames for context
            # This doesn't actually do speech recognition but is a placeholder
            video_filename = os.path.basename(video_path)
            name_without_ext = os.path.splitext(video_filename)[0]
            
            # In a real implementation, would invoke speech recognition here
            return f"This is a placeholder transcript for video {name_without_ext}."
        except Exception as e:
            logger.error(f"Failed to extract transcript: {str(e)}")
            return ""
    
    def generate_metadata(self, labels, video_path=None, max_title_length=100, style_prompt=None):
        """
        Generate title, description, and hashtags based on detected objects using GPT.
        
        Args:
            labels (list): List of detected object labels.
            video_path (str, optional): Path to the video for additional context.
            max_title_length (int): Maximum length of the title.
            style_prompt (str, optional): Custom style instructions for text generation.
            
        Returns:
            tuple: (title, description, hashtags) or (None, None, []) if generation failed.
        """
        if not self.openai_api_key:
            logger.error("OpenAI API key not set")
            return None, None, []
        
        if not labels:
            logger.warning("No labels provided for metadata generation")
            return None, None, []
        
        # Count the most common labels
        counter = Counter(labels)
        common_labels = counter.most_common(10)  # Get top 10 labels
        detection_text = ", ".join(f"{lbl}({count})" for lbl, count in common_labels)
        
        # Get video context if available
        video_context = ""
        if video_path:
            video_filename = os.path.basename(video_path)
            video_context = f"\nFilename: {video_filename}"
            
            # Add transcript if available
            transcript = self.extract_audio_transcript(video_path)
            if transcript:
                video_context += f"\nTranscript: {transcript}"
        
        # Define prompts
        system_prompt = """You are a YouTube Shorts metadata expert. Given a list of objects detected in a short video, 
        create an engaging title, description, and hashtags. Format your response exactly as:
        TITLE: [Your title here]
        DESCRIPTION: [Your description here]
        HASHTAGS: [comma-separated hashtags without the # symbol]
        
        Guidelines:
        - Titles should be catchy, engaging, and to the point (max 100 chars)
        - Descriptions should be 2-3 sentences that expand on the title
        - Include 5-7 relevant hashtags
        - Make titles and descriptions feel authentic and engaging, not AI-generated
        - Focus on trending topics and viral potential
        - Add emotional appeal or curiosity elements"""
        
        user_prompt = f"""Objects detected in video: {detection_text}{video_context}
        
        Create a catchy title (max {max_title_length} characters), engaging description (2-3 sentences), 
        and 5-7 relevant hashtags that will help this short go viral.
        
        Make sure to include the most prominent detected objects and interpret what might be happening in the video.
        Use a contemporary, social media friendly style that would appeal to YouTube Shorts viewers."""
        
        # Add custom style prompt if provided
        if style_prompt and style_prompt.strip():
            user_prompt += f"\n\nAdditional style instructions: {style_prompt}"
            logger.info(f"Using custom style prompt: {style_prompt}")
        
        try:
            logger.info("Generating metadata with GPT")
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response.choices[0].message.content
            logger.debug(f"GPT response: {content}")
            
            # Parse the response
            lines = content.strip().split('\n')
            title = ''
            description = ''
            hashtags = []
            
            for line in lines:
                if line.startswith('TITLE:'):
                    title = line[6:].strip()
                elif line.startswith('DESCRIPTION:'):
                    description = line[12:].strip()
                elif line.startswith('HASHTAGS:'):
                    hashtag_text = line[9:].strip()
                    # Split by comma and remove spaces
                    hashtags = [tag.strip() for tag in hashtag_text.split(',')]
            
            logger.info(f"Generated title: {title}")
            
            return title, description, hashtags
            
        except Exception as e:
            logger.error(f"Error generating metadata: {str(e)}")
            return None, None, []
    
    def generate_alternative_metadata(self, video_path, labels, num_alternatives=3, style_prompt=None):
        """
        Generate multiple alternative titles, descriptions, and hashtags for a video.
        
        Args:
            video_path (str): Path to the video file.
            labels (list): List of detected object labels.
            num_alternatives (int): Number of alternative metadata sets to generate.
            style_prompt (str, optional): Custom style instructions for text generation.
            
        Returns:
            list: List of dictionaries with 'title', 'description', and 'hashtags' keys.
        """
        if not self.openai_api_key or not labels:
            return []
        
        # Count the most common labels
        counter = Counter(labels)
        common_labels = counter.most_common(10)  # Get top 10 labels
        detection_text = ", ".join(f"{lbl}({count})" for lbl, count in common_labels)
        
        # Get video context
        video_filename = os.path.basename(video_path)
        
        system_prompt = f"""You are a YouTube Shorts metadata expert. Generate {num_alternatives} different
        title, description, and hashtag combinations for a short video.
        
        For each alternative, provide a different style/angle that might appeal to different audiences.
        Format your response exactly as a JSON array like this:
        [
            {{
                "title": "First title option",
                "description": "First description option",
                "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
            }},
            {{
                "title": "Second title option",
                "description": "Second description option",
                "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
            }}
        ]"""
        
        user_prompt = f"""Objects detected in video: {detection_text}
        Filename: {video_filename}
        
        Generate {num_alternatives} different metadata options for this YouTube Short.
        Make each option target a different audience or use a different style/angle.
        Keep titles under 100 characters and descriptions 2-3 sentences.
        Include 5-7 relevant hashtags per option (without the # symbol)."""
        
        # Add custom style prompt if provided
        if style_prompt and style_prompt.strip():
            user_prompt += f"\n\nAdditional style instructions: {style_prompt}"
            logger.info(f"Using custom style prompt for alternatives: {style_prompt}")
        
        try:
            logger.info(f"Generating {num_alternatives} alternative metadata options")
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            try:
                alternatives = json.loads(content)
                if isinstance(alternatives, list):
                    logger.info(f"Generated {len(alternatives)} metadata alternatives")
                    return alternatives
                else:
                    logger.error("Response was not a JSON array")
                    return []
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response")
                return []
            
        except Exception as e:
            logger.error(f"Error generating alternative metadata: {str(e)}")
            return []
    
    def extract_thumbnail_frame(self, video_path, position='middle'):
        """
        Extract a frame to use as thumbnail at specified position.
        
        Args:
            video_path (str): Path to the video file.
            position (str): Position to extract thumbnail from ('start', 'middle', 'end').
            
        Returns:
            numpy.ndarray: Extracted frame or None if failed.
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None
            
        # Open the video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_path}")
            return None
        
        try:
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Determine frame position
            target_frame = 0
            if position == 'middle':
                target_frame = frame_count // 2
            elif position == 'end':
                target_frame = max(0, frame_count - 10)  # 10 frames before end
            
            # Seek to target frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            # Read the frame
            ret, frame = cap.read()
            if ret:
                logger.info(f"Extracted thumbnail frame at position {target_frame}/{frame_count}")
                return frame
            else:
                logger.error("Failed to read frame for thumbnail")
                return None
        finally:
            cap.release()
    
    def process_video(self, video_path, sample_interval=5, max_title_length=100, style_prompt=None):
        """
        Process a video to detect objects and generate metadata.
        
        Args:
            video_path (str): Path to the video file.
            sample_interval (int): Sample frames every N seconds for detection.
            max_title_length (int): Maximum length of the title.
            style_prompt (str, optional): Custom style instructions for text generation.
            
        Returns:
            dict: Dictionary with 'title', 'description', 'labels', and 'hashtags'.
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return {
                'title': os.path.basename(video_path),
                'description': '',
                'labels': [],
                'hashtags': []
            }
        
        # Detect objects
        labels = self.detect_objects_in_video(video_path, sample_interval)
        
        # Extract video name as fallback title
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # Generate metadata
        title, description, hashtags = self.generate_metadata(labels, video_path, max_title_length, style_prompt)
        
        # If generation failed, use fallbacks
        if not title:
            title = video_name
        
        if not description:
            top_labels = [label for label, _ in Counter(labels).most_common(3)]
            description = f"Video featuring {', '.join(top_labels) if top_labels else 'content'}."
        
        result = {
            'title': title,
            'description': description,
            'labels': labels,
            'hashtags': hashtags,
            'thumbnail': self.last_video_thumbnail
        }
        
        # Generate alternative metadata
        alternatives = self.generate_alternative_metadata(video_path, labels, num_alternatives=3, style_prompt=style_prompt)
        if alternatives:
            result['alternatives'] = alternatives
        
        return result
