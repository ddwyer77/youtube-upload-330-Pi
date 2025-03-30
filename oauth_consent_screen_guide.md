# OAuth Consent Screen Configuration Guide

## Problem
Your app is showing an error because:
1. Your app is in testing mode in Google Cloud Console
2. The email you're using isn't authorized as a test user

## Solution: Add Your Email as a Test User

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (youtube-buddy-446605 or whatever you renamed it to)
3. Navigate to **APIs & Services** > **OAuth consent screen**
4. Scroll down to the "Test users" section
5. Click **ADD USERS**
6. Enter your email address (the one you want to authenticate with)
7. Click **SAVE**

## Alternative: Publishing Your App
If you're the only one using this app, you can also:

1. Go to **OAuth consent screen**
2. Change the publishing status from "Testing" to "In production"
3. Click through the verification process (may require additional verification steps)

## After Making Changes
After adding your email or publishing the app:

1. Run the authentication script again:
   ```
   python specific_auth.py
   ```
2. When the browser opens, use the same email you added as a test user
3. Accept the permissions

Once authorized, your app should work correctly with the YouTube API. 