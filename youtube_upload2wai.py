import os
import sys
import pickle
import openai
import cv2  # OpenCV
from ultralytics import YOLO
import google.auth
import google.auth.transport.requests
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

#####################################
# 0. Set Your OpenAI API Key
#####################################
# WARNING: This is insecure if you share or publish your code.
openai.api_key = "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"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

#####################################
# 1. Authentication (same as before)
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
# 2. YouTube Upload (same as before)
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
    # If you downloaded a local .pt, put the path, else 'yolov8n.pt' uses the default from ultralytics
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
# 4. Summarize Detections with GPT (Optional)
############################################
def summarize_detections(labels):
    """
    Takes a list of detected labels (e.g., ["person", "car", "dog"]) 
    and prompts GPT to produce a creative or descriptive title & description.
    """
    from collections import Counter
    counter = Counter(labels)
    common_labels = counter.most_common(5)
    # e.g. [("car", 10), ("person", 8), ...]

    # Convert that to a short bullet text
    detection_text = ", ".join(f"{lbl}({count})" for lbl, count in common_labels)
    prompt = (
        "You are a helpful AI that creates YouTube titles and descriptions.\n"
        "Here is a summary of objects detected in the video:\n"
        f"{detection_text}\n\n"
        "Please create:\n1) A short, catchy YouTube title.\n"
        "2) A brief YouTube description mentioning these objects.\n"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        content = response["choices"][0]["message"]["content"]
        lines = content.strip().splitlines()

        # Naive parse (better to request JSON in your prompt for easier extraction)
        title_line = next((l for l in lines if l.lower().startswith("1)")), "1) Untitled")
        desc_line = next((l for l in lines if l.lower().startswith("2)")), "2) No description")

        # Extract text after "1)" or "2)"
        def extract_after_number(line):
            parts = line.split(")", 1)
            return parts[1].strip() if len(parts) > 1 else line

        title = extract_after_number(title_line)
        description = extract_after_number(desc_line)
        return title, description

    except Exception as e:
        print("Error calling OpenAI API:", e)
        return "Untitled Video", "No description"


############################################
# 5. Main Script Flow
############################################
if __name__ == "__main__":
    youtube_service = get_authenticated_service()

    folder_path = "/Users/danieldwyer/Documents/vids4upload"
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
        # Summarize with GPT
        print(f"Objects found: {labels}")
        video_title, video_description = summarize_detections(labels)

    print("Generated Title:", video_title)
    print("Generated Description:", video_description)

    # --- Upload ---
    privacy = "public"
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