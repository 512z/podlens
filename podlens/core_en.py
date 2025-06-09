#!/usr/bin/env python3
"""
PodLens Core Classes - Core classes optimized for automation
"""

import os
import sys
import re
import json
import time
import subprocess
import contextlib
import io
import requests
import feedparser
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from tqdm import tqdm

# Enhanced .env loading function
def load_env_robust():
    """Load .env file from multiple possible locations"""
    if load_dotenv():
        return True
    home_env = Path.home() / '.env'
    if home_env.exists() and load_dotenv(home_env):
        return True
    return False

load_env_robust()

# API Keys
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_AVAILABLE = bool(GROQ_API_KEY)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_AVAILABLE = bool(GEMINI_API_KEY)

# Initialize API clients
if GROQ_AVAILABLE:
    try:
        from groq import Groq
    except ImportError:
        GROQ_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

# Check MLX Whisper availability
try:
    import mlx_whisper
    import mlx.core as mx
    MLX_WHISPER_AVAILABLE = True
    MLX_DEVICE = mx.default_device()
except ImportError:
    MLX_WHISPER_AVAILABLE = False
    MLX_DEVICE = "Not Available"

# YouTube transcript support
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

# Local Whisper for YouTube
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# Check transcription functionality availability
TRANSCRIPTION_AVAILABLE = MLX_WHISPER_AVAILABLE or GROQ_AVAILABLE

# Import YouTube components
from .youtube_en import YouTubeSearcher, TranscriptExtractor, SummaryGenerator

class ApplePodcastExplorer:
    """Tool for exploring Apple podcast channels"""
    
    def __init__(self):
        """Initialize HTTP session"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        # Create root output folder
        self.root_output_dir = Path("outputs")
        self.root_output_dir.mkdir(exist_ok=True)
        
        # Initialize MLX Whisper model - always use medium model
        self.whisper_model_name = 'mlx-community/whisper-medium'
        
        # Groq client initialization
        if GROQ_AVAILABLE:
            self.groq_client = Groq(api_key=GROQ_API_KEY)
        else:
            self.groq_client = None
            
        # Gemini client initialization
        self.api_key = os.getenv('GEMINI_API_KEY')
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.gemini_client = genai
            except Exception as e:
                print(f"⚠️  Gemini client initialization failed: {e}")
                self.gemini_client = None
        else:
            self.gemini_client = None
    
    def load_whisper_model(self):
        """
        Set MLX Whisper model - always use medium model
        """
        if not MLX_WHISPER_AVAILABLE:
            print("❌ MLX Whisper not available")
            return False
        
        try:
            print(f"📥 Setting MLX Whisper model: {self.whisper_model_name}")
            print("ℹ️  The model file will be downloaded on first use, please wait patiently...")
            return True
        except Exception as e:
            print(f"❌ Failed to set MLX Whisper model: {e}")
            return False
    
    def search_podcast_channel(self, podcast_name: str, quiet: bool = False) -> List[Dict]:
        """
        Search for podcast channels
        
        Args:
            podcast_name: Podcast channel name
            quiet: Whether to process silently
        
        Returns:
            List[Dict]: List of podcast channel information
        """
        try:
            if not quiet:
                print(f"Searching for podcast channel: {podcast_name}")
            
            search_url = "https://itunes.apple.com/search"
            params = {
                'term': podcast_name,
                'media': 'podcast',
                'entity': 'podcast',
                'limit': 10  # Get multiple matching podcast channels
            }
            
            response = self.session.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            channels = []
            for result in data.get('results', []):
                channel = {
                    'name': result.get('collectionName', 'Unknown Channel'),
                    'artist': result.get('artistName', 'Unknown Author'),
                    'feed_url': result.get('feedUrl', ''),
                    'genre': ', '.join(result.get('genres', [])),
                    'description': result.get('description', 'No description')
                }
                channels.append(channel)
            
            return channels
            
        except Exception as e:
            if not quiet:
                print(f"Error searching channel: {e}")
            return []
    
    def get_recent_episodes(self, feed_url: str, limit: int = 10, quiet: bool = False) -> List[Dict]:
        """
        Get recent episodes of a podcast channel
        
        Args:
            feed_url: RSS subscription URL
            limit: Limit on the number of episodes returned
            quiet: Whether to process silently
        
        Returns:
            List[Dict]: List of episode information
        """
        try:
            if not quiet:
                print("Getting podcast episodes...")
            
            feed = feedparser.parse(feed_url)
            episodes = []
            
            for entry in feed.entries[:limit]:
                # Extract audio URL
                audio_url = None
                for link in entry.get('links', []):
                    if link.get('type', '').startswith('audio/'):
                        audio_url = link.get('href')
                        break
                
                # Alternative method to get audio URL
                if not audio_url and hasattr(entry, 'enclosures'):
                    for enclosure in entry.enclosures:
                        if enclosure.type.startswith('audio/'):
                            audio_url = enclosure.href
                            break
                
                # Format publish date
                published_date = 'Unknown Date'
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_date = datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d')
                elif hasattr(entry, 'published'):
                    published_date = entry.published
                
                # Get duration (if available)
                duration = 'Unknown Duration'
                if hasattr(entry, 'itunes_duration'):
                    duration = entry.itunes_duration
                
                episode = {
                    'title': entry.get('title', 'Unknown Title'),
                    'audio_url': audio_url,
                    'published_date': published_date,
                    'duration': duration,
                    'description': entry.get('summary', 'No description')[:200] + '...' if len(entry.get('summary', '')) > 200 else entry.get('summary', 'No description')
                }
                episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            if not quiet:
                print(f"Error getting episodes: {e}")
            return []
    
    def display_channels(self, channels: List[Dict]) -> int:
        """
        Display found channels and let the user choose
        
        Args:
            channels: List of channels
        
        Returns:
            int: Index of the channel selected by the user, -1 for invalid selection
        """
        if not channels:
            print("❌ No matching podcast channels found")
            return -1
        
        print(f"\nFound {len(channels)} matching podcast channels:")
        print("=" * 60)
        
        for i, channel in enumerate(channels, 1):
            print(f"{i}. {channel['name']}")
            print(f"   Author: {channel['artist']}")
            print(f"   Genre: {channel['genre']}")
            print(f"   Description: {channel['description'][:100]}{'...' if len(channel['description']) > 100 else ''}")
            print("-" * 60)
        
        try:
            choice = input(f"\nPlease select a channel (1-{len(channels)}), or press Enter to exit: ").strip()
            if not choice:
                return -1
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(channels):
                return choice_num - 1
            else:
                print("❌ Invalid selection")
                return -1
                
        except ValueError:
            print("❌ Please enter a valid number")
            return -1
    
    def display_episodes(self, episodes: List[Dict], channel_name: str):
        """
        Display episode list
        
        Args:
            episodes: List of episodes
            channel_name: Channel name
        """
        if not episodes:
            print("❌ No episodes found for this channel")
            return
        
        print(f"\n📻 {channel_name} - Most recent {len(episodes)} podcast episodes:")
        print("=" * 80)
        
        for i, episode in enumerate(episodes, 1):
            print(f"{i:2d}. {episode['title']}")
            print(f"    📅 Publish Date: {episode['published_date']}")
            print(f"    ⏱️  Duration: {episode['duration']}")
            print(f"    📝 Description: {episode['description']}")
            if episode['audio_url']:
                print(f"    🎵 Audio URL: {episode['audio_url']}")
            print("-" * 80)
    
    def parse_episode_selection(self, user_input: str, max_episodes: int) -> List[int]:
        """
        Parse user's episode selection input
        
        Args:
            user_input: User input (e.g., "1-10", "3", "1,3,5")
            max_episodes: Maximum number of episodes
        
        Returns:
            List[int]: List of selected episode indices (0-based)
        """
        selected = set()
        user_input = user_input.strip()
        
        # Split by comma
        parts = [part.strip() for part in user_input.split(',')]
        
        for part in parts:
            if '-' in part:
                # Handle range, e.g. "1-10"
                try:
                    start, end = part.split('-', 1)
                    start_num = int(start.strip())
                    end_num = int(end.strip())
                    
                    # Ensure range is valid
                    start_num = max(1, min(start_num, max_episodes))
                    end_num = max(1, min(end_num, max_episodes))
                    
                    if start_num > end_num:
                        start_num, end_num = end_num, start_num
                    
                    # Add all numbers in range (convert to 0-based index)
                    for i in range(start_num, end_num + 1):
                        selected.add(i - 1)
                        
                except ValueError:
                    print(f"❌ Invalid range format: {part}")
                    continue
            else:
                # Handle single number
                try:
                    num = int(part)
                    if 1 <= num <= max_episodes:
                        selected.add(num - 1)  # Convert to 0-based index
                    else:
                        print(f"❌ Number out of range: {num} (valid range: 1-{max_episodes})")
                except ValueError:
                    print(f"❌ Invalid number: {part}")
                    continue
        
        return sorted(list(selected))
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Clean filename, remove unsafe characters
        
        Args:
            filename: Original filename
        
        Returns:
            str: Cleaned filename
        """
        # Remove or replace unsafe characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)  # Replace spaces with underscores
        filename = filename.strip('._')  # Remove leading/trailing dots and underscores
        
        # Limit filename length
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename
    
    def ensure_filename_length(self, safe_channel: str, episode_num: int, safe_title: str, extension: str = ".mp3") -> str:
        """
        Ensure the complete filename doesn't exceed filesystem limits (255 characters)
        
        Args:
            safe_channel: Sanitized channel name
            episode_num: Episode number
            safe_title: Sanitized episode title
            extension: File extension (default: .mp3)
        
        Returns:
            str: Final filename that fits within length limits
        """
        # Calculate the fixed parts: episode number, underscores, and extension
        fixed_part = f"_{episode_num:02d}_"  # e.g. "_01_"
        fixed_length = len(fixed_part) + len(extension)  # e.g. 4 + 4 = 8
        
        # Maximum available length for channel and title
        max_content_length = 255 - fixed_length  # e.g. 255 - 8 = 247
        
        # If both channel and title fit, use them as is
        combined_length = len(safe_channel) + len(safe_title)
        if combined_length <= max_content_length:
            return f"{safe_channel}{fixed_part}{safe_title}{extension}"
        
        # If too long, distribute the available space
        # Give priority to the title, but ensure both have minimum representation
        min_channel_length = 20  # Minimum characters for channel name
        min_title_length = 30    # Minimum characters for title
        
        # If even minimums don't fit, truncate more aggressively
        if min_channel_length + min_title_length > max_content_length:
            # Split available space equally
            half_space = max_content_length // 2
            truncated_channel = safe_channel[:half_space]
            truncated_title = safe_title[:max_content_length - len(truncated_channel)]
        else:
            # Try to preserve more of the title
            remaining_space = max_content_length - min_channel_length
            if len(safe_title) <= remaining_space:
                # Title fits, truncate channel
                truncated_title = safe_title
                truncated_channel = safe_channel[:max_content_length - len(safe_title)]
            else:
                # Both need truncation
                truncated_channel = safe_channel[:min_channel_length]
                truncated_title = safe_title[:max_content_length - min_channel_length]
        
        final_filename = f"{truncated_channel}{fixed_part}{truncated_title}{extension}"
        
        # Safety check
        if len(final_filename) > 255:
            # Emergency truncation
            emergency_title = safe_title[:255 - fixed_length - min_channel_length]
            emergency_channel = safe_channel[:min_channel_length]
            final_filename = f"{emergency_channel}{fixed_part}{emergency_title}{extension}"
        
        return final_filename
    
    def ensure_output_filename_length(self, prefix: str, safe_channel: str, safe_title: str, extension: str = ".md") -> str:
        """
        Ensure output filenames (transcript/summary) don't exceed filesystem limits (255 characters)
        
        Args:
            prefix: File prefix (e.g., "Transcript_", "Summary_")
            safe_channel: Sanitized channel name (can be empty for YouTube)
            safe_title: Sanitized title
            extension: File extension (default: .md)
        
        Returns:
            str: Final filename that fits within length limits
        """
        # Calculate fixed parts length: prefix + extension
        fixed_length = len(prefix) + len(extension)
        
        # Maximum available length for content
        max_content_length = 255 - fixed_length
        
        # If no channel (YouTube format)
        if not safe_channel:
            if len(safe_title) <= max_content_length:
                return f"{prefix}{safe_title}{extension}"
            else:
                truncated_title = safe_title[:max_content_length]
                return f"{prefix}{truncated_title}{extension}"
        
        # Apple Podcast format: prefix + channel + "_" + title + extension
        separator = "_"
        combined_content = f"{safe_channel}{separator}{safe_title}"
        
        if len(combined_content) <= max_content_length:
            return f"{prefix}{combined_content}{extension}"
        
        # Need truncation: prioritize title but ensure channel has minimum representation
        min_channel_length = 15
        min_title_length = 20
        
        if min_channel_length + len(separator) + min_title_length > max_content_length:
            # Extreme case: split available space
            available_space = max_content_length - len(separator)
            half_space = available_space // 2
            truncated_channel = safe_channel[:half_space]
            truncated_title = safe_title[:available_space - len(truncated_channel)]
        else:
            # Normal case: prioritize title
            remaining_space = max_content_length - min_channel_length - len(separator)
            if len(safe_title) <= remaining_space:
                truncated_title = safe_title
                truncated_channel = safe_channel[:max_content_length - len(separator) - len(safe_title)]
            else:
                truncated_channel = safe_channel[:min_channel_length]
                truncated_title = safe_title[:max_content_length - len(separator) - min_channel_length]
        
        return f"{prefix}{truncated_channel}{separator}{truncated_title}{extension}"
    
    def ensure_transcript_filename_length(self, safe_channel: str, safe_title: str) -> str:
        """Ensure transcript filename length"""
        return self.ensure_output_filename_length("Transcript_", safe_channel, safe_title)
    
    def ensure_summary_filename_length(self, safe_channel: str, safe_title: str) -> str:
        """Ensure summary filename length"""
        return self.ensure_output_filename_length("Summary_", safe_channel, safe_title)
    
    def ensure_visual_filename_length(self, safe_channel: str, safe_title: str) -> str:
        """Ensure visual filename length"""
        return self.ensure_output_filename_length("Visual_", safe_channel, safe_title, ".html")
    
    def create_episode_folder(self, channel_name: str, episode_title: str, episode_num: int, published_date: str = None) -> Path:
        """
        Create episode folder
        
        Args:
            channel_name: Channel name
            episode_title: Episode title
            episode_num: Episode number
            published_date: Episode publish date (format: YYYY-MM-DD)
        
        Returns:
            Path: Episode folder path
        """
        # Clean channel name and episode title
        safe_channel = self.sanitize_filename(channel_name)
        safe_title = self.sanitize_filename(episode_title)
        
        # Limit folder name length to ensure path doesn't get too long
        max_channel_length = 50
        max_title_length = 100
        
        if len(safe_channel) > max_channel_length:
            safe_channel = safe_channel[:max_channel_length]
        
        if len(safe_title) > max_title_length:
            safe_title = safe_title[:max_title_length]
        
        # Create channel folder (first level)
        channel_dir = self.root_output_dir / safe_channel
        channel_dir.mkdir(parents=True, exist_ok=True)
        
        # Use published date for date folder (second level)
        if published_date and published_date != 'Unknown Date':
            # Apple Podcast already formats to YYYY-MM-DD, use directly
            date_folder = published_date
        else:
            # Use today's date if no published date
            date_folder = datetime.now().strftime('%Y-%m-%d')
        
        date_dir = channel_dir / date_folder
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Create episode folder (third level) - without episode number prefix
        episode_dir = date_dir / safe_title
        episode_dir.mkdir(parents=True, exist_ok=True)
        
        return episode_dir

    def download_episode(self, episode: Dict, episode_num: int, channel_name: str, quiet: bool = False) -> tuple[bool, Path]:
        """
        Download a single episode
        
        Args:
            episode: Episode information
            episode_num: Episode number (1-based)
            channel_name: Channel name
            quiet: Whether to process silently
        
        Returns:
            tuple[bool, Path]: (Whether download was successful, Episode folder path)
        """
        if not episode['audio_url']:
            if not quiet:
                print(f"❌ No available audio URL for episode {episode_num}")
            return False, None
        
        try:
            # Create episode folder
            episode_dir = self.create_episode_folder(channel_name, episode['title'], episode_num, episode.get('published_date'))
            
            # Audio filename
            filename = "audio.mp3"
            filepath = episode_dir / filename
            
            # Check if file already exists
            if filepath.exists():
                if not quiet:
                    print(f"⚠️  File already exists, skipping: {episode_dir.name}/{filename}")
                return True, episode_dir
            
            if not quiet:
                print(f"📥 Downloading: {episode['title']}")
            
            # Download file
            response = self.session.get(episode['audio_url'], stream=True)
            response.raise_for_status()
            
            # Get file size
            total_size = int(response.headers.get('content-length', 0))
            
            # Download with progress bar
            with open(filepath, 'wb') as f:
                if total_size > 0 and not quiet:
                    with tqdm(
                        total=total_size, 
                        unit='B', 
                        unit_scale=True, 
                        desc=f"Episode {episode_num}"
                    ) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
                else:
                    # If no file size info, just download, or in silent mode directly download
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            if not quiet:
                print(f"✅ Download complete")
            return True, episode_dir
            
        except Exception as e:
            if not quiet:
                print(f"❌ Failed to download episode {episode_num}: {e}")
            # If download failed, delete possible incomplete file
            if 'filepath' in locals() and filepath.exists():
                filepath.unlink()
            return False, None
    
    def get_file_size_mb(self, filepath):
        """Get file size (MB)"""
        if not os.path.exists(filepath):
            return 0
        size_bytes = os.path.getsize(filepath)
        return size_bytes / (1024 * 1024)
    
    def compress_audio_file(self, input_file: Path, output_file: Path, quiet: bool = False) -> bool:
        """
        Smart two-level audio compression below Groq API limit
        Prefer 64k for quality, fallback to 48k if still >25MB
        
        Args:
            input_file: Input file path
            output_file: Output file path
        
        Returns:
            bool: Whether compression was successful
        """
        try:
            if quiet:
                print("🔧 Compressing...")
            else:
                print(f"🔧 Compressing audio file: {input_file.name}")
                
                # Level 1 compression: 64k (priority on quality)
                print("📊 Level 1 compression: 16KHz mono, 64kbps MP3")
            
            # Generate safe temporary filename, not exceeding 255 characters
            original_name = output_file.stem  # Filename without extension
            prefix = "temp_64k_"
            extension = output_file.suffix
            
            # Calculate maximum length for original filename part
            max_name_length = 255 - len(prefix) - len(extension)
            
            # Truncate original filename if needed
            if len(original_name) > max_name_length:
                safe_name = original_name[:max_name_length]
            else:
                safe_name = original_name
            
            temp_64k_file = output_file.parent / f"{prefix}{safe_name}{extension}"
            
            cmd_64k = [
                'ffmpeg',
                '-i', str(input_file),
                '-ar', '16000',        # Downsample to 16KHz
                '-ac', '1',            # Mono
                '-b:a', '64k',         # 64kbps bitrate
                '-y',                  # Overwrite output file
                str(temp_64k_file)
            ]
            
            # Run level 1 compression
            result = subprocess.run(
                cmd_64k,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Check file size after 64k compression
            compressed_size_mb = self.get_file_size_mb(temp_64k_file)
            if not quiet:
                print(f"📊 Size after 64k compression: {compressed_size_mb:.1f}MB")
            
            if compressed_size_mb <= 25:
                # 64k compression meets requirements, use 64k result
                temp_64k_file.rename(output_file)
                if not quiet:
                    print(f"✅ 64k compression complete: {output_file.name} ({compressed_size_mb:.1f}MB)")
                return True
            else:
                # Still >25MB after 64k compression, proceed with level 2 48k compression
                if not quiet:
                    print(f"⚠️  Still exceeds 25MB after 64k, proceeding with level 2 48k compression...")
                    print("📊 Level 2 compression: 16KHz mono, 48kbps MP3")
                
                cmd_48k = [
                    'ffmpeg',
                    '-i', str(input_file),
                    '-ar', '16000',        # Downsample to 16KHz
                    '-ac', '1',            # Mono
                    '-b:a', '48k',         # 48kbps bitrate
                    '-y',                  # Overwrite output file
                    str(output_file)
                ]
                
                # Run level 2 compression
                result = subprocess.run(
                    cmd_48k,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                final_size_mb = self.get_file_size_mb(output_file)
                if not quiet:
                    print(f"✅ 48k compression complete: {output_file.name} ({final_size_mb:.1f}MB)")
                
                # Clean up temporary files
                if temp_64k_file.exists():
                    temp_64k_file.unlink()
                
                return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Compression failed: {e}")
            # Clean up temporary files
            if 'temp_64k_file' in locals() and temp_64k_file.exists():
                temp_64k_file.unlink()
            return False
        except Exception as e:
            print(f"❌ Compression error: {e}")
            # Clean up temporary files
            if 'temp_64k_file' in locals() and temp_64k_file.exists():
                temp_64k_file.unlink()
            return False
    
    def transcribe_with_groq(self, audio_file: Path, quiet: bool = False) -> dict:
        """
        Transcribe audio file using Groq API
        
        Args:
            audio_file: Audio file path
        
        Returns:
            dict: Transcription result
        """
        try:
            if not quiet:
                print(f"🚀 Groq API transcription: {audio_file.name}")
                print("🧠 Using model: whisper-large-v3")
            
            start_time = time.time()
            
            # Open audio file and transcribe
            with open(audio_file, "rb") as file:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=file,
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    temperature=0.0
                )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Process response
            text = transcription.text if hasattr(transcription, 'text') else transcription.get('text', '')
            language = getattr(transcription, 'language', 'en') if hasattr(transcription, 'language') else transcription.get('language', 'en')
            
            file_size_mb = self.get_file_size_mb(audio_file)
            speed_ratio = file_size_mb / processing_time * 60 if processing_time > 0 else 0
            
            if not quiet:
                print(f"✅ Groq transcription complete! Time: {processing_time:.1f}s")
            
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
    
    def transcribe_with_mlx(self, audio_file: Path, quiet: bool = False) -> dict:
        """
        Transcribe audio file using MLX Whisper
        
        Args:
            audio_file: Audio file path
        
        Returns:
            dict: Transcription result
        """
        try:
            if not quiet:
                print(f"🎯 MLX Whisper transcription: {audio_file.name}")
                print("🧠 Using model: mlx-community/whisper-medium")
            
            start_time = time.time()
            
            # Hide MLX Whisper output in quiet mode
            if quiet:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    result = mlx_whisper.transcribe(
                        str(audio_file),
                        path_or_hf_repo=self.whisper_model_name
                    )
            else:
                result = mlx_whisper.transcribe(
                    str(audio_file),
                    path_or_hf_repo=self.whisper_model_name
                )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            file_size_mb = self.get_file_size_mb(audio_file)
            speed_ratio = file_size_mb / processing_time * 60 if processing_time > 0 else 0
            
            if not quiet:
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
    
    def transcribe_audio_smart(self, audio_file: Path, episode_title: str, channel_name: str, episode_dir: Path, auto_transcribe: bool = False) -> bool:
        """
        Smart audio transcription: choose the best transcription method based on file size
        
        Args:
            audio_file: Audio file path
            episode_title: Episode title
            channel_name: Channel name
            episode_dir: Episode folder path
            auto_transcribe: Whether to auto transcribe without user prompts
        
        Returns:
            bool: Whether transcription was successful
        """
        if not TRANSCRIPTION_AVAILABLE:
            print("❌ No transcription service available")
            return False
        
        try:
            # Transcript file path
            # Generate transcript filename including episode title
            safe_channel = self.sanitize_filename(channel_name)
            safe_title = self.sanitize_filename(episode_title)
            transcript_filename = self.ensure_transcript_filename_length(safe_channel, safe_title)
            transcript_filepath = episode_dir / transcript_filename
            
            # Check if transcript file already exists
            if transcript_filepath.exists():
                print(f"⚠️  Transcript file already exists, skipping: {episode_dir.name}/{transcript_filename}")
                return True
            
            if not auto_transcribe:
                print(f"🎙️  Starting transcription: {episode_title}")
                
                # Check file size
                file_size_mb = self.get_file_size_mb(audio_file)
                print(f"📊 Audio file size: {file_size_mb:.1f}MB")
            else:
                file_size_mb = self.get_file_size_mb(audio_file)
            
            groq_limit = 25  # MB
            transcript_result = None
            compressed_file = None
            original_size = file_size_mb
            final_size = file_size_mb
            
            # Smart transcription strategy
            if file_size_mb <= groq_limit and GROQ_AVAILABLE:
                # Situation 1: File <25MB, directly use Groq, MLX as backup
                if not auto_transcribe:
                    print("✅ File size within Groq limit, using ultra-fast transcription")
                transcript_result = self.transcribe_with_groq(audio_file, quiet=auto_transcribe)
                
                # MLX backup
                if not transcript_result and MLX_WHISPER_AVAILABLE:
                    if not auto_transcribe:
                        print("🔄 Groq failed, switching to local MLX Whisper...")
                    transcript_result = self.transcribe_with_mlx(audio_file, quiet=auto_transcribe)
            
            elif file_size_mb > groq_limit:
                # Situation 2: File >25MB, needs compression
                if not auto_transcribe:
                    print("⚠️  File exceeds Groq limit, starting compression...")
                
                # Generate safe compressed filename
                original_name = audio_file.stem
                compressed_name = f"compressed_{original_name}"
                extension = audio_file.suffix
                
                # Ensure compressed filename doesn't exceed limit
                max_compressed_length = 255 - len(extension)
                if len(compressed_name) > max_compressed_length:
                    # Truncate to fit
                    truncated_name = compressed_name[:max_compressed_length]
                    compressed_file = audio_file.parent / f"{truncated_name}{extension}"
                else:
                    compressed_file = audio_file.parent / f"{compressed_name}{extension}"
                
                if self.compress_audio_file(audio_file, compressed_file, quiet=auto_transcribe):
                    compressed_size = self.get_file_size_mb(compressed_file)
                    final_size = compressed_size
                    if not auto_transcribe:
                        print(f"📊 Compressed size: {compressed_size:.1f}MB")
                    
                    if compressed_size <= groq_limit and GROQ_AVAILABLE:
                        # Situation 2a: After compression within Groq limit, MLX as backup
                        if not auto_transcribe:
                            print("✅ Compressed size within Groq limit, using ultra-fast transcription")
                        transcript_result = self.transcribe_with_groq(compressed_file, quiet=auto_transcribe)
                        
                        # Groq failed use MLX backup
                        if not transcript_result and MLX_WHISPER_AVAILABLE:
                            if not auto_transcribe:
                                print("🔄 Groq failed, switching to local MLX Whisper...")
                            transcript_result = self.transcribe_with_mlx(compressed_file, quiet=auto_transcribe)
                    else:
                        # Situation 2b: Still exceeds limit after compression, use MLX
                        if not auto_transcribe:
                            print("⚠️  Still exceeds limit after compression, using MLX local transcription")
                        if MLX_WHISPER_AVAILABLE:
                            if auto_transcribe:
                                print("💻 Local transcription...")
                            transcript_result = self.transcribe_with_mlx(compressed_file, quiet=auto_transcribe)
                        else:
                            if not auto_transcribe:
                                print("❌ MLX Whisper unavailable, cannot transcribe large file")
                            return False
                else:
                    # Compression failed, try MLX
                    if not auto_transcribe:
                        print("❌ Compression failed, trying local MLX transcription")
                    if MLX_WHISPER_AVAILABLE:
                        transcript_result = self.transcribe_with_mlx(audio_file, quiet=auto_transcribe)
                    else:
                        if not auto_transcribe:
                            print("❌ MLX Whisper unavailable, transcription failed")
                        return False
            
            else:
                # Situation 3: Groq unavailable, use MLX
                if not auto_transcribe:
                    print("⚠️  Groq API unavailable, using local MLX transcription")
                if MLX_WHISPER_AVAILABLE:
                    transcript_result = self.transcribe_with_mlx(audio_file, quiet=auto_transcribe)
                else:
                    if not auto_transcribe:
                        print("❌ MLX Whisper unavailable, transcription failed")
                    return False
            
            # Process transcription result
            if not transcript_result:
                if not auto_transcribe:
                    print("❌ All transcription methods failed")
                return False
            
            # Save transcription result
            with open(transcript_filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {episode_title}\n\n")
                f.write(f"**Channel:** {channel_name}\n\n")
                f.write("---\n\n")
                f.write(transcript_result['text'])
            
            if not auto_transcribe:
                print(f"✅ Transcription complete: {episode_dir.name}/{transcript_filename}")
            
            # Clean up files
            try:
                # Delete original audio file
                audio_file.unlink()
                if not auto_transcribe:
                    print(f"🗑️  Deleted audio file: {audio_file.name}")
                
                # Delete compressed file (if any)
                if compressed_file and compressed_file.exists():
                    compressed_file.unlink()
                    if not auto_transcribe:
                        print(f"🗑️  Deleted compressed file: {compressed_file.name}")
                    
            except Exception as e:
                if not auto_transcribe:
                    print(f"⚠️  Failed to delete files: {e}")
            
            return True
            
        except Exception as e:
            if not auto_transcribe:
                print(f"❌ Transcription process failed: {e}")
            # Clean up possible incomplete files
            if transcript_filepath.exists():
                transcript_filepath.unlink()
            return False
    
    def download_episodes(self, episodes: List[Dict], channel_name: str):
        """
        Batch download episodes
        
        Args:
            episodes: List of episodes
            channel_name: Channel name
        """
        if not episodes:
            print("❌ No episodes to download")
            return
        
        print(f"\n💾 Download options:")
        print("Format instructions:")
        print("  - Download single episode: enter a number, e.g. '3'")
        print("  - Download multiple episodes: separate with commas, e.g. '1,3,5'")
        print("  - Download range: use hyphen, e.g. '1-10'")
        print("  - Combine: e.g. '1,3-5,8'")
        
        user_input = input(f"\nPlease select episodes to download (1-{len(episodes)}) or press Enter to skip: ").strip()
        
        if not user_input:
            print("Skipping download")
            return
        
        # Parse user selection
        selected_indices = self.parse_episode_selection(user_input, len(episodes))
        
        if not selected_indices:
            print("❌ No valid episodes selected")
            return
        
        # Download results
        success_count = 0
        total_count = len(selected_indices)
        downloaded_files = []  # (audio_file_path, episode_title, episode_dir)
        
        # Download selected episodes
        for i, episode_index in enumerate(selected_indices, 1):
            episode = episodes[episode_index]
            episode_num = episode_index + 1  # Convert back to 1-based numbering
            
            success, episode_dir = self.download_episode(episode, episode_num, channel_name)
            if success and episode_dir:
                success_count += 1
                # Build downloaded file path
                audio_file = episode_dir / "audio.mp3"
                downloaded_files.append((audio_file, episode['title'], episode_dir))
        
        # Ask whether to transcribe
        if success_count > 0 and TRANSCRIPTION_AVAILABLE:
            self.transcribe_downloaded_files(downloaded_files, channel_name, auto_transcribe=True)
    
    def transcribe_downloaded_files(self, downloaded_files: List[tuple], channel_name: str, auto_transcribe: bool = False):
        """
        Transcribe downloaded files
        
        Args:
            downloaded_files: [(file_path, title, episode_folder), ...]
            channel_name: Channel name
            auto_transcribe: Whether to auto transcribe without asking user
        """
        if not auto_transcribe:
            print(f"\n🎙️  Transcription options:")
            transcribe_choice = input("Transcribe the downloaded audio files? (y/n): ").strip().lower()
            if transcribe_choice not in ['y', 'yes']:
                print("Skipping transcription")
                return
        
        # Transcribe files
        success_count = 0
        total_count = len(downloaded_files)
        
        if auto_transcribe:
            print("\n⚡️ Ultra-fast transcription...")
        else:
            print(f"\n🚀 Starting smart transcription of {total_count} files...")
            if GROQ_AVAILABLE:
                print("💡 Will automatically choose the best transcription method: Groq API (ultra-fast) or MLX Whisper (local)")
            else:
                print("💡 Using MLX Whisper local transcription")
        
        successful_transcripts = []  # Store successful transcription info (episode_title, channel_name, episode_dir)
        
        for i, (audio_file, episode_title, episode_dir) in enumerate(downloaded_files, 1):
            if not audio_file.exists():
                if not auto_transcribe:
                    print(f"❌ File does not exist: {audio_file}")
                continue
            
            if not auto_transcribe:
                print(f"\n[{i}/{total_count}] ", end="")
            if self.transcribe_audio_smart(audio_file, episode_title, channel_name, episode_dir, auto_transcribe):
                success_count += 1
                successful_transcripts.append((episode_title, channel_name, episode_dir))
        
        if auto_transcribe:
            print("✅ Transcription complete")
        else:
            print(f"\n📊 Transcription complete! Success: {success_count}/{total_count}")
            if success_count > 0:
                print(f"📁 Transcript files saved in episode folders: {self.root_output_dir.absolute()}")
        
        # Auto generate summaries (no longer ask user)
        if success_count > 0 and self.gemini_client and successful_transcripts:
            # Default to English summaries
            language_choice = 'en'
            
            print("\n🧠 Summarizing...")
            
            summary_success_count = 0
            
            for i, (episode_title, channel_name, episode_dir) in enumerate(successful_transcripts, 1):
                if not auto_transcribe:
                    print(f"\n[{i}/{len(successful_transcripts)}] Processing: {episode_title}")
                
                # Read transcript file
                safe_channel = self.sanitize_filename(channel_name)
                safe_title = self.sanitize_filename(episode_title)
                transcript_filename = self.ensure_transcript_filename_length(safe_channel, safe_title)
                transcript_filepath = episode_dir / transcript_filename
                
                if not transcript_filepath.exists():
                    if not auto_transcribe:
                        print(f"❌ Transcript file does not exist: {episode_dir.name}/{transcript_filename}")
                    continue
                
                try:
                    # Read transcript content
                    with open(transcript_filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract actual transcript text (skip metadata)
                    if "## Transcript Content" in content:
                        transcript_text = content.split("## Transcript Content")[1].strip()
                    elif "## 转录内容" in content:
                        transcript_text = content.split("## 转录内容")[1].strip()
                    elif "---" in content:
                        # Fallback: content after ---
                        parts = content.split("---", 1)
                        if len(parts) > 1:
                            transcript_text = parts[1].strip()
                        else:
                            transcript_text = content
                    else:
                        transcript_text = content
                    
                    if len(transcript_text.strip()) < 100:
                        if not auto_transcribe:
                            print("⚠️  Transcript content too short, skipping summary generation")
                        continue
                    
                    # Generate summary
                    summary = self.generate_summary(transcript_text, episode_title)
                    if not summary:
                        if not auto_transcribe:
                            print("❌ Summary generation failed")
                        continue
                    
                    # Use English summary (no translation needed)
                    final_summary = summary
                    
                    # Save summary
                    summary_path = self.save_summary(final_summary, episode_title, channel_name, language_choice, episode_dir)
                    if summary_path:
                        if not auto_transcribe:
                            print(f"✅ Summary saved: {episode_dir.name}/summary.md")
                        summary_success_count += 1
                    else:
                        if not auto_transcribe:
                            print("❌ Summary save failed")
                        
                except Exception as e:
                    if not auto_transcribe:
                        print(f"❌ Summary processing error: {e}")
                    continue
            
            print("✅ Summaries completed")
            
            # Provide visualization option for both auto and manual modes
            if summary_success_count > 0:
                self.ask_for_visualization(successful_transcripts, language_choice)
        
        elif not self.gemini_client and successful_transcripts and not auto_transcribe:
            print(f"\n⚠️  Gemini API not available, cannot generate summary")
            print(f"💡 To enable summary, set GEMINI_API_KEY in your .env file")
            
            # Ask about visualization for transcript only
            self.ask_for_visualization(successful_transcripts, 'en')
    
    def ask_for_visualization(self, successful_transcripts: List[tuple], language: str):
        """
        Ask user if they want to generate visual stories
        
        Args:
            successful_transcripts: List of (episode_title, channel_name, episode_dir) tuples
            language: Language preference ('en' for English)
        """
        if not successful_transcripts:
            return
        
        visualize_choice = input("\n🎨 Visual Story Generation?(y/n): ").strip().lower()
        
        if visualize_choice not in ['y', 'yes']:
            return
        
        # Ask whether to use transcript or summary
        print("📄 Content source:")
        content_choice = input("Visualize based on transcript or summary? (t/s): ").strip().lower()
        
        if content_choice not in ['t', 's']:
            print("Invalid choice. Skipping visualization.")
            return
        
        # Import visual module
        try:
            from .visual_en import generate_visual_story
        except ImportError:
            print("❌ Visual module not found. Please ensure visual_en.py is in the podlens folder.")
            return
        
        # Process each successful transcript/summary
        visual_success_count = 0
        
        print("\n🎨 Adding colors...")
        
        for i, (episode_title, channel_name, episode_dir) in enumerate(successful_transcripts, 1):
            # Build file paths
            safe_channel = self.sanitize_filename(channel_name)
            safe_title = self.sanitize_filename(episode_title)
            
            if content_choice == 't':
                # Use transcript
                source_filename = self.ensure_transcript_filename_length(safe_channel, safe_title)
                content_type = "transcript"
            else:
                # Use summary
                source_filename = self.ensure_summary_filename_length(safe_channel, safe_title)
                content_type = "summary"
            
            source_filepath = episode_dir / source_filename
            
            if not source_filepath.exists():
                continue
            
            # Set output path for visual story
            visual_filename = self.ensure_visual_filename_length(safe_channel, safe_title)
            visual_output_path = episode_dir / visual_filename
            
            # Generate visual story
            if generate_visual_story(str(source_filepath), str(visual_output_path)):
                visual_success_count += 1
        
        print("✅ Visualization complete")

    def generate_summary(self, transcript: str, title: str) -> str:
        """
        Generate summary using Gemini API
        
        Args:
            transcript: Transcript text
            title: Episode title
        
        Returns:
            str: Generated summary, None if failed
        """
        if not self.gemini_client:
            print("❌ Gemini API not available, cannot generate summary")
            return None
        
        try:
            # print("✨ Generating summary...")  # 隐藏详细信息
            
            prompt = f"""
            Please provide a comprehensive summary and analysis of this podcast episode transcript.
            
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
                print("❌ Gemini API response format abnormal")
                return None
                
        except Exception as e:
            print(f"❌ Summary generation failed: {e}")
            return None
    
    def translate_to_chinese(self, text: str) -> str:
        """
        Translate text to Chinese
        
        Args:
            text: Text to translate
        
        Returns:
            str: Translated Chinese text, None if failed
        """
        if not self.gemini_client:
            print("❌ Gemini API not available, cannot translate")
            return None
        
        try:
            print("🔄 Translating to Chinese...")
            
            prompt = f"Translate everything to Chinese accurately without missing anything:\n\n{text}"
            
            response = self.gemini_client.GenerativeModel("gemini-2.5-flash-preview-05-20").generate_content(prompt)
            
            # Handle the response properly
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                print("❌ Gemini API response format abnormal")
                return None
                
        except Exception as e:
            print(f"❌ Translation failed: {e}")
            return None

    def save_summary(self, summary: str, episode_title: str, channel_name: str, language: str, episode_dir: Path = None) -> Optional[str]:
        """
        Save summary to file
        
        Args:
            summary: Generated summary
            episode_title: Episode title
            channel_name: Channel name
            language: Language preference
            episode_dir: Episode folder path
        
        Returns:
            Optional[str]: Path to saved summary file, None if failed
        """
        try:
            # Build summary filename
            if episode_dir:
                # Generate summary filename with episode title
                safe_channel = self.sanitize_filename(channel_name)
                safe_title = self.sanitize_filename(episode_title)
                summary_filename = self.ensure_summary_filename_length(safe_channel, safe_title)
                summary_filepath = episode_dir / summary_filename
            else:
                # Legacy compatibility
                safe_channel = self.sanitize_filename(channel_name)
                safe_title = self.sanitize_filename(episode_title)
                summary_filename = self.ensure_summary_filename_length(safe_channel, safe_title)
                summary_filepath = self.root_output_dir / summary_filename
            
            with open(summary_filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Summary: {episode_title}\n\n" if language == "en" else f"# 摘要: {episode_title}\n\n")
                f.write(f"**Channel:** {channel_name}\n\n" if language == "en" else f"**频道:** {channel_name}\n\n")
                f.write(f"**Summary Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" if language == "en" else f"**摘要生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**Language:** {'English' if language == 'en' else 'Chinese'}\n\n")
                f.write("---\n\n")
                f.write("## Summary Content\n\n" if language == "en" else "## 摘要内容\n\n")
                f.write(summary)
            
            return str(summary_filepath)
            
        except Exception as e:
            print(f"❌ Failed to save summary: {e}")
            return None

    def auto_process_latest_episode(self, podcast_name: str, progress_tracker=None) -> tuple[bool, str]:
        """
        Automated processing of latest podcast episode - no user interaction
        
        Args:
            podcast_name: Podcast name
            progress_tracker: Progress tracker (for duplicate checking)
            
        Returns:
            tuple[bool, str]: (Whether processing was successful, episode title)
        """
        try:
            # Search channel (silent)
            channels = self.search_podcast_channel(podcast_name, quiet=True)
            if not channels:
                return False, ""
            
            selected_channel = channels[0]  # Automatically select first matching channel
            if not selected_channel['feed_url']:
                return False, ""
            
            # Get latest episode (silent)
            episodes = self.get_recent_episodes(selected_channel['feed_url'], 5, quiet=True)
            if not episodes:
                return False, ""
            
            # Process all episodes in a loop, starting from newest
            processed_count = 0
            last_episode_title = ""
            
            for i, episode in enumerate(episodes):
                episode_title = episode['title']
                last_episode_title = episode_title
                
                # Check if already processed
                if progress_tracker and progress_tracker.is_episode_processed(podcast_name, episode_title):
                    # print(f"⏭️  {podcast_name} episode already processed, skipping: {episode_title[:50]}...")
                    continue
                    
                print(f"📥 Processing new episode: {episode_title[:50]}...")
                
                # Download processing (silent download process)
                success, episode_dir = self.download_episode(episode, i+1, selected_channel['name'], quiet=True)
                if not success or not episode_dir:
                    continue
                
                # Auto transcribe
                audio_filepath = episode_dir / "audio.mp3"
                if audio_filepath.exists():
                    transcribe_success = self.transcribe_audio_smart(
                        audio_filepath, episode_title, 
                        selected_channel['name'], episode_dir, auto_transcribe=True
                    )
                    if transcribe_success:
                        # Auto summary - simulate transcribe_downloaded_files processing logic
                        if self.gemini_client:
                            # Use same summary generation logic as original code
                            self.auto_generate_summary_for_episode(
                                episode_title, selected_channel['name'], episode_dir
                            )
                        
                        # Mark as processed
                        if progress_tracker:
                            progress_tracker.mark_episode_processed(podcast_name, episode_title)
                        processed_count += 1
            
            return processed_count > 0, last_episode_title
            
        except Exception as e:
            return False, ""
    
    def auto_generate_summary_for_episode(self, episode_title: str, channel_name: str, episode_dir: Path) -> bool:
        """
        Automatically generate summary for single episode (simulate transcribe_downloaded_files logic)
        
        Args:
            episode_title: Episode title
            channel_name: Channel name
            episode_dir: Episode directory
            
        Returns:
            bool: Whether summarization was successful
        """
        try:
            # Read transcript file
            safe_channel = self.sanitize_filename(channel_name)
            safe_title = self.sanitize_filename(episode_title)
            transcript_filename = self.ensure_transcript_filename_length(safe_channel, safe_title)
            transcript_filepath = episode_dir / transcript_filename
            
            if not transcript_filepath.exists():
                return False
            
            # Read transcript content
            with open(transcript_filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract actual transcript text (skip metadata) - same logic as original code
            if "## Transcript Content" in content:
                transcript_text = content.split("## Transcript Content")[1].strip()
            elif "## 转录内容" in content:
                transcript_text = content.split("## 转录内容")[1].strip()
            elif "---" in content:
                # Fallback: content after ---
                parts = content.split("---", 1)
                if len(parts) > 1:
                    transcript_text = parts[1].strip()
                else:
                    transcript_text = content
            else:
                transcript_text = content
            
            if len(transcript_text.strip()) < 100:
                return False
            
            # Generate summary
            summary = self.generate_summary(transcript_text, episode_title)
            if not summary:
                return False
            
            # For English version, no translation needed (default English summary)
            language_choice = 'en'
            final_summary = summary
            
            # Save summary
            summary_path = self.save_summary(final_summary, episode_title, channel_name, language_choice, episode_dir)
            return summary_path is not None
            
        except Exception as e:
            return False


class Podnet:
    """Main application class for YouTube processing"""
    
    def __init__(self):
        self.searcher = YouTubeSearcher()
        self.extractor = TranscriptExtractor()
        self.summarizer = SummaryGenerator()
    
    def search_youtube_podcast(self, podcast_name: str, num_episodes: int = 5) -> List[Dict]:
        """Search for podcast episodes on YouTube using channel videos page"""
        return self.searcher.search_youtube_podcast(podcast_name, num_episodes)
    
    def auto_process_channel_latest_video(self, channel_name: str, progress_tracker=None) -> tuple[bool, str]:
        """
        Automated processing of channel's latest video - no user interaction
        
        Args:
            channel_name: Channel name (without @ symbol)
            progress_tracker: Progress tracker (for duplicate checking)
            
        Returns:
            tuple[bool, str]: (Whether processing was successful, video title)
        """
        try:
            # Search for channel's latest video
            episodes = self.searcher.search_youtube_podcast(channel_name, num_episodes=10)
            if not episodes:
                return False, ""
            
            # Process all videos in a loop, starting from newest
            processed_count = 0
            last_video_title = ""
            
            for episode in episodes:
                video_title = episode.get('title', 'Unknown')
                last_video_title = video_title
                
                # Check if already processed
                if progress_tracker and progress_tracker.is_video_processed(channel_name, video_title):
                    # print(f"⏭️  @{channel_name} video already processed, skipping: {video_title[:50]}...")
                    continue
                    
                video_url = episode.get('url', '')
                if not video_url:
                    continue
                
                # Extract video ID
                import re
                video_id_match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', video_url)
                if not video_id_match:
                    continue
                
                video_id = video_id_match.group(1)
                
                # Get video info
                video_info = self.searcher.get_video_info(video_id)
                title = episode.get('title', video_info.get('title', 'Unknown'))
                channel_name_from_video = video_info.get('channel_name', channel_name)
                published_date = episode.get('published_date', 'Recent')
                
                print(f"📥 Processing new video: {title[:50]}...")
                
                # Create episode directory
                episode_dir = self.extractor.create_episode_folder(
                    channel_name_from_video, 
                    title, 
                    published_date
                )
                
                # Try to extract transcript
                transcript = self.extractor.extract_youtube_transcript(
                    video_id, 
                    video_url, 
                    title, 
                    episode_dir=episode_dir
                )
                
                if transcript:
                    # Save transcript
                    transcript_filename = self.extractor.save_transcript(
                        transcript, 
                        title, 
                        channel_name_from_video, 
                        published_date, 
                        episode_dir
                    )
                    
                    # Generate summary
                    if self.summarizer.gemini_client:
                        summary = self.summarizer.generate_summary(transcript, title)
                        if summary:
                            # For English version, no translation needed (default English summary)
                            final_summary = summary
                            
                            self.summarizer.save_summary(
                                final_summary, 
                                title, 
                                episode_dir, 
                                channel_name_from_video, 
                                episode_dir
                            )
                    
                    # Mark as processed
                    if progress_tracker:
                        progress_tracker.mark_video_processed(channel_name, video_title)
                    processed_count += 1
            
            return processed_count > 0, last_video_title
            
        except Exception as e:
            return False, ""

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
                            # For English version, use English summary directly
                            final_summary = summary
                            
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