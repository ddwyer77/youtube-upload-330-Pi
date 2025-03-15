import os
import sys
import pickle
import openai  # Import the openai library directly
import cv2  # OpenCV
from ultralytics import YOLO
import google.auth
import google.auth.transport.requests
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

#####################################
# 0. Set Your OpenAI API Key
#####################################
# Get API key from environment variable - more secure!
openai.api_key = os.getenv('OPENAI_API_KEY')

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

#####################################
# 1. Authentication
#####################################
def get_authenticated_service():
    credentials = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(google.auth.transport.requests.Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                "client_secrets.json", SCOPES
            )
            credentials = flow.run_local_server(
                port=8080, prompt="consent", authorization_prompt_message=""
            )
        with open("token.pickle", "wb") as token:
            pickle.dump(credentials, token)

    return googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


#####################################
# 2. YouTube Upload
#####################################
def upload_video(youtube, video_file, title, description, privacy_status):
    """
    Uploads a video to the authorized YouTube channel.
    """
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["test", "upload", "api"],
            "categoryId": "22"  # '22' is for People & Blogs category
        },
        "status": {
            "privacyStatus": privacy_status  # "public", "private", or "unlisted"
        }
    }

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=video_file  # local file path
    )

    response = None
    try:
        print(f"Uploading: {video_file} ...")
        response = request.execute()
        print("Upload successful!")
        print(f"Video ID: {response['id']}")
        print(f"Watch it here: https://www.youtube.com/watch?v={response['id']}")
    except googleapiclient.errors.HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
    return response


############################################
# 3. Object Detection with YOLO + OpenCV
############################################
def detect_objects_in_video(video_path, sample_interval=5):
    """
    Takes a video file path, samples frames every 'sample_interval' seconds,
    and runs object detection with YOLO.
    Returns a list of detected object labels (strings).
    """
    # Load YOLO model (nano version)
    model = YOLO("yolov8n.pt")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)  # frames per second
    frame_count = 0
    detected_labels = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Current time in seconds
        current_time = frame_count / fps

        # If we've hit the sample interval, run YOLO detection
        if int(current_time) % sample_interval == 0:
            results = model(frame)  # run object detection
            result = results[0]     # YOLOv8 returns a list; we take the first (batch of 1)

            # result.names = dictionary of class idx => label
            # result.boxes.cls = array of class indices
            classes = result.boxes.cls.tolist() if hasattr(result.boxes, 'cls') else []

            for class_idx in classes:
                label = result.names[int(class_idx)]
                detected_labels.append(label)

        frame_count += 1

    cap.release()
    cv2.destroyAllWindows()
    return detected_labels


############################################
# 4. Summarize Detections with GPT
############################################
def summarize_detections(labels):
    """
    Takes a list of detected labels and uses GPT to produce a creative title & description.
    """
    print("Labels received for processing:", labels)

    from collections import Counter
    counter = Counter(labels)
    common_labels = counter.most_common(5)
    detection_text = ", ".join(f"{lbl}({count})" for lbl, count in common_labels)

    system_prompt = """You are a YouTube metadata expert. Given a list of objects detected in a video, 
    create an engaging title and description. Format your response exactly as:
    TITLE: [Your title here]
    DESCRIPTION: [Your description here]"""

    user_prompt = f"""Objects detected in video: {detection_text}
    Create a catchy title (max 100 characters) and engaging description (2-3 sentences) that mentions these objects naturally."""

    try:
        print("Sending request to OpenAI...")

        # Use openai.ChatCompletion.create with the modern library usage
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        # Debug print the raw GPT response content
        content = response.choices[0].message.content
        print("Raw GPT response:", content)

        lines = content.strip().split('\n')
        title = ''
        description = ''

        for line in lines:
            if line.startswith('TITLE:'):
                title = line.replace('TITLE:', '').strip()
            elif line.startswith('DESCRIPTION:'):
                description = line.replace('DESCRIPTION:', '').strip()

        print(f"Parsed title: {title}")
        print(f"Parsed description: {description}")

        if not title or not description:
            print("Warning: Could not parse GPT response properly, using default values.")
            return "Untitled Video", "No description"

        return title, description

    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return "Untitled Video", "No description"


############################################
# 5. Main Script Flow
############################################
if __name__ == "__main__":
    # Verify OpenAI API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY not found in environment variables!")
        print("Please create a .env file with your OpenAI API key.")
        sys.exit(1)

    youtube_service = get_authenticated_service()

    folder_path = "/Users/danieldwyer/Documents/vids4upload"  # Update this path if needed
    video_extensions = (".mp4", ".mov", ".avi", ".mkv", ".flv")
    video_files = sorted(
        [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith(video_extensions)
        ]
    )

    if not video_files:
        print("No videos found in the folder. Exiting...")
        sys.exit(0)

    # Take the first video
    video_file_path = video_files[0]

    # --- Detect Objects ---
    print(f"Detecting scenes/objects in: {video_file_path}")
    labels = detect_objects_in_video(video_file_path, sample_interval=5)
    if not labels:
        print("No objects detected, or something went wrong. Using default metadata...")
        base_name = os.path.basename(video_file_path)
        title_without_ext = os.path.splitext(base_name)[0]
        video_title = f"{title_without_ext} (Auto-Uploaded)"
        video_description = "This video was uploaded via the YouTube Data API!"
    else:
        print(f"Objects found: {labels}")
        video_title, video_description = summarize_detections(labels)

    print("Generated Title:", video_title)
    print("Generated Description:", video_description)

    # --- Upload ---
    privacy = "public"  # You can change this to "private" or "unlisted"
    response = upload_video(
        youtube=youtube_service,
        video_file=video_file_path,
        title=video_title,
        description=video_description,
        privacy_status=privacy
    )

    # --- Delete if successful ---
    if response and "id" in response:
        print(f"Deleting file: {video_file_path}")
        os.remove(video_file_path)
        print("File deleted successfully!")
    else:
        print("Upload failed or could not retrieve video ID; file not deleted.")