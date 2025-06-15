from dotenv import load_dotenv
load_dotenv()  # Load the .env file

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import uvicorn
import asyncio
from video_creator import VideoCreator
from youtube_uploader import YouTubeUploader
from metadata_generator import MetadataGenerator
import json
from datetime import datetime
import uuid

app = FastAPI(
    title="Type Beat Video Creator API",
    description="Create professional type beat videos with YouTube integration",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracking (use Redis in production)
jobs = {}

# Create necessary directories
directories = ['uploads', 'videos', 'user_credentials', 'temp']
for directory in directories:
    os.makedirs(directory, exist_ok=True)

class VideoRequest(BaseModel):
    beatName: str
    artistType: str
    producerName: Optional[str] = "Producer"
    userId: Optional[str] = "anonymous"

class JobStatus(BaseModel):
    jobId: str
    status: str
    progress: int
    message: str
    videoPath: Optional[str] = None
    youtubeUrl: Optional[str] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    return {
        "message": "🎬 Type Beat Video Creator API v2.0",
        "status": "running",
        "endpoints": {
            "create_video": "POST /video/create",
            "job_status": "GET /video/status/{job_id}",
            "youtube_connect": "GET /youtube/connect/{user_id}",
            "youtube_callback": "GET /youtube/callback",
            "youtube_status": "GET /youtube/status/{user_id}"
        },
        "features": [
            "Professional 1080p video creation",
            "YouTube OAuth integration",
            "Automatic video upload",
            "Real-time job tracking",
            "Professional metadata generation"
        ]
    }

@app.post("/video/create")
async def create_video(
    background_tasks: BackgroundTasks,
    beatName: str = Form(...),
    artistType: str = Form(...),
    producerName: str = Form("Producer"),
    userId: str = Form("anonymous"),
    audioFile: UploadFile = File(...),
    coverImage: UploadFile = File(...)
):
    """Create a professional type beat video"""
    try:
        print(f"🎬 Video creation request: {beatName} by {artistType}")
        
        # Validate file types
        if not audioFile.content_type or not audioFile.content_type.startswith(('audio/', 'application/')):
            raise HTTPException(status_code=400, detail="Invalid audio file type")
        
        if not coverImage.content_type or not coverImage.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Invalid image file type")
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job tracking
        jobs[job_id] = {
            "jobId": job_id,
            "status": "processing",
            "progress": 0,
            "message": "Starting video creation...",
            "createdAt": datetime.now().isoformat(),
            "beatName": beatName,
            "artistType": artistType,
            "producerName": producerName,
            "userId": userId
        }
        
        # Save uploaded files
        audio_path = f"uploads/{job_id}_audio_{audioFile.filename}"
        image_path = f"uploads/{job_id}_cover_{coverImage.filename}"
        
        with open(audio_path, "wb") as f:
            content = await audioFile.read()
            f.write(content)
        
        with open(image_path, "wb") as f:
            content = await coverImage.read()
            f.write(content)
        
        # Start background processing
        background_tasks.add_task(
            process_video_background,
            job_id, audio_path, image_path, {
                "beatName": beatName,
                "artistType": artistType,
                "producerName": producerName,
                "userId": userId
            }
        )
        
        return {
            "jobId": job_id,
            "status": "processing",
            "message": "Video creation started",
            "checkStatusUrl": f"/video/status/{job_id}"
        }
        
    except Exception as e:
        print(f"❌ Error in create_video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start video creation: {str(e)}")

@app.get("/video/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a video creation job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

@app.get("/youtube/connect/{user_id}")
async def youtube_connect(user_id: str):
    """Get YouTube OAuth URL for user authentication"""
    try:
        youtube_uploader = YouTubeUploader()
        auth_url = youtube_uploader.get_auth_url(user_id)
        
        return {
            "authUrl": auth_url,
            "message": "Visit this URL to authorize YouTube access",
            "userId": user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")

@app.get("/youtube/callback")
async def youtube_callback(code: str = None, state: str = None, error: str = None):
    """Handle YouTube OAuth callback"""
    if error:
        return HTMLResponse(f"""
            <html>
                <head><title>Authorization Failed</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2 style="color: #dc3545;">❌ Authorization Failed</h2>
                    <p>Error: {error}</p>
                </body>
            </html>
        """)
    
    if not code or not state:
        return HTMLResponse("""
            <html>
                <head><title>Error</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2 style="color: #dc3545;">❌ Error</h2>
                    <p>No authorization code received</p>
                </body>
            </html>
        """)
    
    try:
        youtube_uploader = YouTubeUploader()
        success = await youtube_uploader.exchange_code_for_tokens(code, state)
        
        if success:
            return HTMLResponse(f"""
                <html>
                    <head><title>YouTube Connected!</title></head>
                    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                        <h2 style="color: #28a745;">✅ YouTube Connected Successfully!</h2>
                        <p><strong>User:</strong> {state}</p>
                        <p>Your videos will now auto-upload to YouTube!</p>
                        <p><em>You can close this window and return to the video creator.</em></p>
                        <script>
                            setTimeout(() => window.close(), 3000);
                        </script>
                    </body>
                </html>
            """)
        else:
            raise Exception("Token exchange failed")
            
    except Exception as e:
        return HTMLResponse(f"""
            <html>
                <head><title>Connection Failed</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2 style="color: #dc3545;">❌ Connection Failed</h2>
                    <p>Failed to save YouTube credentials: {str(e)}</p>
                </body>
            </html>
        """)

@app.get("/youtube/status/{user_id}")
async def youtube_status(user_id: str):
    """Check YouTube connection status for a user"""
    creds_path = f"user_credentials/youtube_{user_id}.json"
    connected = os.path.exists(creds_path)
    
    return {
        "youtubeConnected": connected,
        "userId": user_id,
        "message": "YouTube is connected and ready" if connected else "YouTube not connected"
    }

async def process_video_background(job_id: str, audio_path: str, image_path: str, metadata: dict):
    """Background task for video processing"""
    try:
        print(f"🎬 Processing video for job {job_id}")
        
        # Update progress
        jobs[job_id]["progress"] = 10
        jobs[job_id]["message"] = "Preparing files..."
        
        # Generate video metadata
        metadata_gen = MetadataGenerator()
        video_metadata = metadata_gen.generate_metadata(
            metadata["artistType"],
            metadata["beatName"],
            producer_name=metadata["producerName"]
        )
        
        # Generate output path
        safe_filename = metadata["beatName"].replace(' ', '_').replace('/', '_')
        output_filename = f"{safe_filename}_{int(datetime.now().timestamp())}.mp4"
        output_path = f"videos/{output_filename}"
        
        jobs[job_id]["progress"] = 30
        jobs[job_id]["message"] = "Creating video..."
        
        # Create video
        video_creator = VideoCreator()
        result = await video_creator.create_video(
            audio_path, image_path, output_path, video_metadata["title"]
        )
        
        if not result["success"]:
            raise Exception(result["error"])
        
        jobs[job_id]["progress"] = 80
        jobs[job_id]["message"] = "Video created successfully!"
        jobs[job_id]["videoPath"] = output_path
        
        # Check for YouTube upload
        youtube_creds_path = f"user_credentials/youtube_{metadata['userId']}.json"
        if os.path.exists(youtube_creds_path):
            jobs[job_id]["progress"] = 90
            jobs[job_id]["message"] = "Uploading to YouTube..."
            
            # Upload to YouTube
            youtube_uploader = YouTubeUploader()
            upload_result = await youtube_uploader.upload_video(
                output_path, video_metadata, youtube_creds_path
            )
            
            if upload_result["success"]:
                jobs[job_id]["progress"] = 100
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["message"] = "Video uploaded to YouTube successfully!"
                jobs[job_id]["youtubeUrl"] = upload_result["video_url"]
                jobs[job_id]["videoId"] = upload_result["video_id"]
            else:
                jobs[job_id]["progress"] = 100
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["message"] = "Video created but YouTube upload failed"
                jobs[job_id]["youtubeError"] = upload_result["error"]
        else:
            jobs[job_id]["progress"] = 100
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["message"] = "Video created successfully (YouTube not connected)"
        
        # Cleanup temp files
        cleanup_files([audio_path, image_path])
        
    except Exception as e:
        print(f"❌ Video processing failed for job {job_id}: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        
        # Cleanup temp files even on failure
        cleanup_files([audio_path, image_path])

def cleanup_files(file_paths):
    """Clean up temporary files"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️ Cleaned up: {file_path}")
        except Exception as e:
            print(f"⚠️ Failed to cleanup {file_path}: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)