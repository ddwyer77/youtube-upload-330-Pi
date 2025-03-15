import os
import sys
import google.auth
import google.auth.transport.requests
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import pickle

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

def get_authenticated_service():
    """
    Returns an authorized YouTube API client service.
    Checks for existing credentials in token.pickle,
    otherwise starts the OAuth2 flow.
    """
    credentials = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            credentials = pickle.load(token)

    # If there are no valid credentials, go through OAuth flow
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

        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(credentials, token)

    return googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

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

if __name__ == "__main__":
    # 1. Build the authenticated service
    youtube_service = get_authenticated_service()

    # 2. Folder containing your videos
    folder_path = "/Users/danieldwyer/Documents/vids4upload"

    # 3. Get a sorted list of video files (any extension you want to include)
    video_extensions = (".mp4", ".mov", ".avi", ".mkv", ".flv")  # adjust as needed
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

    # 4. Pick the first video file in the list
    video_file_path = video_files[0]

    # 5. Generate a title from the filename (optional)
    #    Or you can just use a static title for all videos
    base_name = os.path.basename(video_file_path)
    title_without_ext = os.path.splitext(base_name)[0]
    video_title = f"{title_without_ext} (Auto-Uploaded)"
    video_description = "This video was uploaded via the YouTube Data API!"
    privacy = "public"  # choose "public", "unlisted", or "private"

    # 6. Upload the video
    response = upload_video(
        youtube=youtube_service,
        video_file=video_file_path,
        title=video_title,
        description=video_description,
        privacy_status=privacy
    )

    # 7. If upload was successful, delete the file
    if response and "id" in response:
        print(f"Deleting file: {video_file_path}")
        os.remove(video_file_path)
        print("File deleted successfully!")
    else:
        print("Upload failed or could not retrieve video ID; file not deleted.")