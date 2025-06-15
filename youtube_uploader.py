import os
import json
import aiohttp
from datetime import datetime
from typing import Dict, Optional

class YouTubeUploader:
    """Handle YouTube OAuth and video uploads"""
    
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('REDIRECT_URI', 'http://localhost:8000/youtube/callback')
        
        if not self.client_id or not self.client_secret:
            print("⚠️ Warning: YouTube OAuth credentials not configured")
    
    def get_auth_url(self, user_id: str) -> str:
        """Generate YouTube OAuth authorization URL"""
        base_url = "https://accounts.google.com/o/oauth2/auth"
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "https://www.googleapis.com/auth/youtube.upload",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "state": user_id
        }
        
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{base_url}?{param_string}"
        
        print(f"🔗 Generated auth URL for user {user_id}")
        return auth_url
    
    async def exchange_code_for_tokens(self, code: str, user_id: str) -> bool:
        """Exchange authorization code for access tokens"""
        try:
            token_url = "https://oauth2.googleapis.com/token"
            
            data = {
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data) as response:
                    tokens = await response.json()
                    
                    if "error" in tokens:
                        raise Exception(tokens.get("error_description", tokens["error"]))
                    
                    # Save credentials
                    creds_data = {
                        "access_token": tokens["access_token"],
                        "refresh_token": tokens.get("refresh_token"),
                        "token_type": tokens["token_type"],
                        "expires_in": tokens["expires_in"],
                        "scope": tokens["scope"],
                        "created_at": datetime.now().timestamp()
                    }
                    
                    creds_path = f"user_credentials/youtube_{user_id}.json"
                    with open(creds_path, 'w') as f:
                        json.dump(creds_data, f, indent=2)
                    
                    print(f"✅ YouTube credentials saved for user: {user_id}")
                    return True
                    
        except Exception as e:
            print(f"❌ Token exchange failed: {str(e)}")
            return False
    
    async def refresh_access_token(self, creds_path: str) -> Optional[str]:
        """Refresh expired access token"""
        try:
            with open(creds_path, 'r') as f:
                creds_data = json.load(f)
            
            if not creds_data.get("refresh_token"):
                raise Exception("No refresh token available")
            
            token_url = "https://oauth2.googleapis.com/token"
            
            data = {
                "refresh_token": creds_data["refresh_token"],
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data) as response:
                    refresh_data = await response.json()
                    
                    if "error" in refresh_data:
                        raise Exception(refresh_data.get("error_description", refresh_data["error"]))
                    
                    # Update stored credentials
                    creds_data["access_token"] = refresh_data["access_token"]
                    creds_data["created_at"] = datetime.now().timestamp()
                    if "expires_in" in refresh_data:
                        creds_data["expires_in"] = refresh_data["expires_in"]
                    
                    with open(creds_path, 'w') as f:
                        json.dump(creds_data, f, indent=2)
                    
                    print("🔄 Access token refreshed successfully")
                    return refresh_data["access_token"]
                    
        except Exception as e:
            print(f"❌ Token refresh failed: {str(e)}")
            return None
    
    async def upload_video(self, video_path: str, metadata: Dict, creds_path: str) -> Dict:
        """Upload video to YouTube"""
        try:
            print(f"🎥 Starting YouTube upload: {video_path}")
            
            # Load credentials
            if not os.path.exists(creds_path):
                return {"success": False, "error": "YouTube credentials not found"}
            
            with open(creds_path, 'r') as f:
                creds_data = json.load(f)
            
            # Check if token needs refresh
            now = datetime.now().timestamp()
            token_age = now - creds_data["created_at"]
            token_expired = token_age > creds_data["expires_in"]
            
            access_token = creds_data["access_token"]
            
            if token_expired:
                access_token = await self.refresh_access_token(creds_path)
                if not access_token:
                    return {"success": False, "error": "Failed to refresh access token"}
            
            # Upload video
            upload_url = "https://www.googleapis.com/upload/youtube/v3/videos"
            
            # First, initialize upload
            init_data = {
                "snippet": {
                    "title": metadata["title"],
                    "description": metadata["description"],
                    "tags": metadata["tags"],
                    "categoryId": "10"  # Music category
                },
                "status": {
                    "privacyStatus": "private"  # Change to "public" or "unlisted" as needed
                }
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Upload-Content-Type": "video/mp4"
            }
            
            async with aiohttp.ClientSession() as session:
                # Initialize resumable upload
                async with session.post(
                    f"{upload_url}?uploadType=resumable&part=snippet,status",
                    headers=headers,
                    json=init_data
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        return {"success": False, "error": f"Upload init failed: {error_text}"}
                    
                    upload_location = response.headers.get("location")
                    if not upload_location:
                        return {"success": False, "error": "No upload URL received"}
                
                # Upload video file
                with open(video_path, 'rb') as video_file:
                    video_data = video_file.read()
                
                upload_headers = {"Content-Type": "video/mp4"}
                
                async with session.put(upload_location, headers=upload_headers, data=video_data) as response:
                    if response.status not in [200, 201]:
                        error_text = await response.text()
                        return {"success": False, "error": f"Video upload failed: {error_text}"}
                    
                    upload_result = await response.json()
                    
                    if "id" not in upload_result:
                        return {"success": False, "error": "No video ID received from YouTube"}
                    
                    video_id = upload_result["id"]
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    print(f"✅ YouTube upload successful: {video_url}")
                    
                    return {
                        "success": True,
                        "video_id": video_id,
                        "video_url": video_url,
                        "title": metadata["title"]
                    }
                    
        except Exception as e:
            print(f"❌ YouTube upload error: {str(e)}")
            return {"success": False, "error": f"YouTube upload failed: {str(e)}"}