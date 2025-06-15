import asyncio
import subprocess
import json
import os
from PIL import Image
import tempfile

class VideoCreator:
    """Handle video creation using FFmpeg"""
    
    def __init__(self):
        self.temp_dir = "temp"
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def create_video(self, audio_path: str, image_path: str, output_path: str, title: str) -> dict:
        """Create a professional 1080p video from audio and image"""
        try:
            print(f"🎬 Creating video: {title}")
            
            # Process the cover image
            processed_image_path = await self._process_image(image_path)
            
            # Get audio duration
            duration = await self._get_audio_duration(audio_path)
            
            # Create video using FFmpeg
            result = await self._create_video_with_ffmpeg(
                audio_path, processed_image_path, output_path, duration
            )
            
            # Cleanup temporary image
            if os.path.exists(processed_image_path):
                os.remove(processed_image_path)
            
            return result
            
        except Exception as e:
            print(f"❌ Video creation failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _process_image(self, image_path: str) -> str:
        """Process cover image to 1080p format with professional layout"""
        try:
            # Open and process image
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create 1080p black background
                video_width = 1920
                video_height = 1080
                background = Image.new('RGB', (video_width, video_height), (0, 0, 0))
                
                # Make image square and crop from center
                min_dimension = min(img.size)
                left = (img.width - min_dimension) // 2
                top = (img.height - min_dimension) // 2
                right = left + min_dimension
                bottom = top + min_dimension
                img_square = img.crop((left, top, right, bottom))
                
                # Resize to fit nicely in 1080p frame (leave some padding)
                square_size = min(video_height - 100, video_width // 2)
                img_square = img_square.resize((square_size, square_size), Image.Resampling.LANCZOS)
                
                # Center the image
                x_offset = (video_width - square_size) // 2
                y_offset = (video_height - square_size) // 2
                background.paste(img_square, (x_offset, y_offset))
                
                # Save processed image
                processed_path = f"{self.temp_dir}/processed_cover_{os.path.basename(image_path)}.jpg"
                background.save(processed_path, "JPEG", quality=95)
                
                return processed_path
                
        except Exception as e:
            raise Exception(f"Image processing failed: {str(e)}")
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration using FFprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', audio_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"FFprobe failed: {stderr.decode()}")
            
            result = json.loads(stdout.decode())
            duration = float(result['format']['duration'])
            
            print(f"🎵 Audio duration: {duration:.2f} seconds")
            return duration
            
        except Exception as e:
            raise Exception(f"Failed to get audio duration: {str(e)}")
    
    async def _create_video_with_ffmpeg(self, audio_path: str, image_path: str, output_path: str, duration: float) -> dict:
        """Create video using FFmpeg"""
        try:
            # FFmpeg command for high-quality video creation
            cmd = [
                'ffmpeg', '-y',  # -y to overwrite output file
                '-loop', '1',
                '-i', image_path,
                '-i', audio_path,
                '-c:v', 'libx264',
                '-tune', 'stillimage',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-pix_fmt', 'yuv420p',
                '-shortest',
                '-movflags', '+faststart',
                output_path
            ]
            
            print(f"🎬 Running FFmpeg: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                raise Exception(f"FFmpeg failed: {error_msg}")
            
            # Verify output file exists and has reasonable size
            if not os.path.exists(output_path):
                raise Exception("Output video file was not created")
            
            file_size = os.path.getsize(output_path)
            if file_size < 1000:  # Less than 1KB is suspicious
                raise Exception("Output video file is too small")
            
            print(f"✅ Video created successfully: {output_path} ({file_size:,} bytes)")
            
            return {
                "success": True,
                "output_path": output_path,
                "file_size": file_size,
                "duration": duration
            }
            
        except Exception as e:
            raise Exception(f"FFmpeg video creation failed: {str(e)}")