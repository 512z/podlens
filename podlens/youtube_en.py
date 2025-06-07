"""
YouTube related features
"""

import requests
from datetime import datetime, timedelta
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
    
    def _fix_encoding(self, text: str) -> str:
        """
        Smart encoding fix - precise Unicode escape sequence handling
        
        Args:
            text: Original text
            
        Returns:
            str: Fixed text
        """
        if not text:
            return text
            
        try:
            # Only process Unicode escape sequences like \u0026 -> &
            if '\\u' in text:
                import re
                # Use regex to precisely replace Unicode escape sequences
                def unicode_replacer(match):
                    try:
                        return match.group(0).encode().decode('unicode_escape')
                    except:
                        return match.group(0)
                
                # Only match and replace \uXXXX format Unicode escape sequences
                result = re.sub(r'\\u[0-9a-fA-F]{4}', unicode_replacer, text)
                return result
            
            # Otherwise return original string directly
            # Most of the time YouTube returns correct UTF-8 encoding
            return text
            
        except Exception:
            # If processing fails, return original text
            return text
    
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
                # Use intelligent encoding fix
                title = self._fix_encoding(title)
                return title
            else:
                return "YouTube Video"
        except Exception as e:
            print(f"Could not get video title: {e}")
            return "YouTube Video"

    def get_video_info(self, video_id: str) -> Dict:
        """
        Get video information: title, channel name, published date
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dict: Dictionary containing title, channel name, published date
        """
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            response = self.session.get(video_url, timeout=10)
            response.raise_for_status()
            
            import re
            
            # Extract title
            title = "Unknown Title"
            title_match = re.search(r'"title":"([^"]+)"', response.text)
            if title_match:
                title = title_match.group(1)
                title = self._fix_encoding(title)
            
            # Extract channel name
            channel_name = "Unknown Channel"
            # Try multiple patterns to extract channel name
            channel_patterns = [
                r'"channelName":"([^"]+)"',
                r'"author":"([^"]+)"',
                r'"ownerChannelName":"([^"]+)"',
                r'<link itemprop="name" content="([^"]+)">'
            ]
            
            for pattern in channel_patterns:
                channel_match = re.search(pattern, response.text)
                if channel_match:
                    channel_name = channel_match.group(1).strip()
                    # Smart encoding fix
                    channel_name = self._fix_encoding(channel_name)
                    break
            
            # Extract published date - usually relative time from page
            published_date = "Recent"
            
            return {
                'title': title,
                'channel_name': channel_name,
                'published_date': published_date,
                'video_id': video_id
            }
            
        except Exception as e:
            print(f"Failed to get video info: {e}")
            return {
                'title': "Unknown Title", 
                'channel_name': "Unknown Channel",
                'published_date': "Recent",
                'video_id': video_id
            }
    
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

    def parse_youtube_relative_time(self, time_str: str) -> str:
        """
        Parse YouTube relative time to specific date
        
        Args:
            time_str: YouTube time string like "14 hours ago", "2 days ago"
            
        Returns:
            str: Date in YYYY-MM-DD format
        """
        if not time_str or time_str in ['Recent', 'Unknown']:
            return datetime.now().strftime('%Y-%m-%d')
        
        # Normalize input
        time_str = time_str.lower().strip()
        
        # Match various time formats
        patterns = [
            (r'(\d+)\s*(second|minute|hour)s?\s*ago', 'hours'),
            (r'(\d+)\s*hours?\s*ago', 'hours'),
            (r'(\d+)\s*days?\s*ago', 'days'),
            (r'(\d+)\s*weeks?\s*ago', 'weeks'),
            (r'(\d+)\s*months?\s*ago', 'months'),
            (r'(\d+)\s*years?\s*ago', 'years'),
        ]
        
        now = datetime.now()
        
        for pattern, unit in patterns:
            match = re.search(pattern, time_str)
            if match:
                amount = int(match.group(1))
                
                if unit == 'hours':
                    target_date = now - timedelta(hours=amount)
                elif unit == 'days':
                    target_date = now - timedelta(days=amount)
                elif unit == 'weeks':
                    target_date = now - timedelta(weeks=amount)
                elif unit == 'months':
                    target_date = now - timedelta(days=amount * 30)  # approximate
                elif unit == 'years':
                    target_date = now - timedelta(days=amount * 365)  # approximate
                else:
                    target_date = now
                
                return target_date.strftime('%Y-%m-%d')
        
        # If unable to parse, return today's date
        return now.strftime('%Y-%m-%d')

    def create_episode_folder(self, channel_name: str, episode_title: str, published_date_str: str) -> Path:
        """
        Create YouTube episode folder (Apple Podcast style)
        
        Args:
            channel_name: Channel name
            episode_title: Episode title
            published_date_str: Published time string (like "14 hours ago")
            
        Returns:
            Path: Episode folder path
        """
        # Clean filenames
        safe_channel = self.sanitize_filename(channel_name)
        safe_title = self.sanitize_filename(episode_title)
        
        # Limit folder name lengths
        if len(safe_channel) > 50:
            safe_channel = safe_channel[:50]
        if len(safe_title) > 100:
            safe_title = safe_title[:100]
        
        # Parse date
        date_folder = self.parse_youtube_relative_time(published_date_str)
        
        # Create directory structure: outputs/channel_name/date/episode_name/
        channel_dir = self.output_dir / safe_channel
        date_dir = channel_dir / date_folder
        episode_dir = date_dir / safe_title
        
        # Create directories
        episode_dir.mkdir(parents=True, exist_ok=True)
        
        return episode_dir
    
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
    
    def download_youtube_audio(self, video_url: str, title: str, episode_dir: Path = None) -> Optional[Path]:
        """Download YouTube video audio using yt-dlp"""
        if not YT_DLP_AVAILABLE:
            print("❌ yt-dlp not available, cannot download audio")
            return None
        
        try:
            # Use episode directory if provided, otherwise use output directory
            download_dir = episode_dir if episode_dir else self.output_dir
            
            # Clean filename
            safe_title = self.sanitize_filename(title)
            audio_filename = self.ensure_filename_length("youtube_", safe_title)
            audio_filepath = download_dir / audio_filename
            
            # Check if file already exists
            if audio_filepath.exists():
                return audio_filepath
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(download_dir / f"youtube_{safe_title}.%(ext)s"),
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
            return audio_filepath
            
        except Exception as e:
            print(f"❌ Audio download failed: {e}")
            return None
    
    def compress_audio_file(self, input_file: Path, output_file: Path) -> bool:
        """Smart two-level audio compression below Groq API limit (copied from Apple section)
        Prefer 64k for quality, fallback to 48k if still >25MB"""
        try:
            print("🔧 Compressing...")
            
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
            
            if compressed_size_mb <= 25:
                # 64k compression meets requirement, use 64k result
                temp_64k_file.rename(output_file)
                return True
            else:
                # 64k compression still >25MB, perform second level 48k compression
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
            
            return {
                'text': text,
                'language': language,
                'processing_time': processing_time,
                'speed_ratio': speed_ratio,
                'method': 'Groq API whisper-large-v3'
            }
            
        except Exception as e:
            # print(f"❌ Groq transcription failed: {e}")
            return None
    
    def transcribe_with_mlx(self, audio_file: Path) -> dict:
        """Transcribe audio file using MLX Whisper (copied from Apple section)"""
        try:
            print("💻 Local transcription...")
            
            start_time = time.time()
            
            result = mlx_whisper.transcribe(
                str(audio_file),
                path_or_hf_repo=self.whisper_model_name
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            file_size_mb = self.get_file_size_mb(audio_file)
            speed_ratio = file_size_mb / processing_time * 60 if processing_time > 0 else 0
            
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
    
    def detect_chinese_content(self, text):
        """
        Detect the proportion of Chinese characters in text
        
        Args:
            text: Text to analyze
            
        Returns:
            float: Chinese character ratio (0.0 - 1.0)
        """
        if not text:
            return 0.0
        
        # Try to fix encoding issues
        try:
            # If garbled text, try to fix
            if '\\' in text or 'è' in text or 'ä' in text:
                try:
                    # Try different encoding fixes
                    fixed_text = text.encode('latin1').decode('utf-8')
                    text = fixed_text
                except:
                    pass
        except:
            pass
        
        # Chinese character ranges (including Chinese punctuation)
        import re
        chinese_pattern = r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3000-\u303f\uff00-\uffef]'
        chinese_chars = len(re.findall(chinese_pattern, text))
        total_chars = len(text.replace(' ', ''))  # Don't count spaces
        
        if total_chars == 0:
            return 0.0
        
        return chinese_chars / total_chars

    def smart_language_selection(self, available_transcripts, video_title="", channel_name="", threshold=0.3):
        """
        Smart transcript language selection
        
        Args:
            available_transcripts: List of available transcripts
            video_title: Video title
            channel_name: Channel name
            threshold: Chinese character ratio threshold
            
        Returns:
            (selected transcript object, language code, is_generated, reason)
        """
        # Analyze content language
        combined_text = f"{video_title} {channel_name}"
        chinese_ratio = self.detect_chinese_content(combined_text)
        
        # Analyze available subtitle languages
        available_languages = set()
        chinese_available = False
        english_available = False
        
        for trans in available_transcripts:
            lang = trans['language_code']
            available_languages.add(lang)
            if lang in ['zh', 'zh-CN', 'zh-TW', 'zh-Hans', 'zh-Hant']:
                chinese_available = True
            elif lang == 'en':
                english_available = True
        
        # Smart decision logic (running in background, no output)
        if chinese_ratio >= threshold:
            # Detected Chinese content
            if chinese_available:
                target_languages = ['zh', 'zh-CN', 'zh-TW', 'zh-Hans', 'zh-Hant']
                reason = f"Detected Chinese content ({chinese_ratio:.1%}), selecting Chinese subtitles"
            else:
                target_languages = ['en']
                reason = f"Detected Chinese content ({chinese_ratio:.1%}), but no Chinese subtitles available, selecting English"
        else:
            # No Chinese content detected
            if chinese_available and not english_available:
                target_languages = ['zh', 'zh-CN', 'zh-TW', 'zh-Hans', 'zh-Hant']
                reason = f"Although content appears non-Chinese ({chinese_ratio:.1%}), only Chinese subtitles available"
            else:
                target_languages = ['en']
                reason = f"Detected non-Chinese content ({chinese_ratio:.1%}), prioritizing English subtitles"
        
        # Priority: target language manual > target language auto > English manual > English auto > other manual > other auto
        priorities = []
        
        # Add target language priorities
        for lang in target_languages:
            priorities.append((lang, False))  # Manual subtitles
            priorities.append((lang, True))   # Auto-generated subtitles
        
        # If target is not English, add English as fallback
        if 'en' not in target_languages:
            priorities.append(('en', False))  # English manual
            priorities.append(('en', True))   # English auto
        
        # Add other language fallbacks
        priorities.append((None, False))  # Any manual subtitles
        priorities.append((None, True))   # Any auto-generated subtitles
        
        # Select by priority
        for target_lang, target_generated in priorities:
            for trans_info in available_transcripts:
                lang_code = trans_info['language_code']
                is_generated = trans_info['is_generated']
                
                if target_lang is None:  # Match any language
                    if is_generated == target_generated:
                        return trans_info['transcript'], lang_code, is_generated, f"Fallback: {lang_code}"
                elif lang_code == target_lang and is_generated == target_generated:
                    status = "auto" if is_generated else "manual"
                    return trans_info['transcript'], lang_code, is_generated, f"Best match: {lang_code}({status})"
        
        # If nothing found, return first
        if available_transcripts:
            first = available_transcripts[0]
            return first['transcript'], first['language_code'], first['is_generated'], "Default first"
        
        return None, None, None, "No subtitles found"

    def transcribe_audio_smart(self, audio_file: Path, title: str) -> Optional[str]:
        """Smart audio transcription: choose best method based on file size (copied and simplified from Apple section)"""
        if not (GROQ_AVAILABLE or MLX_WHISPER_AVAILABLE):
            print("❌ No available transcription service")
            return None
        
        try:
            # Check file size
            file_size_mb = self.get_file_size_mb(audio_file)
            
            groq_limit = 25  # MB
            transcript_result = None
            compressed_file = None
            
            # Smart transcription strategy
            if file_size_mb <= groq_limit and GROQ_AVAILABLE:
                # Case 1: File < 25MB, use Groq directly with MLX fallback
                transcript_result = self.transcribe_with_groq(audio_file)
                
                # Fallback to MLX if Groq fails
                if not transcript_result and MLX_WHISPER_AVAILABLE:
                    transcript_result = self.transcribe_with_mlx(audio_file)
            
            elif file_size_mb > groq_limit:
                # Case 2: File > 25MB, need compression
                
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
                    
                    if compressed_size <= groq_limit and GROQ_AVAILABLE:
                        # Case 2a: After compression, within Groq limit with MLX fallback
                        transcript_result = self.transcribe_with_groq(compressed_file)
                        
                        # Fallback to MLX if Groq fails
                        if not transcript_result and MLX_WHISPER_AVAILABLE:
                            transcript_result = self.transcribe_with_mlx(compressed_file)
                    else:
                        # Case 2b: Still over limit, use MLX
                        if MLX_WHISPER_AVAILABLE:
                            transcript_result = self.transcribe_with_mlx(compressed_file)
                        else:
                            print("❌ MLX Whisper not available, cannot transcribe large file")
                            return None
                else:
                    # Compression failed, try MLX
                    if MLX_WHISPER_AVAILABLE:
                        transcript_result = self.transcribe_with_mlx(audio_file)
                    else:
                        print("❌ MLX Whisper not available, transcription failed")
                        return None
            
            else:
                # Case 3: Groq not available, use MLX
                if MLX_WHISPER_AVAILABLE:
                    transcript_result = self.transcribe_with_mlx(audio_file)
                else:
                    print("❌ MLX Whisper not available, transcription failed")
                    return None
            
            # Handle transcription result
            if not transcript_result:
                print("❌ All transcription methods failed")
                return None
            
            # Clean up files silently
            try:
                # Delete original audio file
                audio_file.unlink()
                
                # Delete compressed file (if exists)
                if compressed_file and compressed_file.exists():
                    compressed_file.unlink()
                    
            except Exception as e:
                pass  # Silently ignore cleanup errors
            
            return transcript_result['text']
            
        except Exception as e:
            print(f"❌ Transcription process failed: {e}")
            return None
    
    def extract_youtube_transcript(self, video_id: str, video_url: str = None, title: str = "Unknown", episode_dir: Path = None) -> Optional[str]:
        """Extract transcript from YouTube video, with audio download fallback"""
        if not YOUTUBE_TRANSCRIPT_AVAILABLE:
            if video_url and YT_DLP_AVAILABLE:
                return self.audio_download_fallback(video_url, title, episode_dir)
            return None
        
        try:
            # Clean the video ID - remove any extra characters
            clean_video_id = video_id.strip()
            if len(clean_video_id) != 11:
                if video_url and YT_DLP_AVAILABLE:
                    return self.audio_download_fallback(video_url, title, episode_dir)
                return None
            
            # Enhanced retry mechanism with smart language selection
            max_retries = 20
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
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
                        continue
                    
                    # Smart language selection - automatically choose best transcript
                    selected_transcript, selected_lang, is_generated, reason = self.smart_language_selection(
                        available_transcripts, title, ""
                    )
                    
                    if not selected_transcript:
                        continue
                    
                    # Fetch the selected transcript
                    try:
                        transcript_data = selected_transcript.fetch()
                        
                        if not transcript_data:
                            # If selected transcript fails, try others
                            for trans_info in available_transcripts:
                                if trans_info['transcript'] == selected_transcript:
                                    continue
                                try:
                                    transcript_data = trans_info['transcript'].fetch()
                                    if transcript_data:
                                        break
                                except Exception as e:
                                    continue
                        
                        if not transcript_data:
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
                        
                        if text_parts:
                            full_text = " ".join(text_parts).strip()
                            if full_text:
                                return full_text
                        
                    except Exception as e3:
                        pass
                    
                except Exception as e2:
                    error_msg = str(e2)
                    
                    # Check for specific error types
                    if "no element found" in error_msg.lower():
                        continue
                    elif "not available" in error_msg.lower() or "disabled" in error_msg.lower():
                        break  # No point retrying
                    else:
                        continue
            
            # Fallback to audio download if transcript extraction failed
            if video_url and YT_DLP_AVAILABLE:
                return self.audio_download_fallback(video_url, title, episode_dir)
            else:
                return None
            
        except Exception as e:
            if video_url and YT_DLP_AVAILABLE:
                return self.audio_download_fallback(video_url, title, episode_dir)
            return None

    def audio_download_fallback(self, video_url: str, title: str, episode_dir: Path = None) -> Optional[str]:
        """Audio download and transcription fallback solution"""
        
        # Download audio to episode directory
        audio_file = self.download_youtube_audio(video_url, title, episode_dir)
        if not audio_file:
            return None
        
        # Transcribe audio
        transcript_text = self.transcribe_audio_smart(audio_file, title)
        return transcript_text
    
    def save_transcript(self, transcript: str, title: str, channel_name: str = None, published_date: str = None, episode_dir: Path = None) -> str:
        """
        Save transcript to file (supports new directory structure)
        
        Args:
            transcript: Transcript content
            title: Video title
            channel_name: Channel name (for new directory structure)
            published_date: Published date (for new directory structure)
            episode_dir: Episode directory (if already created)
            
        Returns:
            str: Saved file path
        """
        if episode_dir:
            # Use new directory structure: episode_dir is already complete path
            safe_channel = self.sanitize_filename(channel_name) if channel_name else ""
            safe_title = self.sanitize_filename(title)
            
            # Generate filename
            if safe_channel:
                content_part = f"{safe_channel}_{safe_title}"
            else:
                content_part = safe_title
            
            transcript_filename = self.ensure_output_filename_length("Transcript_", content_part, ".md")
            transcript_path = episode_dir / transcript_filename
        else:
            # Compatible with old version calls
            safe_title = self.sanitize_filename(title)
            transcript_path = self.output_dir / self.ensure_transcript_filename_length(safe_title)
        
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(f"# Transcript: {title}\n\n")
            if channel_name:
                f.write(f"**Channel:** {channel_name}\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
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
            except Exception as e:
                self.gemini_client = None
        else:
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
    
    def save_summary(self, summary: str, title: str, output_dir: Path, channel_name: str = None, episode_dir: Path = None) -> str:
        """
        Save summary to file (supports new directory structure)
        
        Args:
            summary: Summary content
            title: Video title
            output_dir: Output directory (compatibility parameter)
            channel_name: Channel name (for new directory structure)
            episode_dir: Episode directory (if already created)
            
        Returns:
            str: Saved file path
        """
        if episode_dir:
            # Use new directory structure: episode_dir is already complete path
            safe_channel = self.sanitize_filename(channel_name) if channel_name else ""
            safe_title = self.sanitize_filename(title)
            
            # Generate filename
            if safe_channel:
                content_part = f"{safe_channel}_{safe_title}"
            else:
                content_part = safe_title
            
            # Ensure filename doesn't exceed limits
            def ensure_length(prefix, content, extension, max_len=255):
                fixed_len = len(prefix) + len(extension)
                if len(content) + fixed_len <= max_len:
                    return f"{prefix}{content}{extension}"
                max_content = max_len - fixed_len
                truncated = content[:max_content]
                return f"{prefix}{truncated}{extension}"
            
            summary_filename = ensure_length("Summary_", content_part, ".md")
            summary_path = episode_dir / summary_filename
        else:
            # Compatible with old version calls
            safe_title = self.sanitize_filename(title)
            summary_path = output_dir / self.ensure_summary_filename_length(safe_title)
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(f"# Summary: {title}\n\n")
            if channel_name:
                f.write(f"**Channel:** {channel_name}\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
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
        
        while True:
            # 修改询问信息类型的提示
            print("\nSelect YouTube resource type:")
            print("- name: Channel name (@name)")
            print("- link: Video link")
            print("- script: Direct text content")
            print("\nExamples:")
            print("  name: lex fridman, or lexfridman (channel's @name)")
            print("  link: https://www.youtube.com/watch?v=qCbfTN-caFI (single video link)")
            print("  script: Place text content in scripts/script.txt")
            
            content_type = input("\nPlease select type (name/link/script) or enter 'quit' to exit: ").strip().lower()
            
            if content_type in ['quit', 'exit', 'q']:
                print("🔙 Back to main menu")
                break
            
            if content_type not in ['name', 'link', 'script']:
                print("Please select 'name', 'link', 'script' or 'quit'.")
                continue
            
            # Handle script input
            if content_type == 'script':
                # Look for script content in scripts/script.txt
                script_file_path = Path("scripts/script.txt")
                
                if not script_file_path.exists():
                    print("❌ Script file not found!")
                    print("Please create a file at scripts/script.txt")
                    print("Place your transcript content in that file and try again.")
                    continue
                
                try:
                    with open(script_file_path, 'r', encoding='utf-8') as f:
                        transcript = f.read().strip()
                    
                    if not transcript:
                        print("❌ Script file is empty.")
                        print("Please add your transcript content to scripts/script.txt")
                        continue
                    
                    print(f"✅ Successfully loaded script from scripts/script.txt ({len(transcript)} characters)")
                    
                except Exception as e:
                    print(f"❌ Error reading script file: {e}")
                    continue
                
                if len(transcript) < 50:
                    print("⚠️  Transcript content seems short, are you sure it's complete?")
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
                
                print(f"✅ Received script content ({len(transcript)} characters)")
                
                # 自动设置为获取转录文本和摘要
                want_transcripts = True
                want_summaries = True
            
            else:
                # Handle name/link input (existing logic)
                user_input = input(f"\nPlease enter {content_type}: ").strip()
                
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
                            print(f"🎥 Detected single video link: {user_input}")
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
                            print(f"🎥 Detected channel link: @{channel_name}")
                        else:
                            print("❌ Invalid YouTube channel link format.")
                            continue
                    else:
                        print("❌ Unsupported YouTube link format. Please use video link (youtube.com/watch?v=...) or channel videos link (youtube.com/@channel/videos)")
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
                            num_episodes = input("How many recent episodes would you like to see? (default: 5): ").strip()
                            if not num_episodes:
                                num_episodes = 5
                            else:
                                num_episodes = int(num_episodes)
                            
                            if num_episodes <= 0:
                                print("Please enter a positive integer.")
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
                    print(f"\n🔍 Searching YouTube for '{channel_name}' ...")
                    
                    episodes = self.searcher.search_youtube_podcast(channel_name, num_episodes)
                    
                    if not episodes:
                        print("❌ No relevant episodes found. Please try other search terms.")
                        continue
                    
                    # Display episodes with platform information
                    print(f"\n📋 Found {len(episodes)} latest episodes:")
                    for i, episode in enumerate(episodes, 1):
                        print(f"{i}. 🎥 [YouTube] '{episode['title']}' - {episode['published_date']}")
                    
                    # Get episode selection
                    episode_selection = input(f"\nWhich episodes are you interested in? (1-{len(episodes)}, e.g., '1,3,5' or '1-3' or 'all'): ").strip()
                    
                    if episode_selection.lower() == 'all':
                        selected_episodes = episodes
                    else:
                        try:
                            selected_indices = []
                            # Split by comma first
                            parts = episode_selection.split(',')
                            for part in parts:
                                part = part.strip()
                                if '-' in part:
                                    # Handle range format like "1-3"
                                    start, end = part.split('-', 1)
                                    start_idx = int(start.strip()) - 1
                                    end_idx = int(end.strip()) - 1
                                    selected_indices.extend(range(start_idx, end_idx + 1))
                                else:
                                    # Handle single number
                                    selected_indices.append(int(part) - 1)
                            
                            # Remove duplicates and filter valid indices
                            selected_indices = list(set(selected_indices))
                            valid_indices = [i for i in selected_indices if 0 <= i < len(episodes)]
                            
                            # If no valid indices after filtering, raise error
                            if not valid_indices:
                                raise ValueError("No valid episode indices")
                            
                            selected_episodes = [episodes[i] for i in sorted(valid_indices)]
                        except (ValueError, IndexError):
                            print("Invalid episode selection, please try again.")
                            continue
                    
                    if not selected_episodes:
                        print("No valid episodes selected.")
                        continue
                    
                    print(f"\n✅ Selected {len(selected_episodes)} episodes")
                
                # 自动设置为获取转录文本和摘要
                want_transcripts = True
                want_summaries = True
            
            # 英文版默认使用英文输出，不进行翻译
            want_chinese = False
            
            # 处理每个节目
            for episode in selected_episodes:
                print(f"\n🎥 Processing: {episode['title']}")
                print()  # 空行
                
                transcript_content = None
                episode_dir = None
                
                if episode['platform'] == 'script':
                    # Use the script content directly
                    transcript_content = transcript
                    print("⚡️ Ultra-fast transcription...")
                    print("✅ Transcription complete")
                    print()  # 空行
                else:
                    # Extract transcript from YouTube (existing logic)
                    video_id = episode.get('video_id')
                    if video_id:
                        # Get detailed video info to create episode directory
                        video_info = self.searcher.get_video_info(video_id)
                        channel_name = video_info.get('channel_name', 'Unknown_Channel')
                        
                        # Use the published_date from search results first, fallback to video info
                        published_date = episode.get('published_date', 'Unknown')
                        if published_date in ['Unknown', 'Recent']:
                            published_date = video_info.get('published_date', 'Recent')
                        
                        # Create episode directory using Apple Podcast style
                        episode_dir = self.extractor.create_episode_folder(
                            channel_name, 
                            episode['title'], 
                            published_date
                        )
                        
                        print("⚡️ Ultra-fast transcription...")
                        transcript_content = self.extractor.extract_youtube_transcript(
                            video_id, 
                            episode.get('url'), 
                            episode['title'],
                            episode_dir
                        )
                        if transcript_content:
                            print("✅ Transcription complete")
                            print()  # 空行
                    
                    # If no transcript available, create placeholder
                    if not transcript_content and (want_transcripts or want_summaries):
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
                        print("✅ Transcription complete")
                        print()  # 空行
                
                if not transcript_content:
                    print("❌ Unable to extract transcript for this episode")
                    continue
                
                # Save transcript if requested
                if want_transcripts and transcript_content:
                    if episode['platform'] == 'script':
                        # For script content, use default save method
                        transcript_path = self.extractor.save_transcript(transcript_content, episode['title'])
                    else:
                        # For YouTube content, use new directory structure
                        video_info = self.searcher.get_video_info(episode.get('video_id', ''))
                        channel_name = video_info.get('channel_name', 'Unknown_Channel')
                        
                        # Use published_date from search results first
                        published_date = episode.get('published_date', 'Unknown')
                        if published_date in ['Unknown', 'Recent']:
                            published_date = video_info.get('published_date', 'Recent')
                        
                        transcript_path = self.extractor.save_transcript(
                            transcript_content, 
                            episode['title'], 
                            channel_name, 
                            published_date, 
                            episode_dir
                        )
                
                # Generate and save summary if requested
                if want_summaries and transcript_content:
                    # Check if transcript has actual content (not just placeholder)
                    if len(transcript_content.strip()) > 100 and "Note: No transcript available" not in transcript_content:
                        print("🧠 Generating summary...")
                        summary = self.summarizer.generate_summary(transcript_content, episode['title'])
                        if summary:
                            # Translate summary to Chinese if requested
                            final_summary = summary
                            if want_chinese:
                                translated_summary = self.summarizer.translate_to_chinese(summary)
                                if translated_summary:
                                    final_summary = translated_summary
                                else:
                                    print("⚠️  Translation failed, using original summary")
                            
                            if episode['platform'] == 'script':
                                # For script content, use default save method
                                summary_path = self.summarizer.save_summary(
                                    final_summary, 
                                    episode['title'], 
                                    self.extractor.output_dir
                                )
                            else:
                                # For YouTube content, use new directory structure
                                video_info = self.searcher.get_video_info(episode.get('video_id', ''))
                                channel_name = video_info.get('channel_name', 'Unknown_Channel')
                                
                                summary_path = self.summarizer.save_summary(
                                    final_summary, 
                                    episode['title'], 
                                    self.extractor.output_dir,
                                    channel_name,
                                    episode_dir
                                )
                            print("✅ Summary complete")
                            print()  # 空行
                        else:
                            print("❌ Unable to generate summary")
                    else:
                        print("⚠️  Skipping summary - no valid transcript content")
            
            # Ask about visualization if any content was processed
            if selected_episodes:
                self.ask_for_visualization(selected_episodes, want_chinese)
            
            # Ask if the user wants to continue
            continue_choice = input("\nContinue in YouTube mode? (y/n): ").strip().lower()
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
        
        print(f"\n🎨 Visual story generation? (y/n):")
        visualize_choice = input().strip().lower()
        
        if visualize_choice not in ['y', 'yes']:
            return
        
        # 自动选择基于摘要生成
        content_choice = 's'
        
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
        
        print("\n🎨 Adding colors...")
        
        for i, episode in enumerate(processed_episodes, 1):
            if episode['platform'] == 'script':
                title = episode['title']
            else:
                title = episode['title']
            
            # For YouTube episodes, find the correct file in new directory structure
            if episode['platform'] == 'youtube':
                # Get episode directory path
                video_info = self.searcher.get_video_info(episode.get('video_id', ''))
                channel_name = video_info.get('channel_name', 'Unknown_Channel')
                published_date = episode.get('published_date', 'Recent')
                
                # Create episode directory path (same logic as in run method)
                episode_dir = self.extractor.create_episode_folder(
                    channel_name, 
                    episode['title'], 
                    published_date
                )
                
                # Use the same filename generation logic as save_transcript and save_summary
                safe_channel = self.extractor.sanitize_filename(channel_name) if channel_name else ""
                safe_title = self.extractor.sanitize_filename(episode['title'])
                
                # Generate content part (same logic as in save functions)
                if safe_channel:
                    content_part = f"{safe_channel}_{safe_title}"
                else:
                    content_part = safe_title
                
                if content_choice == 't':
                    # Use transcript - generate filename same as save_transcript
                    source_filename = self.extractor.ensure_output_filename_length("Transcript_", content_part, ".md")
                    content_type = "transcript"
                else:
                    # Use summary - generate filename same as save_summary
                    def ensure_length(prefix, content, extension, max_len=255):
                        fixed_len = len(prefix) + len(extension)
                        if len(content) + fixed_len <= max_len:
                            return f"{prefix}{content}{extension}"
                        max_content = max_len - fixed_len
                        truncated = content[:max_content]
                        return f"{prefix}{truncated}{extension}"
                    
                    source_filename = ensure_length("Summary_", content_part, ".md")
                    content_type = "summary"
                
                source_filepath = episode_dir / source_filename
            else:
                # For other platforms, use the old logic
                safe_title = re.sub(r'[^\w\s-]', '', title).strip()
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                
                if content_choice == 't':
                    source_filename = self.extractor.ensure_transcript_filename_length(safe_title)
                    content_type = "transcript"
                else:
                    source_filename = self.extractor.ensure_summary_filename_length(safe_title)
                    content_type = "summary"
                
                source_filepath = self.extractor.output_dir / source_filename
            
            if not source_filepath.exists():
                continue
            
            # Generate visual story
            if generate_visual_story(str(source_filepath)):
                visual_success_count += 1
        
        if visual_success_count > 0:
            print("✅ Visualization complete")