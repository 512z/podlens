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

# Whisper 转录支持
try:
    import mlx_whisper
    import mlx.core as mx
    MLX_WHISPER_AVAILABLE = True
    # 检查 MLX 设备可用性
    MLX_DEVICE = mx.default_device()
    # print(f"🎯 MLX Whisper 可用，使用设备: {MLX_DEVICE}")
except ImportError:
    MLX_WHISPER_AVAILABLE = False
    # print("⚠️  MLX Whisper 不可用")

# Groq API 极速转录
try:
    from groq import Groq
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_AVAILABLE = bool(GROQ_API_KEY)
    # if GROQ_AVAILABLE:
    #     print(f"🚀 Groq API 可用，已启用超快转录")
    # else:
    #     print("⚠️  未设置 Groq API 密钥")
except ImportError:
    GROQ_AVAILABLE = False
    # print("⚠️  未安装 Groq SDK")

# Gemini API 摘要支持
try:
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# 检查转录功能可用性
TRANSCRIPTION_AVAILABLE = MLX_WHISPER_AVAILABLE or GROQ_AVAILABLE

# YouTube 转录提取
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import TextFormatter
    YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError:
    YOUTUBE_TRANSCRIPT_AVAILABLE = False

# YouTube 音频下载备用方案
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    print("⚠️  未安装 yt-dlp，YouTube 音频下载备用方案不可用")

# 本地 Whisper 免费音频转录（用于 YouTube）
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
            print(f"无法获取视频标题: {e}")
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
            print(f"YouTube搜索失败: {e}")
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
        """Clean filename, remove unsafe characters"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = filename.strip('._')
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def ensure_filename_length(self, prefix: str, safe_title: str, extension: str = ".mp3") -> str:
        """
        确保完整文件名不超过文件系统限制（255字符）
        
        Args:
            prefix: 文件前缀（例如："youtube_"）
            safe_title: 清理后的标题
            extension: 文件扩展名（默认：.mp3）
        
        Returns:
            str: 符合长度限制的最终文件名
        """
        # 计算固定部分：前缀和扩展名
        fixed_length = len(prefix) + len(extension)
        
        # 标题的最大可用长度
        max_title_length = 255 - fixed_length
        
        # 如果标题能放下，直接使用
        if len(safe_title) <= max_title_length:
            return f"{prefix}{safe_title}{extension}"
        
        # 如果太长，截断标题
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
            print("❌ 未检测到yt-dlp，无法下载音频")
            return None
        
        try:
            # Clean filename
            safe_title = self.sanitize_filename(title)
            audio_filename = self.ensure_filename_length("youtube_", safe_title)
            audio_filepath = self.media_dir / audio_filename
            
            # Check if file already exists
            if audio_filepath.exists():
                print(f"⚠️  音频文件已存在: {audio_filename}")
                return audio_filepath
            
            print(f"📥 正在下载YouTube音频: {title}")
            
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
            
            print(f"✅ 音频下载完成: {audio_filename}")
            return audio_filepath
            
        except Exception as e:
            print(f"❌ 音频下载失败: {e}")
            return None
    
    def compress_audio_file(self, input_file: Path, output_file: Path) -> bool:
        """智能两级压缩音频文件至Groq API限制以下 (从Apple模块复制)
        首选64k保证质量，如果仍>25MB则降至48k"""
        try:
            print(f"🔧 正在压缩音频文件: {input_file.name}")
            
            # 第一级压缩：64k (优先保证质量)
            print("📊 第一级压缩: 16KHz 单声道, 64kbps MP3")
            
            # 生成安全的临时文件名，不超过255字符
            original_name = output_file.stem  # 不含扩展名的文件名
            prefix = "temp_64k_"
            extension = output_file.suffix
            
            # 计算原文件名部分的最大长度
            max_name_length = 255 - len(prefix) - len(extension)
            
            # 如果需要，截断原文件名
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
            
            # 运行第一级压缩
            result = subprocess.run(
                cmd_64k,
                capture_output=True,
                text=True,
                check=True
            )
            
            # 检查64k压缩后的文件大小
            compressed_size_mb = self.get_file_size_mb(temp_64k_file)
            print(f"📊 64k压缩后大小: {compressed_size_mb:.1f}MB")
            
            if compressed_size_mb <= 25:
                # 64k压缩满足要求，使用64k结果
                temp_64k_file.rename(output_file)
                print(f"✅ 64k压缩完成: {output_file.name} ({compressed_size_mb:.1f}MB)")
                return True
            else:
                # 64k压缩后仍>25MB，进行第二级48k压缩
                print(f"⚠️  64k压缩后仍超25MB，进行第二级48k压缩...")
                print("📊 第二级压缩: 16KHz 单声道, 48kbps MP3")
                
                cmd_48k = [
                    'ffmpeg',
                    '-i', str(input_file),
                    '-ar', '16000',
                    '-ac', '1',
                    '-b:a', '48k',
                    '-y',
                    str(output_file)
                ]
                
                # 运行第二级压缩
                result = subprocess.run(
                    cmd_48k,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                final_size_mb = self.get_file_size_mb(output_file)
                print(f"✅ 48k压缩完成: {output_file.name} ({final_size_mb:.1f}MB)")
                
                # 清理临时文件
                if temp_64k_file.exists():
                    temp_64k_file.unlink()
                
                return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 压缩失败: {e}")
            # 清理临时文件
            if 'temp_64k_file' in locals() and temp_64k_file.exists():
                temp_64k_file.unlink()
            return False
        except Exception as e:
            print(f"❌ 压缩出错: {e}")
            # 清理临时文件
            if 'temp_64k_file' in locals() and temp_64k_file.exists():
                temp_64k_file.unlink()
            return False
    
    def transcribe_with_groq(self, audio_file: Path) -> dict:
        """Transcribe audio file using Groq API (copied from Apple section)"""
        try:
            print(f"🚀 Groq API转录: {audio_file.name}")
            print("🧠 使用模型: whisper-large-v3")
            
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
            
            print(f"✅ Groq转录完成! 用时: {processing_time:.1f}秒")
            
            return {
                'text': text,
                'language': language,
                'processing_time': processing_time,
                'speed_ratio': speed_ratio,
                'method': 'Groq API whisper-large-v3'
            }
            
        except Exception as e:
            print(f"❌ Groq转录失败: {e}")
            return None
    
    def transcribe_with_mlx(self, audio_file: Path) -> dict:
        """Transcribe audio file using MLX Whisper (copied from Apple section)"""
        try:
            print(f"🎯 MLX Whisper转录: {audio_file.name}")
            print("🧠 使用模型: mlx-community/whisper-medium")
            
            start_time = time.time()
            
            result = mlx_whisper.transcribe(
                str(audio_file),
                path_or_hf_repo=self.whisper_model_name
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            file_size_mb = self.get_file_size_mb(audio_file)
            speed_ratio = file_size_mb / processing_time * 60 if processing_time > 0 else 0
            
            print(f"✅ MLX转录完成! 用时: {processing_time:.1f}秒")
            
            return {
                'text': result['text'],
                'language': result.get('language', 'en'),
                'processing_time': processing_time,
                'speed_ratio': speed_ratio,
                'method': 'MLX Whisper medium'
            }
            
        except Exception as e:
            print(f"❌ MLX转录失败: {e}")
            return None
    
    def transcribe_audio_smart(self, audio_file: Path, title: str) -> Optional[str]:
        """Smart audio transcription: choose best method based on file size (copied and simplified from Apple section)"""
        if not (GROQ_AVAILABLE or MLX_WHISPER_AVAILABLE):
            print("❌ 没有可用的转录服务")
            return None
        
        try:
            print(f"🎙️  开始转录: {title}")
            
            # Check file size
            file_size_mb = self.get_file_size_mb(audio_file)
            print(f"📊 音频文件大小: {file_size_mb:.1f}MB")
            
            groq_limit = 25  # MB
            transcript_result = None
            compressed_file = None
            original_size = file_size_mb
            final_size = file_size_mb
            
            # Smart transcription strategy
            if file_size_mb <= groq_limit and GROQ_AVAILABLE:
                # Case 1: File < 25MB, use Groq directly with MLX fallback
                print("✅ 文件大小在Groq限制内，使用超快转录")
                transcript_result = self.transcribe_with_groq(audio_file)
                
                # Fallback to MLX if Groq fails
                if not transcript_result and MLX_WHISPER_AVAILABLE:
                    print("🔄 Groq转录失败，切换到MLX Whisper...")
                    transcript_result = self.transcribe_with_mlx(audio_file)
            
            elif file_size_mb > groq_limit:
                # Case 2: File > 25MB, need compression
                print("⚠️  文件超出Groq限制，开始压缩...")
                
                # 生成安全的压缩文件名
                original_name = audio_file.stem
                compressed_name = f"compressed_{original_name}"
                extension = audio_file.suffix
                
                # 确保压缩文件名不超出限制
                max_compressed_length = 255 - len(extension)
                if len(compressed_name) > max_compressed_length:
                    # 截断以适合
                    truncated_name = compressed_name[:max_compressed_length]
                    compressed_file = audio_file.parent / f"{truncated_name}{extension}"
                else:
                    compressed_file = audio_file.parent / f"{compressed_name}{extension}"
                
                if self.compress_audio_file(audio_file, compressed_file):
                    compressed_size = self.get_file_size_mb(compressed_file)
                    final_size = compressed_size
                    print(f"📊 压缩后大小: {compressed_size:.1f}MB")
                    
                    if compressed_size <= groq_limit and GROQ_AVAILABLE:
                        # Case 2a: After compression, within Groq limit with MLX fallback
                        print("✅ 压缩后在Groq限制内，使用超快转录")
                        transcript_result = self.transcribe_with_groq(compressed_file)
                        
                        # Fallback to MLX if Groq fails
                        if not transcript_result and MLX_WHISPER_AVAILABLE:
                            print("🔄 Groq转录失败，切换到MLX Whisper...")
                            transcript_result = self.transcribe_with_mlx(compressed_file)
                    else:
                        # Case 2b: Still over limit, use MLX
                        print("⚠️  压缩后仍超出限制，使用MLX转录")
                        if MLX_WHISPER_AVAILABLE:
                            transcript_result = self.transcribe_with_mlx(compressed_file)
                        else:
                            print("❌ 未检测到MLX Whisper，无法转录大文件")
                            return None
                else:
                    # Compression failed, try MLX
                    print("❌ 压缩失败，尝试本地MLX转录")
                    if MLX_WHISPER_AVAILABLE:
                        transcript_result = self.transcribe_with_mlx(audio_file)
                    else:
                        print("❌ 未检测到MLX Whisper，转录失败")
                        return None
            
            else:
                # Case 3: Groq not available, use MLX
                print("⚠️  未检测到Groq API，使用本地MLX转录")
                if MLX_WHISPER_AVAILABLE:
                    transcript_result = self.transcribe_with_mlx(audio_file)
                else:
                    print("❌ 未检测到MLX Whisper，转录失败")
                    return None
            
            # Handle transcription result
            if not transcript_result:
                print("❌ 所有转录方式均失败")
                return None
            
            # Clean up files
            try:
                # Delete original audio file
                audio_file.unlink()
                print(f"🗑️  已删除音频文件: {audio_file.name}")
                
                # Delete compressed file (if exists)
                if compressed_file and compressed_file.exists():
                    compressed_file.unlink()
                    print(f"🗑️  已删除压缩文件: {compressed_file.name}")
                    
            except Exception as e:
                print(f"⚠️  删除文件失败: {e}")
            
            return transcript_result['text']
            
        except Exception as e:
            print(f"❌ 转录流程失败: {e}")
            return None
    
    def extract_youtube_transcript(self, video_id: str, video_url: str = None, title: str = "Unknown") -> Optional[str]:
        """Extract transcript from YouTube video, with audio download fallback"""
        if not YOUTUBE_TRANSCRIPT_AVAILABLE:
            print("YouTube转录API不可用，尝试音频下载备用方案...")
            if video_url and YT_DLP_AVAILABLE:
                return self.audio_download_fallback(video_url, title)
            return None
        
        try:
            # Clean the video ID - remove any extra characters
            clean_video_id = video_id.strip()
            if len(clean_video_id) != 11:
                print(f"无效的视频ID长度: {len(clean_video_id)} (应为11位)")
                if video_url and YT_DLP_AVAILABLE:
                    return self.audio_download_fallback(video_url, title)
                return None
            
            print(f"🎯 优先使用YouTube转录API: {clean_video_id}")
            
            # Try multiple times in case of network issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        print(f"  重试第{attempt + 1}/{max_retries}次...")
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
                        print(f"  第{attempt + 1}次尝试未找到可用转录")
                        continue
                    
                    print(f"  找到 {len(available_transcripts)} 种转录语言:")
                    for i, trans_info in enumerate(available_transcripts, 1):
                        status = "自动生成" if trans_info['is_generated'] else "手动字幕"
                        translatable = "可翻译" if trans_info['is_translatable'] else "不可翻译"
                        print(f"    {i}. {trans_info['language_code']} - {trans_info['language_name']} ({status}, {translatable})")
                    
                    # If only one transcript available, use it directly
                    if len(available_transcripts) == 1:
                        selected_transcript = available_transcripts[0]['transcript']
                        print(f"  只有一种转录可用，自动选择: {available_transcripts[0]['language_code']}")
                    else:
                        # Multiple transcripts available, let user choose
                        print(f"\n  检测到多种转录语言，请选择:")
                        for i, trans_info in enumerate(available_transcripts, 1):
                            status = "自动生成" if trans_info['is_generated'] else "手动字幕"
                            print(f"    {i}. {trans_info['language_code']} - {trans_info['language_name']} ({status})")
                        
                        while True:
                            try:
                                choice = input(f"  请选择转录语言 (1-{len(available_transcripts)}), 或按回车使用第一个: ").strip()
                                
                                if not choice:
                                    # Default to first option
                                    selected_index = 0
                                    print(f"  使用默认选择: {available_transcripts[0]['language_code']}")
                                    break
                                else:
                                    selected_index = int(choice) - 1
                                    if 0 <= selected_index < len(available_transcripts):
                                        print(f"  已选择: {available_transcripts[selected_index]['language_code']} - {available_transcripts[selected_index]['language_name']}")
                                        break
                                    else:
                                        print(f"  请输入 1 到 {len(available_transcripts)} 之间的数字")
                                        continue
                            except ValueError:
                                print(f"  请输入有效的数字 (1-{len(available_transcripts)})")
                                continue
                        
                        selected_transcript = available_transcripts[selected_index]['transcript']
                    
                    # Fetch the selected transcript
                    try:
                        print(f"  正在获取转录: {selected_transcript.language_code}")
                        transcript_data = selected_transcript.fetch()
                        
                        if not transcript_data:
                            print(f"    {selected_transcript.language_code}未返回数据")
                            # If selected transcript fails, try others
                            print("  尝试其他可用转录...")
                            for trans_info in available_transcripts:
                                if trans_info['transcript'] == selected_transcript:
                                    continue
                                try:
                                    print(f"  备用转录: {trans_info['language_code']}")
                                    transcript_data = trans_info['transcript'].fetch()
                                    if transcript_data:
                                        print(f"  备用转录成功: {trans_info['language_code']}")
                                        break
                                except Exception as e:
                                    print(f"    备用转录{trans_info['language_code']}失败: {e}")
                                    continue
                        
                        if not transcript_data:
                            print(f"  第{attempt + 1}次尝试: 所有转录都失败")
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
                                print(f"    警告: 未知片段格式: {type(entry)}")
                        
                        if text_parts:
                            full_text = " ".join(text_parts).strip()
                            if full_text:
                                print(f"✅ YouTube转录API成功! (共{len(full_text)}个字符)")
                                return full_text
                            else:
                                print(f"    合并后为空")
                        else:
                            print(f"    未提取到文本")
                        
                    except Exception as e3:
                        error_msg = str(e3)
                        print(f"    获取选中转录失败: {error_msg}")
                        
                        # Check for specific error types
                        if "no element found" in error_msg.lower():
                            print(f"    这可能是XML解析错误，可能是临时问题")
                        elif "not available" in error_msg.lower():
                            print(f"    该转录不可用")
                        else:
                            print(f"    未知错误类型: {type(e3)}")
                    
                    # If we get here, selected transcript failed
                    print(f"  第{attempt + 1}次尝试失败")
                    
                except Exception as e2:
                    error_msg = str(e2)
                    print(f"  第{attempt + 1}次获取转录列表失败: {error_msg}")
                    
                    # Check for specific error types
                    if "no element found" in error_msg.lower():
                        print(f"    XML解析错误 - 可能是临时问题，重试中...")
                        continue
                    elif "not available" in error_msg.lower() or "disabled" in error_msg.lower():
                        print(f"    视频转录被禁用或不可用")
                        break  # No point retrying
                    else:
                        print(f"    未知错误: {type(e2)}")
                        if attempt == max_retries - 1:  # Last attempt
                            import traceback
                            print(f"    完整错误信息:")
                            traceback.print_exc()
                        continue
            
            print("❌ YouTube转录API失败，尝试音频下载备用方案...")
            # Fallback to audio download if transcript extraction failed
            if video_url and YT_DLP_AVAILABLE:
                return self.audio_download_fallback(video_url, title)
            else:
                print("❌ 音频下载备用方案不可用")
                return None
            
        except Exception as e:
            print(f"提取YouTube转录出错: {e}")
            print("🔄 尝试音频下载备用方案...")
            if video_url and YT_DLP_AVAILABLE:
                return self.audio_download_fallback(video_url, title)
            return None
    
    def audio_download_fallback(self, video_url: str, title: str) -> Optional[str]:
        """Audio download and transcription fallback solution"""
        print("🎵 开始音频下载备用方案...")
        
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
        确保输出文件名（转录/摘要）不超过文件系统限制（255字符）
        YouTube格式：prefix + title + extension（无频道名）
        
        Args:
            prefix: 文件前缀（如"Transcript_", "Summary_"）
            safe_title: 清理后的标题
            extension: 文件扩展名（默认：.md）
        
        Returns:
            str: 符合长度限制的最终文件名
        """
        # 计算固定部分长度：前缀 + 扩展名
        fixed_length = len(prefix) + len(extension)
        
        # 最大可用内容长度
        max_content_length = 255 - fixed_length
        
        if len(safe_title) <= max_content_length:
            return f"{prefix}{safe_title}{extension}"
        else:
            truncated_title = safe_title[:max_content_length]
            return f"{prefix}{truncated_title}{extension}"
    
    def ensure_transcript_filename_length(self, safe_title: str) -> str:
        """确保转录文件名长度"""
        return self.ensure_output_filename_length("Transcript_", safe_title)
    
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


class SummaryGenerator:
    """Handles summary generation using new Gemini API for YouTube"""
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.gemini_client = None
        
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.gemini_client = genai
                print("✅ Gemini API已成功初始化用于YouTube！")
            except Exception as e:
                print(f"⚠️  初始化Gemini客户端出错: {e}")
                self.gemini_client = None
        else:
            if not self.api_key:
                print("请将Gemini API密钥添加到.env文件中")
            self.gemini_client = None
    
    def generate_summary(self, transcript: str, title: str) -> Optional[str]:
        """Generate summary from transcript using new Gemini API"""
        if not self.gemini_client:
            print("Gemini API不可用或API密钥未配置")
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
            
            print("正在生成摘要...")
            response = self.gemini_client.GenerativeModel("gemini-2.5-flash-preview-05-20").generate_content(prompt)
            
            # Handle the response properly
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                print("Gemini API响应格式异常")
                return None
            
        except Exception as e:
            print(f"生成摘要出错: {e}")
            return None
    
    def translate_to_chinese(self, text: str) -> Optional[str]:
        """Translate text to Chinese using Gemini API"""
        if not self.gemini_client:
            print("Gemini API不可用或API密钥未配置")
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
                print("Gemini API响应格式异常")
                return None
            
        except Exception as e:
            print(f"翻译为中文出错: {e}")
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
        print("🎥 欢迎使用 Podnet - 您的 YouTube 播客助手工具！")
        print("=" * 50)
        
        while True:
            # First ask what type of information the user wants to provide
            print("\n您感兴趣的信息类型是？")
            print("- name: 播客/频道名称")
            print("- link: YouTube 视频或频道链接") 
            print("- script: 直接提供转录文本内容")
            print("\n示例：")
            print("  name: lex fridman, or lexfridman (频道的@username)")
            print("  link: https://www.youtube.com/watch?v=qCbfTN-caFI (单视频链接)")
            print("  script: 将文本内容放入 scripts/script.txt")
            
            content_type = input("\n请选择类型 (name/link/script) 或输入 'quit' 退出: ").strip().lower()
            
            if content_type in ['quit', 'exit', 'q']:
                print("🔙 返回主菜单")
                break
            
            if content_type not in ['name', 'link', 'script']:
                print("请选择 'name'、'link'、'script' 或 'quit'。")
                continue
            
            # Handle script input
            if content_type == 'script':
                # Look for script content in scripts/script.txt
                script_file_path = Path("scripts/script.txt")
                
                if not script_file_path.exists():
                    print("❌ 未找到脚本文件！")
                    print("请在 scripts/script.txt 路径下创建文件")
                    print("请将您的转录内容放入该文件后重试。")
                    continue
                
                try:
                    with open(script_file_path, 'r', encoding='utf-8') as f:
                        transcript = f.read().strip()
                    
                    if not transcript:
                        print("❌ 脚本文件为空。")
                        print("请将您的转录内容添加到 scripts/script.txt")
                        continue
                    
                    print(f"✅ 成功加载脚本，来自 scripts/script.txt（{len(transcript)} 个字符）")
                    
                except Exception as e:
                    print(f"❌ 读取脚本文件出错: {e}")
                    continue
                
                if len(transcript) < 50:
                    print("⚠️  转录内容似乎很短，您确定内容完整吗？")
                    confirm = input("仍然继续？(y/n): ").strip().lower()
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
                
                print(f"✅ 已收到脚本内容（{len(transcript)} 个字符）")
                
                # Skip to action selection
                want_transcripts = True  # Always save transcript for script
                want_summaries = True   # Always generate summary for script
            
            else:
                # Handle name/link input (existing logic)
                user_input = input(f"\n请输入 {content_type}: ").strip()
                
                if not user_input:
                    print(f"请输入一个 {content_type}。")
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
                            print(f"🎥 检测到单个视频链接: {user_input}")
                        else:
                            print("❌ YouTube 视频链接格式无效。")
                            continue
                    elif "/@" in user_input and "/videos" in user_input:
                        # Channel videos link
                        is_channel_link = True
                        # Extract channel name from link
                        channel_match = re.search(r'/@([^/]+)', user_input)
                        if channel_match:
                            channel_name = channel_match.group(1)
                            print(f"🎥 检测到频道链接: @{channel_name}")
                        else:
                            print("❌ YouTube 频道链接格式无效。")
                            continue
                    else:
                        print("❌ 不支持的 YouTube 链接格式。请使用视频链接 (youtube.com/watch?v=...) 或频道视频链接 (youtube.com/@channel/videos)")
                        continue
                elif content_type == 'link':
                    print("❌ 请提供有效的 YouTube 链接。")
                    continue
                else:
                    # Regular name input - use existing logic
                    channel_name = user_input
                
                if is_single_video:
                    # Skip episode selection for single video
                    selected_episodes = episodes
                    print(f"\n✅ 正在处理单个视频")
                else:
                    # Ask how many recent episodes the user wants (for name or channel link)
                    while True:
                        try:
                            num_episodes = input("您想查看最近多少期播客？(默认: 5): ").strip()
                            if not num_episodes:
                                num_episodes = 5
                            else:
                                num_episodes = int(num_episodes)
                            
                            if num_episodes <= 0:
                                print("请输入一个正整数。")
                                continue
                            elif num_episodes > 20:
                                print("最多只能选择 20 期。")
                                continue
                            else:
                                break
                        except ValueError:
                            print("请输入有效的数字。")
                            continue
                    
                    # Search for episodes on YouTube
                    print(f"\n🔍 正在 YouTube 上搜索 '{channel_name}' ...")
                    
                    episodes = self.searcher.search_youtube_podcast(channel_name, num_episodes)
                    
                    if not episodes:
                        print("❌ 未找到相关节目。请尝试其他搜索词。")
                        continue
                    
                    # Display episodes with platform information
                    print(f"\n📋 找到 {len(episodes)} 期最新节目：")
                    for i, episode in enumerate(episodes, 1):
                        print(f"{i}. 🎥 [YouTube] '{episode['title']}' - {episode['published_date']}")
                    
                    # Get episode selection FIRST
                    episode_selection = input(f"\n您对哪些节目感兴趣？(1-{len(episodes)}，如 '1,3,5' 或 'all'): ").strip()
                    
                    if episode_selection.lower() == 'all':
                        selected_episodes = episodes
                    else:
                        try:
                            selected_indices = [int(x.strip()) - 1 for x in episode_selection.split(',')]
                            selected_episodes = [episodes[i] for i in selected_indices if 0 <= i < len(episodes)]
                        except (ValueError, IndexError):
                            print("节目选择无效，请重试。")
                            continue
                    
                    if not selected_episodes:
                        print("未选择有效的节目。")
                        continue
                    
                    print(f"\n✅ 已选择 {len(selected_episodes)} 期节目")
                
                # THEN ask what to do with selected episodes (only for name/link)
                print("\n您希望对所选节目进行什么操作？")
                print("1. 获取节目的转录文本")
                print("2. 获取节目的摘要")
                print("3. 获取转录文本和摘要")
                
                action = input("请选择 (1, 2, 或 3): ").strip()
                
                if action not in ['1', '2', '3']:
                    print("请选择有效的选项 (1, 2, 或 3)")
                    continue
                
                # Parse action
                want_transcripts = action in ['1', '3']
                want_summaries = action in ['2', '3']
            
            # Ask for language preference (common for all types)
            language = input("\n您希望输出什么语言？(en/ch): ").strip().lower()
            want_chinese = language == 'ch'
            
            # Process selected episodes
            print(f"\n🚀 正在处理 {len(selected_episodes)} 期节目 ...")
            
            for episode in selected_episodes:
                print(f"\n📝 正在处理 {f'📜 [脚本]' if episode['platform'] == 'script' else '🎥 [YouTube]'}: {episode['title']}")
                
                transcript_content = None
                
                if episode['platform'] == 'script':
                    # Use the script content directly
                    transcript_content = transcript
                    print("✅ 脚本内容加载成功！")
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
                            print("✅ 成功提取 YouTube 转录文本！")
                    
                    # If no transcript available, create placeholder
                    if not transcript_content and (want_transcripts or want_summaries):
                        print("⚠️  此视频没有可用的 YouTube 转录文本")
                        print("   该视频可能没有自动生成的字幕")
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
                        print("✅ 已创建节目信息（无转录文本）")
                
                if not transcript_content:
                    print("❌ 无法提取该节目的转录文本")
                    continue
                
                # Save transcript if requested
                if want_transcripts and transcript_content:
                    transcript_path = self.extractor.save_transcript(transcript_content, episode['title'])
                    print(f"💾 转录文本已保存至: {transcript_path}")
                
                # Generate and save summary if requested
                if want_summaries and transcript_content:
                    # Check if transcript has actual content (not just placeholder)
                    if len(transcript_content.strip()) > 100 and "Note: No transcript available" not in transcript_content:
                        summary = self.summarizer.generate_summary(transcript_content, episode['title'])
                        if summary:
                            # Translate summary to Chinese if requested
                            final_summary = summary
                            if want_chinese:
                                print("🔄 正在将摘要翻译为中文 ...")
                                translated_summary = self.summarizer.translate_to_chinese(summary)
                                if translated_summary:
                                    final_summary = translated_summary
                                    print("✅ 摘要已翻译为中文！")
                                else:
                                    print("⚠️  翻译失败，使用原始摘要")
                            
                            summary_path = self.summarizer.save_summary(
                                final_summary, 
                                episode['title'], 
                                self.extractor.output_dir
                            )
                            print(f"📄 摘要已保存至: {summary_path}")
                        else:
                            print("❌ 无法生成摘要")
                    else:
                        print("⚠️  跳过摘要 - 无有效转录内容")
                
                print("✅ 节目处理完成！")
            
            print(f"\n🎉 全部完成！文件已保存至: {self.extractor.output_dir}")
            
            # Ask about visualization if any content was processed
            if selected_episodes:
                self.ask_for_visualization(selected_episodes, want_chinese)
            
            # Ask if the user wants to continue
            continue_choice = input("\n继续在 YouTube 模式下吗？(y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes', 'yes']:
                print("🔙 返回主菜单")
                break
    
    def ask_for_visualization(self, processed_episodes: List[Dict], want_chinese: bool):
        """
        询问用户是否要生成可视化故事
        
        Args:
            processed_episodes: 已处理的剧集列表
            want_chinese: 是否使用中文
        """
        if not processed_episodes:
            return
        
        print(f"\n🎨 可视化故事生成:")
        visualize_choice = input("生成可视化故事? (y/n): ").strip().lower()
        
        if visualize_choice not in ['y', 'yes', '是']:
            return
        
        # Ask whether to use transcript or summary
        print("📄 内容来源:")
        content_choice = input("基于转录文本还是摘要生成可视化? (t/s): ").strip().lower()
        
        if content_choice not in ['t', 's']:
            print("选择无效，跳过可视化生成。")
            return
        
        # Import visual module based on language
        try:
            if want_chinese:
                from .visual_ch import generate_visual_story
            else:
                from .visual_en import generate_visual_story
        except ImportError:
            visual_module = "visual_ch.py" if want_chinese else "visual_en.py"
            print(f"❌ 未找到可视化模块。请确保{visual_module}在podlens文件夹中。")
            return
        
        # Process each episode
        visual_success_count = 0
        
        for i, episode in enumerate(processed_episodes, 1):
            if episode['platform'] == 'script':
                title = episode['title']
            else:
                title = episode['title']
            
            print(f"\n[{i}/{len(processed_episodes)}] 正在生成可视化故事: {title}")
            
            # Build file paths - using the same naming pattern as save functions
            # Use the same sanitization logic as save_transcript and save_summary
            safe_title = re.sub(r'[^\w\s-]', '', title).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            
            if content_choice == 't':
                # Use transcript
                source_filename = self.extractor.ensure_transcript_filename_length(safe_title)
                content_type = "转录文本"
            else:
                # Use summary
                source_filename = self.extractor.ensure_summary_filename_length(safe_title)
                content_type = "摘要"
            
            source_filepath = self.extractor.output_dir / source_filename
            
            if not source_filepath.exists():
                print(f"❌ {content_type}文件未找到: {source_filename}")
                continue
            
            # Generate visual story
            if generate_visual_story(str(source_filepath)):
                visual_success_count += 1
                print(f"✅ 可视化故事生成成功!")
            else:
                print(f"❌ 可视化故事生成失败")
        
        print(f"\n📊 可视化故事生成完成! 成功: {visual_success_count}/{len(processed_episodes)}")
        if visual_success_count > 0:
            print(f"📁 可视化故事保存在: {self.extractor.output_dir.absolute()}")


def main():
    """Main function"""
    print("🎧🎥 播客转录与摘要工具")
    print("=" * 50)
    print("支持 Apple Podcast 和 YouTube 平台")
    print("=" * 50)
    
    while True:
        # Let the user choose the information source
        print("\n📡 请选择信息来源：")
        print("1. Apple Podcast")
        print("2. YouTube")
        print("0. 退出")
        
        choice = input("\n请输入您的选择 (1/2/0): ").strip()
        
        if choice == '0':
            print("👋 再见！")
            break
        elif choice == '1':
            # Apple Podcast processing logic
            print("\n🎧 您选择了 Apple Podcast")
            print("=" * 40)
            apple_main()
        elif choice == '2':
            # YouTube processing logic
            print("\n🎥 您选择了 YouTube")
            print("=" * 40)
            youtube_main()
        else:
            print("❌ 选择无效，请输入 1、2 或 0")


def apple_main():
    """Apple Podcast main processing function"""
    explorer = ApplePodcastExplorer()
    
    while True:
        # Get user input
        podcast_name = input("\n请输入您要搜索的播客频道名称（或直接回车返回主菜单）: ").strip()
        
        if not podcast_name:
            print("🔙 返回主菜单")
            break
        
        # Search for channels
        channels = explorer.search_podcast_channel(podcast_name)
        
        # Display channels and let user select
        selected_index = explorer.display_channels(channels)
        
        if selected_index == -1:
            continue
        
        selected_channel = channels[selected_index]
        
        # Check if RSS feed URL is available
        if not selected_channel['feed_url']:
            print("❌ 该频道没有可用的 RSS 订阅链接")
            continue
        
        # Ask user how many episodes to preview
        episode_limit_input = input("请选择要预览的节目数量（默认 10）: ").strip()
        if episode_limit_input:
            try:
                episode_limit = int(episode_limit_input)
                episode_limit = max(1, min(episode_limit, 50))  # Limit between 1-50
            except ValueError:
                print("输入无效，使用默认值 10")
                episode_limit = 10
        else:
            episode_limit = 10
        
        episodes = explorer.get_recent_episodes(selected_channel['feed_url'], episode_limit)
        
        # Display episodes
        explorer.display_episodes(episodes, selected_channel['name'])
        
        # Ask if user wants to download
        explorer.download_episodes(episodes, selected_channel['name'])
        
        # Ask if user wants to continue
        continue_search = input("\n继续搜索其他频道？(y/n): ").strip().lower()
        if continue_search not in ['y', 'yes']:
            print("🔙 返回主菜单")
            break


