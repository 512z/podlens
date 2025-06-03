"""
YouTube related features
"""

import requests
from datetime import datetime
from typing import List, Dict, Optional
import os
from pathlib import Path
import re
import time
import subprocess
from dotenv import load_dotenv
import google.generativeai as genai
import urllib.parse

# Enhanced .env loading function
def load_env_robust():
    """Load .env file from multiple possible locations"""
    # Try loading from current working directory first
    if load_dotenv():
        return True
    
    # Try loading from home directory
    home_env = Path.home() / '.env'
    if home_env.exists() and load_dotenv(home_env):
        return True
    
    return False

# Load .env file with robust search
load_env_robust()

# Whisper transcription support
try:
    import mlx_whisper
    import mlx.core as mx
    MLX_WHISPER_AVAILABLE = True
    MLX_DEVICE = mx.default_device()
    # print(f"🎯 MLX Whisper available, using device: {MLX_DEVICE}")
except ImportError:
    MLX_WHISPER_AVAILABLE = False
    # print("⚠️  MLX Whisper not available")

# Groq API ultra-fast transcription
try:
    from groq import Groq
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_AVAILABLE = bool(GROQ_API_KEY)
    # if GROQ_AVAILABLE:
    #     print(f"🚀 Groq API available, ultra-fast transcription enabled")
    # else:
    #     print("⚠️  Groq API key not set")
except ImportError:
    GROQ_AVAILABLE = False
    # print("⚠️  Groq SDK not installed")

# Gemini API summary support
try:
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# YouTube transcript extraction
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import TextFormatter
    YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError:
    YOUTUBE_TRANSCRIPT_AVAILABLE = False

# YouTube audio download fallback
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    print("⚠️  yt-dlp not installed, YouTube audio download fallback unavailable")

# Local Whisper free audio transcription (for YouTube)
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


# YouTube classes
class YouTubeSearcher:
    """Handles searching for podcasts on YouTube"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_video_title(self, video_id: str) -> str:
        """Get video title from video ID"""
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            response = self.session.get(video_url, timeout=10)
            response.raise_for_status()
            
            # Extract title from page
            import re
            title_match = re.search(r'"title":"([^"]+)"', response.text)
            if title_match:
                title = title_match.group(1)
                # Decode unicode escapes
                title = title.encode().decode('unicode_escape')
                return title
            else:
                return "YouTube Video"
        except Exception as e:
            print(f"Could not get video title: {e}")
            return "YouTube Video"
    
    def search_youtube_podcast(self, podcast_name: str, num_episodes: int = 5) -> List[Dict]:
        """Search for podcast episodes on YouTube using channel videos page"""
        try:
            # Convert podcast name to channel format
            # Remove spaces and convert to lowercase for channel name
            channel_name = podcast_name.lower().replace(' ', '')
            
            # Try the channel videos page first
            channel_url = f"https://www.youtube.com/@{channel_name}/videos"
            
            response = self.session.get(channel_url, timeout=10)
            response.raise_for_status()
            
            import re
            
            # Find all video IDs - YouTube orders them by recency on the channel page
            all_video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', response.text)
            
            videos = []
            seen_ids = set()
            
            # Just take the first N unique video IDs (most recent)
            for video_id in all_video_ids:
                if video_id in seen_ids:
                    continue
                
                seen_ids.add(video_id)
                
                # Try to find title and date for this video
                video_id_pattern = f'"videoId":"{video_id}"'
                start_pos = response.text.find(video_id_pattern)
                
                title = "Unknown Title"
                date = "Recent"
                
                if start_pos != -1:
                    # Look for title and date within a reasonable range of this video ID
                    search_start = max(0, start_pos - 500)
                    search_end = min(len(response.text), start_pos + 1500)
                    section = response.text[search_start:search_end]
                    
                    # Find title and date in this section
                    title_match = re.search(r'"title":\s*{"runs":\s*\[{"text":"([^"]+)"', section)
                    date_match = re.search(r'"publishedTimeText":\s*{"simpleText":"([^"]+)"', section)
                    
                    if title_match:
                        title = title_match.group(1)
                    if date_match:
                        date = date_match.group(1)
                
                videos.append({
                    'title': title.strip(),
                    'video_id': video_id,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'published_date': date.strip(),
                    'platform': 'youtube'
                })
                
                # Stop when we have enough videos
                if len(videos) >= num_episodes:
                    break
            
            # If we got videos from the channel, return them
            if videos:
                return videos
            
            # Fallback: if channel approach didn't work, try general search
            search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(podcast_name)}"
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            # Use the same approach for search results
            all_video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', response.text)
            
            videos = []
            seen_ids = set()
            
            for video_id in all_video_ids:
                if video_id in seen_ids:
                    continue
                
                seen_ids.add(video_id)
                
                # Try to find title and date for this video
                video_id_pattern = f'"videoId":"{video_id}"'
                start_pos = response.text.find(video_id_pattern)
                
                title = "Unknown Title"
                date = "Recent"
                
                if start_pos != -1:
                    # Look for title and date within a reasonable range of this video ID
                    search_start = max(0, start_pos - 500)
                    search_end = min(len(response.text), start_pos + 1500)
                    section = response.text[search_start:search_end]
                    
                    # Find title and date in this section
                    title_match = re.search(r'"title":\s*{"runs":\s*\[{"text":"([^"]+)"', section)
                    date_match = re.search(r'"publishedTimeText":\s*{"simpleText":"([^"]+)"', section)
                    
                    if title_match:
                        title = title_match.group(1)
                    if date_match:
                        date = date_match.group(1)
                
                videos.append({
                    'title': title.strip(),
                    'video_id': video_id,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'published_date': date.strip(),
                    'platform': 'youtube'
                })
                
                if len(videos) >= num_episodes:
                    break
            
            return videos
            
        except Exception as e:
            print(f"YouTube search failed: {e}")
            return []


class TranscriptExtractor:
    """Handles transcript extraction from YouTube"""
    
    def __init__(self, output_dir: str = "./outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create media folder for audio download fallback
        self.media_dir = Path("media")
        self.media_dir.mkdir(exist_ok=True)
        
        # Initialize session for downloads
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        # Initialize local Whisper model (preferred free option)
        self.whisper_model = None
        if WHISPER_AVAILABLE:
            try:
                self.whisper_model = whisper.load_model("base")
            except Exception as e:
                pass
        
        # Initialize MLX Whisper model name (copied from Apple section)
        self.whisper_model_name = 'mlx-community/whisper-medium'
        
        # Groq client initialization (copied from Apple section)
        if GROQ_AVAILABLE:
            self.groq_client = Groq(api_key=GROQ_API_KEY)
        else:
            self.groq_client = None
    
    def sanitize_filename(self, filename: str) -> str:
        """Clean filename, remove unsafe characters (copied from Apple section)"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = filename.strip('._')
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def ensure_filename_length(self, prefix: str, safe_title: str, extension: str = ".mp3") -> str:
        """
        Ensure the complete filename doesn't exceed filesystem limits (255 characters)
        
        Args:
            prefix: File prefix (e.g., "youtube_")
            safe_title: Sanitized title
            extension: File extension (default: .mp3)
        
        Returns:
            str: Final filename that fits within length limits
        """
        # Calculate the fixed parts: prefix and extension
        fixed_length = len(prefix) + len(extension)
        
        # Maximum available length for title
        max_title_length = 255 - fixed_length
        
        # If title fits, use it as is
        if len(safe_title) <= max_title_length:
            return f"{prefix}{safe_title}{extension}"
        
        # If too long, truncate the title
        truncated_title = safe_title[:max_title_length]
        final_filename = f"{prefix}{truncated_title}{extension}"
        
        return final_filename
    
    def get_file_size_mb(self, filepath):
        """Get file size (MB) (copied from Apple section)"""
        if not os.path.exists(filepath):
            return 0
        size_bytes = os.path.getsize(filepath)
        return size_bytes / (1024 * 1024)
    
    def download_youtube_audio(self, video_url: str, title: str) -> Optional[Path]:
        """Download YouTube video audio using yt-dlp"""
        if not YT_DLP_AVAILABLE:
            print("❌ yt-dlp not available, cannot download audio")
            return None
        
        try:
            # Clean filename
            safe_title = self.sanitize_filename(title)
            audio_filename = self.ensure_filename_length("youtube_", safe_title)
            audio_filepath = self.media_dir / audio_filename
            
            # Check if file already exists
            if audio_filepath.exists():
                print(f"⚠️  Audio file already exists: {audio_filename}")
                return audio_filepath
            
            print(f"📥 Downloading YouTube audio: {title}")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(self.media_dir / f"youtube_{safe_title}.%(ext)s"),
                'extractaudio': True,
                'audioformat': 'mp3',
                'audioquality': '192',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,  # Reduce output
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            print(f"✅ Audio download complete: {audio_filename}")
            return audio_filepath
            
        except Exception as e:
            print(f"❌ Audio download failed: {e}")
            return None
    
    def compress_audio_file(self, input_file: Path, output_file: Path) -> bool:
        """Smart two-level audio compression below Groq API limit (copied from Apple section)
        Prefer 64k for quality, fallback to 48k if still >25MB"""
        try:
            print(f"🔧 Compressing audio file: {input_file.name}")
            
            # First level compression: 64k (prioritize quality)
            print("📊 First level compression: 16KHz mono, 64kbps MP3")
            
            # Generate safe temporary filename that doesn't exceed 255 chars
            original_name = output_file.stem  # filename without extension
            prefix = "temp_64k_"
            extension = output_file.suffix
            
            # Calculate max length for original name part
            max_name_length = 255 - len(prefix) - len(extension)
            
            # Truncate original name if needed
            if len(original_name) > max_name_length:
                safe_name = original_name[:max_name_length]
            else:
                safe_name = original_name
            
            temp_64k_file = output_file.parent / f"{prefix}{safe_name}{extension}"
            
            cmd_64k = [
                'ffmpeg',
                '-i', str(input_file),
                '-ar', '16000',
                '-ac', '1',
                '-b:a', '64k',
                '-y',
                str(temp_64k_file)
            ]
            
            # Run first level compression
            result = subprocess.run(
                cmd_64k,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Check 64k compressed file size
            compressed_size_mb = self.get_file_size_mb(temp_64k_file)
            print(f"📊 64k compressed size: {compressed_size_mb:.1f}MB")
            
            if compressed_size_mb <= 25:
                # 64k compression meets requirement, use 64k result
                temp_64k_file.rename(output_file)
                print(f"✅ 64k compression complete: {output_file.name} ({compressed_size_mb:.1f}MB)")
                return True
            else:
                # 64k compression still >25MB, perform second level 48k compression
                print(f"⚠️  64k compression still >25MB, performing second level 48k compression...")
                print("📊 Second level compression: 16KHz mono, 48kbps MP3")
                
                cmd_48k = [
                    'ffmpeg',
                    '-i', str(input_file),
                    '-ar', '16000',
                    '-ac', '1',
                    '-b:a', '48k',
                    '-y',
                    str(output_file)
                ]
                
                # Run second level compression
                result = subprocess.run(
                    cmd_48k,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                final_size_mb = self.get_file_size_mb(output_file)
                print(f"✅ 48k compression complete: {output_file.name} ({final_size_mb:.1f}MB)")
                
                # Clean up temporary file
                if temp_64k_file.exists():
                    temp_64k_file.unlink()
                
                return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Compression failed: {e}")
            # Clean up temporary file
            if 'temp_64k_file' in locals() and temp_64k_file.exists():
                temp_64k_file.unlink()
            return False
        except Exception as e:
            print(f"❌ Compression error: {e}")
            # Clean up temporary file
            if 'temp_64k_file' in locals() and temp_64k_file.exists():
                temp_64k_file.unlink()
            return False
    
    def transcribe_with_groq(self, audio_file: Path) -> dict:
        """Transcribe audio file using Groq API (copied from Apple section)"""
        try:
            print(f"🚀 Groq API transcription: {audio_file.name}")
            print("🧠 Using model: whisper-large-v3")
            
            start_time = time.time()
            
            with open(audio_file, "rb") as file:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=file,
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    temperature=0.0
                )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            text = transcription.text if hasattr(transcription, 'text') else transcription.get('text', '')
            language = getattr(transcription, 'language', 'en') if hasattr(transcription, 'language') else transcription.get('language', 'en')
            
            file_size_mb = self.get_file_size_mb(audio_file)
            speed_ratio = file_size_mb / processing_time * 60 if processing_time > 0 else 0
            
            print(f"✅ Groq transcription complete! Time: {processing_time:.1f}s")
            
            return {
                'text': text,
                'language': language,
                'processing_time': processing_time,
                'speed_ratio': speed_ratio,
                'method': 'Groq API whisper-large-v3'
            }
            
        except Exception as e:
            print(f"❌ Groq transcription failed: {e}")
            return None
    
    def transcribe_with_mlx(self, audio_file: Path) -> dict:
        """Transcribe audio file using MLX Whisper (copied from Apple section)"""
        try:
            print(f"🎯 MLX Whisper transcription: {audio_file.name}")
            print("🧠 Using model: mlx-community/whisper-medium")
            
            start_time = time.time()
            
            result = mlx_whisper.transcribe(
                str(audio_file),
                path_or_hf_repo=self.whisper_model_name
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            file_size_mb = self.get_file_size_mb(audio_file)
            speed_ratio = file_size_mb / processing_time * 60 if processing_time > 0 else 0
            
            print(f"✅ MLX transcription complete! Time: {processing_time:.1f}s")
            
            return {
                'text': result['text'],
                'language': result.get('language', 'en'),
                'processing_time': processing_time,
                'speed_ratio': speed_ratio,
                'method': 'MLX Whisper medium'
            }
            
        except Exception as e:
            print(f"❌ MLX transcription failed: {e}")
            return None
    
    def transcribe_audio_smart(self, audio_file: Path, title: str) -> Optional[str]:
        """Smart audio transcription: choose best method based on file size (copied and simplified from Apple section)"""
        if not (GROQ_AVAILABLE or MLX_WHISPER_AVAILABLE):
            print("❌ No available transcription service")
            return None
        
        try:
            print(f"🎙️  Starting transcription: {title}")
            
            # Check file size
            file_size_mb = self.get_file_size_mb(audio_file)
            print(f"📊 Audio file size: {file_size_mb:.1f}MB")
            
            groq_limit = 25  # MB
            transcript_result = None
            compressed_file = None
            original_size = file_size_mb
            final_size = file_size_mb
            
            # Smart transcription strategy
            if file_size_mb <= groq_limit and GROQ_AVAILABLE:
                # Case 1: File < 25MB, use Groq directly with MLX fallback
                print("✅ File size within Groq limit, using ultra-fast transcription")
                transcript_result = self.transcribe_with_groq(audio_file)
                
                # Fallback to MLX if Groq fails
                if not transcript_result and MLX_WHISPER_AVAILABLE:
                    print("🔄 Groq failed, falling back to MLX Whisper...")
                    transcript_result = self.transcribe_with_mlx(audio_file)
            
            elif file_size_mb > groq_limit:
                # Case 2: File > 25MB, need compression
                print("⚠️  File exceeds Groq limit, starting compression...")
                
                # Generate safe compressed filename
                original_name = audio_file.stem
                compressed_name = f"compressed_{original_name}"
                extension = audio_file.suffix
                
                # Ensure compressed filename doesn't exceed limits
                max_compressed_length = 255 - len(extension)
                if len(compressed_name) > max_compressed_length:
                    # Truncate to fit
                    truncated_name = compressed_name[:max_compressed_length]
                    compressed_file = audio_file.parent / f"{truncated_name}{extension}"
                else:
                    compressed_file = audio_file.parent / f"{compressed_name}{extension}"
                
                if self.compress_audio_file(audio_file, compressed_file):
                    compressed_size = self.get_file_size_mb(compressed_file)
                    final_size = compressed_size
                    print(f"📊 Compressed size: {compressed_size:.1f}MB")
                    
                    if compressed_size <= groq_limit and GROQ_AVAILABLE:
                        # Case 2a: After compression, within Groq limit with MLX fallback
                        print("✅ After compression within Groq limit, using ultra-fast transcription")
                        transcript_result = self.transcribe_with_groq(compressed_file)
                        
                        # Fallback to MLX if Groq fails
                        if not transcript_result and MLX_WHISPER_AVAILABLE:
                            print("🔄 Groq failed, falling back to MLX Whisper...")
                            transcript_result = self.transcribe_with_mlx(compressed_file)
                    else:
                        # Case 2b: Still over limit, use MLX
                        print("⚠️  Still over limit after compression, using MLX transcription")
                        if MLX_WHISPER_AVAILABLE:
                            transcript_result = self.transcribe_with_mlx(compressed_file)
                        else:
                            print("❌ MLX Whisper not available, cannot transcribe large file")
                            return None
                else:
                    # Compression failed, try MLX
                    print("❌ Compression failed, trying local MLX transcription")
                    if MLX_WHISPER_AVAILABLE:
                        transcript_result = self.transcribe_with_mlx(audio_file)
                    else:
                        print("❌ MLX Whisper not available, transcription failed")
                        return None
            
            else:
                # Case 3: Groq not available, use MLX
                print("⚠️  Groq API not available, using local MLX transcription")
                if MLX_WHISPER_AVAILABLE:
                    transcript_result = self.transcribe_with_mlx(audio_file)
                else:
                    print("❌ MLX Whisper not available, transcription failed")
                    return None
            
            # Handle transcription result
            if not transcript_result:
                print("❌ All transcription methods failed")
                return None
            
            # Clean up files
            try:
                # Delete original audio file
                audio_file.unlink()
                print(f"🗑️  Deleted audio file: {audio_file.name}")
                
                # Delete compressed file (if exists)
                if compressed_file and compressed_file.exists():
                    compressed_file.unlink()
                    print(f"🗑️  Deleted compressed file: {compressed_file.name}")
                    
            except Exception as e:
                print(f"⚠️  Failed to delete file: {e}")
            
            return transcript_result['text']
            
        except Exception as e:
            print(f"❌ Transcription process failed: {e}")
            return None
    
    def extract_youtube_transcript(self, video_id: str, video_url: str = None, title: str = "Unknown") -> Optional[str]:
        """Extract transcript from YouTube video, with audio download fallback"""
        if not YOUTUBE_TRANSCRIPT_AVAILABLE:
            print("YouTube transcript API not available, trying audio download fallback...")
            if video_url and YT_DLP_AVAILABLE:
                return self.audio_download_fallback(video_url, title)
            return None
        
        try:
            # Clean the video ID - remove any extra characters
            clean_video_id = video_id.strip()
            if len(clean_video_id) != 11:
                print(f"Invalid video ID length: {len(clean_video_id)} (expected 11)")
                if video_url and YT_DLP_AVAILABLE:
                    return self.audio_download_fallback(video_url, title)
                return None
            
            print(f"🎯 Prefer YouTube transcript API: {clean_video_id}")
            
            # Try multiple times in case of network issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        print(f"  Retry attempt {attempt + 1}/{max_retries}...")
                        import time
                        time.sleep(2)  # Wait 2 seconds between retries
                    
                    # List available transcripts
                    transcript_list = YouTubeTranscriptApi.list_transcripts(clean_video_id)
                    
                    available_transcripts = []
                    for transcript in transcript_list:
                        available_transcripts.append({
                            'transcript': transcript,
                            'language_code': transcript.language_code,
                            'language_name': transcript.language,
                            'is_generated': transcript.is_generated,
                            'is_translatable': transcript.is_translatable
                        })
                    
                    if not available_transcripts:
                        print(f"  No available transcripts found in attempt {attempt + 1}")
                        continue
                    
                    print(f"  Found {len(available_transcripts)} transcript languages:")
                    for i, trans_info in enumerate(available_transcripts, 1):
                        status = "auto-generated" if trans_info['is_generated'] else "manual captions"
                        translatable = "translatable" if trans_info['is_translatable'] else "not translatable"
                        print(f"    {i}. {trans_info['language_code']} - {trans_info['language_name']} ({status}, {translatable})")
                    
                    # If only one transcript available, use it directly
                    if len(available_transcripts) == 1:
                        selected_transcript = available_transcripts[0]['transcript']
                        print(f"  Only one transcript available, auto-selecting: {available_transcripts[0]['language_code']}")
                    else:
                        # Multiple transcripts available, let user choose
                        print(f"\n  Multiple transcript languages detected, please choose:")
                        for i, trans_info in enumerate(available_transcripts, 1):
                            status = "auto-generated" if trans_info['is_generated'] else "manual captions"
                            print(f"    {i}. {trans_info['language_code']} - {trans_info['language_name']} ({status})")
                        
                        while True:
                            try:
                                choice = input(f"  Please select transcript language (1-{len(available_transcripts)}), or press Enter to use first: ").strip()
                                
                                if not choice:
                                    # Default to first option
                                    selected_index = 0
                                    print(f"  Using default selection: {available_transcripts[0]['language_code']}")
                                    break
                                else:
                                    selected_index = int(choice) - 1
                                    if 0 <= selected_index < len(available_transcripts):
                                        print(f"  Selected: {available_transcripts[selected_index]['language_code']} - {available_transcripts[selected_index]['language_name']}")
                                        break
                                    else:
                                        print(f"  Please enter a number between 1 and {len(available_transcripts)}")
                                        continue
                            except ValueError:
                                print(f"  Please enter a valid number (1-{len(available_transcripts)})")
                                continue
                        
                        selected_transcript = available_transcripts[selected_index]['transcript']
                    
                    # Fetch the selected transcript
                    try:
                        print(f"  Fetching transcript: {selected_transcript.language_code}")
                        transcript_data = selected_transcript.fetch()
                        
                        if not transcript_data:
                            print(f"    No data returned for {selected_transcript.language_code}")
                            # If selected transcript fails, try others
                            print("  Trying other available transcripts...")
                            for trans_info in available_transcripts:
                                if trans_info['transcript'] == selected_transcript:
                                    continue
                                try:
                                    print(f"  Fallback transcript: {trans_info['language_code']}")
                                    transcript_data = trans_info['transcript'].fetch()
                                    if transcript_data:
                                        print(f"  Fallback transcript success: {trans_info['language_code']}")
                                        break
                                except Exception as e:
                                    print(f"    Fallback transcript {trans_info['language_code']} failed: {e}")
                                    continue
                        
                        if not transcript_data:
                            print(f"  Attempt {attempt + 1}: All transcripts failed")
                            continue
                        
                        # Extract text - handle different possible formats
                        text_parts = []
                        for entry in transcript_data:
                            if hasattr(entry, 'text'):
                                # FetchedTranscriptSnippet objects
                                text_parts.append(entry.text)
                            elif isinstance(entry, dict) and 'text' in entry:
                                # Dictionary format
                                text_parts.append(entry['text'])
                            elif hasattr(entry, '__dict__') and 'text' in entry.__dict__:
                                # Object with text attribute
                                text_parts.append(entry.__dict__['text'])
                            else:
                                print(f"    Warning: Unknown segment format: {type(entry)}")
                        
                        if text_parts:
                            full_text = " ".join(text_parts).strip()
                            if full_text:
                                print(f"✅ YouTube transcript API success! ({len(full_text)} characters)")
                                return full_text
                            else:
                                print(f"    Empty text after joining")
                        else:
                            print(f"    No text parts extracted")
                        
                    except Exception as e3:
                        error_msg = str(e3)
                        print(f"    Failed to fetch selected transcript: {error_msg}")
                        
                        # Check for specific error types
                        if "no element found" in error_msg.lower():
                            print(f"    This appears to be an XML parsing error, possibly temporary")
                        elif "not available" in error_msg.lower():
                            print(f"    This transcript is not available")
                        else:
                            print(f"    Unexpected error type: {type(e3)}")
                    
                    # If we get here, selected transcript failed
                    print(f"  Attempt {attempt + 1} failed")
                    
                except Exception as e2:
                    error_msg = str(e2)
                    print(f"  Failed to list transcripts (attempt {attempt + 1}): {error_msg}")
                    
                    # Check for specific error types
                    if "no element found" in error_msg.lower():
                        print(f"    XML parsing error - this might be temporary, retrying...")
                        continue
                    elif "not available" in error_msg.lower() or "disabled" in error_msg.lower():
                        print(f"    Video transcripts are disabled or unavailable")
                        break  # No point retrying
                    else:
                        print(f"    Unexpected error: {type(e2)}")
                        if attempt == max_retries - 1:  # Last attempt
                            import traceback
                            print(f"    Full traceback:")
                            traceback.print_exc()
                        continue
            
            print("❌ YouTube transcript API failed, trying audio download fallback...")
            # Fallback to audio download if transcript extraction failed
            if video_url and YT_DLP_AVAILABLE:
                return self.audio_download_fallback(video_url, title)
            else:
                print("❌ Audio download fallback not available")
                return None
            
        except Exception as e:
            print(f"Error extracting YouTube transcript: {e}")
            print("🔄 Trying audio download fallback...")
            if video_url and YT_DLP_AVAILABLE:
                return self.audio_download_fallback(video_url, title)
            return None
    
    def audio_download_fallback(self, video_url: str, title: str) -> Optional[str]:
        """Audio download and transcription fallback solution"""
        print("🎵 Starting audio download fallback solution...")
        
        # Download audio
        audio_file = self.download_youtube_audio(video_url, title)
        if not audio_file:
            return None
        
        # Transcribe audio
        transcript_text = self.transcribe_audio_smart(audio_file, title)
        return transcript_text
    
    def save_transcript(self, transcript: str, title: str) -> str:
        """Save transcript to file"""
        # Build path
        safe_title = self.sanitize_filename(title)
        transcript_path = self.output_dir / self.ensure_transcript_filename_length(safe_title)
        
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(f"# Transcript: {title}\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(transcript)
        
        return str(transcript_path)

    def ensure_output_filename_length(self, prefix: str, safe_title: str, extension: str = ".md") -> str:
        """
        Ensure output filenames (transcript/summary) don't exceed filesystem limits (255 characters)
        YouTube format: prefix + title + extension (no channel)
        
        Args:
            prefix: File prefix (e.g., "Transcript_", "Summary_")
            safe_title: Sanitized title
            extension: File extension (default: .md)
        
        Returns:
            str: Final filename that fits within length limits
        """
        # Calculate fixed parts length: prefix + extension
        fixed_length = len(prefix) + len(extension)
        
        # Maximum available length for content
        max_content_length = 255 - fixed_length
        
        if len(safe_title) <= max_content_length:
            return f"{prefix}{safe_title}{extension}"
        else:
            truncated_title = safe_title[:max_content_length]
            return f"{prefix}{truncated_title}{extension}"
    
    def ensure_transcript_filename_length(self, safe_title: str) -> str:
        """Ensure transcript filename length"""
        return self.ensure_output_filename_length("Transcript_", safe_title)
    
    def ensure_summary_filename_length(self, safe_title: str) -> str:
        """Ensure summary filename length"""
        return self.ensure_output_filename_length("Summary_", safe_title)


class SummaryGenerator:
    """Handles summary generation using new Gemini API for YouTube"""
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.gemini_client = None
        
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.gemini_client = genai
                print("✅ Gemini API initialized successfully for YouTube!")
            except Exception as e:
                print(f"⚠️  Error initializing Gemini client: {e}")
                self.gemini_client = None
        else:
            if not self.api_key:
                print("Please add your Gemini API key to the .env file")
            self.gemini_client = None
    
    def generate_summary(self, transcript: str, title: str) -> Optional[str]:
        """Generate summary from transcript using new Gemini API"""
        if not self.gemini_client:
            print("Gemini API not available or API key not configured")
            return None
        
        try:
            prompt = f"""
            Please provide a comprehensive summary of this podcast episode transcript.
            
            Episode Title: {title}
            
            Include:
            1. Main topics outline (in sequence)
            2. Comprehensive and detailed summary on each section sequentially
            3. Key insights and takeaways
            4. Important quotes or statements
            5. key terminology/jargon explanation
            6. Overall themes, and the logic of the opinions expressed in the podcast
            7. Critical thinking and analysis for this podcast, reasoning from first principles
            
            Transcript:
            {transcript}
            """
            
            print("Generating summary...")
            response = self.gemini_client.GenerativeModel("gemini-2.5-flash-preview-05-20").generate_content(prompt)
            
            # Handle the response properly
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                print("Unexpected response format from Gemini API")
                return None
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return None
    
    def translate_to_chinese(self, text: str) -> Optional[str]:
        """Translate text to Chinese using Gemini API"""
        if not self.gemini_client:
            print("Gemini API not available or API key not configured")
            return None
        
        try:
            prompt = f"Translate everything to Chinese accurately without missing anything:\n\n{text}"
            
            response = self.gemini_client.GenerativeModel("gemini-2.5-flash-preview-05-20").generate_content(prompt)
            
            # Handle the response properly
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                print("Unexpected response format from Gemini API")
                return None
            
        except Exception as e:
            print(f"Error translating to Chinese: {e}")
            return None
    
    def sanitize_filename(self, filename: str) -> str:
        """Clean filename, remove unsafe characters"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = filename.strip('._')
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def ensure_summary_filename_length(self, safe_title: str) -> str:
        """Ensure summary filename length"""
        # Calculate fixed parts length: prefix + extension
        prefix = "Summary_"
        extension = ".md"
        fixed_length = len(prefix) + len(extension)
        
        # Maximum available length for content
        max_content_length = 255 - fixed_length
        
        if len(safe_title) <= max_content_length:
            return f"{prefix}{safe_title}{extension}"
        else:
            truncated_title = safe_title[:max_content_length]
            return f"{prefix}{truncated_title}{extension}"
    
    def save_summary(self, summary: str, title: str, output_dir: Path) -> str:
        """Save summary to file"""
        # Sanitize filename
        safe_title = self.sanitize_filename(title)
        summary_path = output_dir / self.ensure_summary_filename_length(safe_title)
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(f"# Summary: {title}\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(summary)
        
        return str(summary_path)


class Podnet:
    """Main application class for YouTube processing"""
    
    def __init__(self):
        self.searcher = YouTubeSearcher()
        self.extractor = TranscriptExtractor()
        self.summarizer = SummaryGenerator()
    
    def run(self):
        """Main application loop for YouTube"""
        print("🎥 Welcome to Podnet - Your YouTube Podcast Assistant Tool!")
        print("=" * 50)
        
        while True:
            # First ask what type of information the user wants to provide
            print("\nWhat type of information are you interested in?")
            print("- name: podcast/channel name")
            print("- link: YouTube video or channel link") 
            print("- script: direct transcript content")
            print("\nExamples:")
            print("  name: lex fridman, or lexfridman (the @username of the channel)")
            print("  link: https://www.youtube.com/watch?v=qCbfTN-caFI (for a single video)")
            print("  script: put text content in scripts/script.txt")
            
            content_type = input("\nChoose type (name/link/script) or 'quit' to exit: ").strip().lower()
            
            if content_type in ['quit', 'exit', 'q']:
                print("🔙 Back to main menu")
                break
            
            if content_type not in ['name', 'link', 'script']:
                print("Please choose 'name', 'link', 'script', or 'quit'.")
                continue
            
            # Handle script input
            if content_type == 'script':
                # Look for script content in scripts/script.txt
                script_file_path = Path("scripts/script.txt")
                
                if not script_file_path.exists():
                    print("❌ Script file not found!")
                    print("Please create a file at: scripts/script.txt")
                    print("Put your transcript content in that file and try again.")
                    continue
                
                try:
                    with open(script_file_path, 'r', encoding='utf-8') as f:
                        transcript = f.read().strip()
                    
                    if not transcript:
                        print("❌ The script file is empty.")
                        print("Please add your transcript content to scripts/script.txt")
                        continue
                    
                    print(f"✅ Successfully loaded script from scripts/script.txt ({len(transcript)} characters)")
                    
                except Exception as e:
                    print(f"❌ Error reading script file: {e}")
                    continue
                
                if len(transcript) < 50:
                    print("⚠️  The transcript seems very short. Are you sure this is complete?")
                    confirm = input("Continue anyway? (y/n): ").strip().lower()
                    if confirm not in ['y', 'yes']:
                        continue
                
                # Create episode object for script
                selected_episodes = [{
                    'title': f"Custom Script {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    'video_id': None,
                    'url': None,
                    'published_date': datetime.now().strftime('%Y-%m-%d'),
                    'platform': 'script'
                }]
                
                print(f"✅ Script content received ({len(transcript)} characters)")
                
                # Skip to action selection
                want_transcripts = True  # Always save transcript for script
                want_summaries = True   # Always generate summary for script
            
            else:
                # Handle name/link input (existing logic)
                user_input = input(f"\nPlease enter the {content_type}: ").strip()
                
                if not user_input:
                    print(f"Please enter a {content_type}.")
                    continue
                
                # Check if input is a YouTube link
                is_single_video = False
                is_channel_link = False
                episodes = []
                
                if content_type == 'link' and ("youtube.com" in user_input or "youtu.be" in user_input):
                    # Handle YouTube links
                    if "/watch?v=" in user_input:
                        # Single video link
                        is_single_video = True
                        # Extract video ID from link
                        import re
                        video_id_match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', user_input)
                        if video_id_match:
                            video_id = video_id_match.group(1)
                            # Create episode object for single video
                            episodes = [{
                                'title': self.searcher.get_video_title(video_id),
                                'video_id': video_id,
                                'url': f"https://www.youtube.com/watch?v={video_id}",
                                'published_date': 'Unknown',
                                'platform': 'youtube'
                            }]
                            print(f"🎥 Single video detected: {user_input}")
                        else:
                            print("❌ Invalid YouTube video link format.")
                            continue
                    elif "/@" in user_input and "/videos" in user_input:
                        # Channel videos link
                        is_channel_link = True
                        # Extract channel name from link
                        channel_match = re.search(r'/@([^/]+)', user_input)
                        if channel_match:
                            channel_name = channel_match.group(1)
                            print(f"🎥 Channel link detected: @{channel_name}")
                        else:
                            print("❌ Invalid YouTube channel link format.")
                            continue
                    else:
                        print("❌ Unsupported YouTube link format. Please use video links (youtube.com/watch?v=...) or channel videos links (youtube.com/@channel/videos)")
                        continue
                elif content_type == 'link':
                    print("❌ Please provide a valid YouTube link.")
                    continue
                else:
                    # Regular name input - use existing logic
                    channel_name = user_input
                
                if is_single_video:
                    # Skip episode selection for single video
                    selected_episodes = episodes
                    print(f"\n✅ Processing single video")
                else:
                    # Ask how many recent episodes the user wants (for name or channel link)
                    while True:
                        try:
                            num_episodes = input("How many recent podcasts do you want to see? (default: 5): ").strip()
                            if not num_episodes:
                                num_episodes = 5
                            else:
                                num_episodes = int(num_episodes)
                            
                            if num_episodes <= 0:
                                print("Please enter a positive number.")
                                continue
                            elif num_episodes > 20:
                                print("Maximum 20 episodes allowed.")
                                continue
                            else:
                                break
                        except ValueError:
                            print("Please enter a valid number.")
                            continue
                    
                    # Search for episodes on YouTube
                    print(f"\n🔍 Searching YouTube for '{channel_name}'...")
                    
                    episodes = self.searcher.search_youtube_podcast(channel_name, num_episodes)
                    
                    if not episodes:
                        print("❌ No episodes found. Please try a different search term.")
                        continue
                    
                    # Display episodes with platform information
                    print(f"\n📋 Found {len(episodes)} recent episodes:")
                    for i, episode in enumerate(episodes, 1):
                        print(f"{i}. 🎥 [YouTube] '{episode['title']}' - {episode['published_date']}")
                    
                    # Get episode selection FIRST
                    episode_selection = input(f"\nWhich episodes are you interested in? (1-{len(episodes)}, e.g., '1,3,5' or 'all'): ").strip()
                    
                    if episode_selection.lower() == 'all':
                        selected_episodes = episodes
                    else:
                        try:
                            selected_indices = [int(x.strip()) - 1 for x in episode_selection.split(',')]
                            selected_episodes = [episodes[i] for i in selected_indices if 0 <= i < len(episodes)]
                        except (ValueError, IndexError):
                            print("Invalid episode selection. Please try again.")
                            continue
                    
                    if not selected_episodes:
                        print("No valid episodes selected.")
                        continue
                    
                    print(f"\n✅ Selected {len(selected_episodes)} episode(s)")
                
                # THEN ask what to do with selected episodes (only for name/link)
                print("\nWhat would you like to do with the selected episodes?")
                print("1. Get transcripts of the episodes")
                print("2. Get summaries of the episodes")
                print("3. Get both transcripts and summaries")
                
                action = input("Your choice (1, 2, or 3): ").strip()
                
                if action not in ['1', '2', '3']:
                    print("Please select a valid option (1, 2, or 3)")
                    continue
                
                # Parse action
                want_transcripts = action in ['1', '3']
                want_summaries = action in ['2', '3']
            
            # Ask for language preference (common for all types)
            language = input("\nWhat language would you like the output to be? (en/ch): ").strip().lower()
            want_chinese = language == 'ch'
            
            # Process selected episodes
            print(f"\n🚀 Processing {len(selected_episodes)} episode(s)...")
            
            for episode in selected_episodes:
                print(f"\n📝 Processing {f'📜 [Script]' if episode['platform'] == 'script' else '🎥 [YouTube]'}: {episode['title']}")
                
                transcript_content = None
                
                if episode['platform'] == 'script':
                    # Use the script content directly
                    transcript_content = transcript
                    print("✅ Script content loaded successfully!")
                else:
                    # Extract transcript from YouTube (existing logic)
                    video_id = episode.get('video_id')
                    if video_id:
                        transcript_content = self.extractor.extract_youtube_transcript(
                            video_id, 
                            episode.get('url'), 
                            episode['title']
                        )
                        if transcript_content:
                            print("✅ YouTube transcript extracted successfully!")
                    
                    # If no transcript available, create placeholder
                    if not transcript_content and (want_transcripts or want_summaries):
                        print("⚠️  No YouTube transcript available for this video")
                        print("   This video may not have auto-generated captions")
                        # Create a placeholder transcript for YouTube videos without captions
                        transcript_content = f"""# {episode['title']}

Published: {episode['published_date']}
Platform: YouTube
Video URL: {episode.get('url', 'Not available')}

---

Note: No transcript available for this YouTube video.
The video may not have auto-generated captions.

You can:
1. Try other episodes from this creator
2. Check if captions are available manually on YouTube
3. Request the creator to add captions
"""
                        print("✅ Created episode info (no transcript available)")
                
                if not transcript_content:
                    print("❌ Could not extract transcript for this episode")
                    continue
                
                # Save transcript if requested
                if want_transcripts and transcript_content:
                    transcript_path = self.extractor.save_transcript(transcript_content, episode['title'])
                    print(f"💾 Transcript saved to: {transcript_path}")
                
                # Generate and save summary if requested
                if want_summaries and transcript_content:
                    # Check if transcript has actual content (not just placeholder)
                    if len(transcript_content.strip()) > 100 and "Note: No transcript available" not in transcript_content:
                        summary = self.summarizer.generate_summary(transcript_content, episode['title'])
                        if summary:
                            # Translate summary to Chinese if requested
                            final_summary = summary
                            if want_chinese:
                                print("🔄 Translating summary to Chinese...")
                                translated_summary = self.summarizer.translate_to_chinese(summary)
                                if translated_summary:
                                    final_summary = translated_summary
                                    print("✅ Summary translated to Chinese!")
                                else:
                                    print("⚠️  Translation failed, using original summary")
                            
                            summary_path = self.summarizer.save_summary(
                                final_summary, 
                                episode['title'], 
                                self.extractor.output_dir
                            )
                            print(f"📄 Summary saved to: {summary_path}")
                        else:
                            print("❌ Could not generate summary")
                    else:
                        print("⚠️  Skipping summary - no transcript content available")
                
                print("✅ Episode processing complete!")
            
            print(f"\n🎉 All done! Files saved in: {self.extractor.output_dir}")
            
            # Ask about visualization if any content was processed
            if selected_episodes:
                self.ask_for_visualization(selected_episodes, want_chinese)
            
            # Ask if the user wants to continue
            continue_choice = input("\nstay in youtube? (y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes', 'yes']:
                print("🔙 Back to main menu")
                break
    
    def ask_for_visualization(self, processed_episodes: List[Dict], want_chinese: bool):
        """
        Ask user if they want to generate visual stories
        
        Args:
            processed_episodes: List of processed episodes
            want_chinese: Whether to use Chinese
        """
        if not processed_episodes:
            return
        
        print(f"\n🎨 Visual Story Generation:")
        visualize_choice = input("Visualize the story? (y/n): ").strip().lower()
        
        if visualize_choice not in ['y', 'yes']:
            return
        
        # Ask whether to use transcript or summary
        print("📄 Content source:")
        content_choice = input("Visualize based on transcript or summary? (t/s): ").strip().lower()
        
        if content_choice not in ['t', 's']:
            print("Invalid choice. Skipping visualization.")
            return
        
        # Import visual module based on language
        try:
            if want_chinese:
                from .visual_ch import generate_visual_story
            else:
                from .visual_en import generate_visual_story
        except ImportError:
            visual_module = "visual_ch.py" if want_chinese else "visual_en.py"
            print(f"❌ Visual module not found. Please ensure {visual_module} is in the podlens folder.")
            return
        
        # Process each episode
        visual_success_count = 0
        
        for i, episode in enumerate(processed_episodes, 1):
            if episode['platform'] == 'script':
                title = episode['title']
            else:
                title = episode['title']
            
            print(f"\n[{i}/{len(processed_episodes)}] Generating visual story: {title}")
            
            # Build file paths - using the same naming pattern as save functions
            # Use the same sanitization logic as save_transcript and save_summary
            safe_title = re.sub(r'[^\w\s-]', '', title).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            
            if content_choice == 't':
                # Use transcript
                source_filename = self.extractor.ensure_transcript_filename_length(safe_title)
                content_type = "transcript"
            else:
                # Use summary
                source_filename = self.extractor.ensure_summary_filename_length(safe_title)
                content_type = "summary"
            
            source_filepath = self.extractor.output_dir / source_filename
            
            if not source_filepath.exists():
                print(f"❌ {content_type.capitalize()} file not found: {source_filename}")
                continue
            
            # Generate visual story
            if generate_visual_story(str(source_filepath)):
                visual_success_count += 1
                print(f"✅ Visual story generated successfully!")
            else:
                print(f"❌ Failed to generate visual story")
        
        print(f"\n📊 Visual story generation complete! Success: {visual_success_count}/{len(processed_episodes)}")
        if visual_success_count > 0:
            print(f"📁 Visual stories saved in: {self.extractor.output_dir.absolute()}")