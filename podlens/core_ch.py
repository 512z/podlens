#!/usr/bin/env python3
"""
PodLens Core Classes - 为自动化优化的核心类
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
from .youtube_ch import YouTubeSearcher, TranscriptExtractor, SummaryGenerator


class ApplePodcastExplorer:
    """Apple播客频道探索工具"""
    
    def __init__(self):
        """初始化HTTP会话"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        # 创建根输出文件夹
        self.root_output_dir = Path("outputs")
        self.root_output_dir.mkdir(exist_ok=True)
        
        # 初始化MLX Whisper模型 - 始终使用medium模型
        self.whisper_model_name = 'mlx-community/whisper-medium'
        
        # Groq客户端初始化
        if GROQ_AVAILABLE:
            self.groq_client = Groq(api_key=GROQ_API_KEY)
        else:
            self.groq_client = None
            
        # Gemini客户端初始化
        self.api_key = os.getenv('GEMINI_API_KEY')
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.gemini_client = genai
            except Exception as e:
                print(f"⚠️  Gemini客户端初始化失败: {e}")
                self.gemini_client = None
        else:
            self.gemini_client = None
    
    def load_whisper_model(self):
        """
        设置MLX Whisper模型 - 始终使用medium模型
        """
        if not MLX_WHISPER_AVAILABLE:
            print("❌ MLX Whisper不可用")
            return False
        
        try:
            print(f"📥 设置MLX Whisper模型: {self.whisper_model_name}")
            print("ℹ️  首次使用会下载模型文件，请耐心等待...")
            return True
        except Exception as e:
            print(f"❌ 设置MLX Whisper模型失败: {e}")
            return False
    
    def search_podcast_channel(self, podcast_name: str, quiet: bool = False) -> List[Dict]:
        """
        搜索播客频道
        
        Args:
            podcast_name: 播客频道名称
            quiet: 是否静默处理
        
        Returns:
            List[Dict]: 播客频道信息列表
        """
        try:
            if not quiet:
                print(f"正在搜索播客频道: {podcast_name}")
            
            search_url = "https://itunes.apple.com/search"
            params = {
                'term': podcast_name,
                'media': 'podcast',
                'entity': 'podcast',
                'limit': 10  # 获取多个匹配的播客频道
            }
            
            response = self.session.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            channels = []
            for result in data.get('results', []):
                channel = {
                    'name': result.get('collectionName', '未知频道'),
                    'artist': result.get('artistName', '未知作者'),
                    'feed_url': result.get('feedUrl', ''),
                    'genre': ', '.join(result.get('genres', [])),
                    'description': result.get('description', '无描述')
                }
                channels.append(channel)
            
            return channels
            
        except Exception as e:
            if not quiet:
                print(f"搜索频道出错: {e}")
            return []
    
    def get_recent_episodes(self, feed_url: str, limit: int = 10, quiet: bool = False) -> List[Dict]:
        """
        获取播客频道的最新剧集
        
        Args:
            feed_url: RSS订阅地址
            limit: 返回剧集数量上限
            quiet: 是否静默处理
        
        Returns:
            List[Dict]: 剧集信息列表
        """
        try:
            if not quiet:
                print("正在获取播客剧集...")
            
            feed = feedparser.parse(feed_url)
            episodes = []
            
            for entry in feed.entries[:limit]:
                # 提取音频URL
                audio_url = None
                for link in entry.get('links', []):
                    if link.get('type', '').startswith('audio/'):
                        audio_url = link.get('href')
                        break
                
                # 备用方法获取音频URL
                if not audio_url and hasattr(entry, 'enclosures'):
                    for enclosure in entry.enclosures:
                        if enclosure.type.startswith('audio/'):
                            audio_url = enclosure.href
                            break
                
                # 格式化发布日期
                published_date = '未知日期'
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_date = datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d')
                elif hasattr(entry, 'published'):
                    published_date = entry.published
                
                # 获取时长（如有）
                duration = '未知时长'
                if hasattr(entry, 'itunes_duration'):
                    duration = entry.itunes_duration
                
                episode = {
                    'title': entry.get('title', '未知标题'),
                    'audio_url': audio_url,
                    'published_date': published_date,
                    'duration': duration,
                    'description': entry.get('summary', '无描述')[:200] + '...' if len(entry.get('summary', '')) > 200 else entry.get('summary', '无描述')
                }
                episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            if not quiet:
                print(f"获取剧集出错: {e}")
            return []
    
    def display_channels(self, channels: List[Dict]) -> int:
        """
        展示找到的频道并让用户选择
        
        Args:
            channels: 频道列表
        
        Returns:
            int: 用户选择的频道索引，-1为无效选择
        """
        if not channels:
            print("❌ 未找到匹配的播客频道")
            return -1
        
        print(f"\n共找到{len(channels)}个匹配的播客频道:")
        print("=" * 60)
        
        for i, channel in enumerate(channels, 1):
            print(f"{i}. {channel['name']}")
            print(f"   作者: {channel['artist']}")
            print(f"   类型: {channel['genre']}")
            print(f"   简介: {channel['description'][:100]}{'...' if len(channel['description']) > 100 else ''}")
            print("-" * 60)
        
        try:
            choice = input(f"\n请选择频道 (1-{len(channels)})，或回车退出: ").strip()
            if not choice:
                return -1
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(channels):
                return choice_num - 1
            else:
                print("❌ 选择无效")
                return -1
                
        except ValueError:
            print("❌ 请输入有效数字")
            return -1
    
    def display_episodes(self, episodes: List[Dict], channel_name: str):
        """
        展示剧集列表
        
        Args:
            episodes: 剧集列表
            channel_name: 频道名称
        """
        if not episodes:
            print("❌ 该频道没有找到剧集")
            return
        
        print(f"\n📻 {channel_name} - 最新{len(episodes)}期播客剧集:")
        print("=" * 80)
        
        for i, episode in enumerate(episodes, 1):
            print(f"{i:2d}. {episode['title']}")
            print(f"    📅 发布日期: {episode['published_date']}")
            print(f"    ⏱️  时长: {episode['duration']}")
            print(f"    📝 简介: {episode['description']}")
            if episode['audio_url']:
                print(f"    🎵 音频链接: {episode['audio_url']}")
            print("-" * 80)
    
    def parse_episode_selection(self, user_input: str, max_episodes: int) -> List[int]:
        """
        解析用户的剧集选择输入
        
        Args:
            user_input: 用户输入（如"1-10", "3", "1,3,5"）
            max_episodes: 剧集最大数量
        
        Returns:
            List[int]: 选中的剧集索引（0基）
        """
        selected = set()
        user_input = user_input.strip()
        
        # 逗号分割
        parts = [part.strip() for part in user_input.split(',')]
        
        for part in parts:
            if '-' in part:
                # 处理范围，如"1-10"
                try:
                    start, end = part.split('-', 1)
                    start_num = int(start.strip())
                    end_num = int(end.strip())
                    
                    # 保证范围有效
                    start_num = max(1, min(start_num, max_episodes))
                    end_num = max(1, min(end_num, max_episodes))
                    
                    if start_num > end_num:
                        start_num, end_num = end_num, start_num
                    
                    # 添加所有范围内数字（转为0基索引）
                    for i in range(start_num, end_num + 1):
                        selected.add(i - 1)
                        
                except ValueError:
                    print(f"❌ 范围格式无效: {part}")
                    continue
            else:
                # 处理单个数字
                try:
                    num = int(part)
                    if 1 <= num <= max_episodes:
                        selected.add(num - 1)  # 转为0基索引
                    else:
                        print(f"❌ 数字超出范围: {num} (有效范围: 1-{max_episodes})")
                except ValueError:
                    print(f"❌ 无效数字: {part}")
                    continue
        
        return sorted(list(selected))
    
    def sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除不安全字符
        
        Args:
            filename: 原始文件名
        
        Returns:
            str: 清理后的文件名
        """
        # 移除或替换不安全字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)  # 空格替换为下划线
        filename = filename.strip('._')  # 去除首尾点和下划线
        
        # 限制文件名长度
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename
    
    def ensure_filename_length(self, safe_channel: str, episode_num: int, safe_title: str, extension: str = ".mp3") -> str:
        """
        确保完整文件名不超过文件系统限制（255字符）
        
        Args:
            safe_channel: 清理后的频道名
            episode_num: 剧集编号
            safe_title: 清理后的剧集标题
            extension: 文件扩展名（默认：.mp3）
        
        Returns:
            str: 符合长度限制的最终文件名
        """
        # 计算固定部分：剧集编号、下划线和扩展名
        fixed_part = f"_{episode_num:02d}_"  # 例如 "_01_"
        fixed_length = len(fixed_part) + len(extension)  # 例如 4 + 4 = 8
        
        # 频道名和标题的最大可用长度
        max_content_length = 255 - fixed_length  # 例如 255 - 8 = 247
        
        # 如果频道名和标题都能放下，直接使用
        combined_length = len(safe_channel) + len(safe_title)
        if combined_length <= max_content_length:
            return f"{safe_channel}{fixed_part}{safe_title}{extension}"
        
        # 如果太长，分配可用空间
        # 优先保留标题，但确保频道名也有最小表示
        min_channel_length = 20  # 频道名最小字符数
        min_title_length = 30    # 标题最小字符数
        
        # 如果连最小值都放不下，更激进地截断
        if min_channel_length + min_title_length > max_content_length:
            # 平分可用空间
            half_space = max_content_length // 2
            truncated_channel = safe_channel[:half_space]
            truncated_title = safe_title[:max_content_length - len(truncated_channel)]
        else:
            # 尝试保留更多标题
            remaining_space = max_content_length - min_channel_length
            if len(safe_title) <= remaining_space:
                # 标题能放下，截断频道名
                truncated_title = safe_title
                truncated_channel = safe_channel[:max_content_length - len(safe_title)]
            else:
                # 两者都需要截断
                truncated_channel = safe_channel[:min_channel_length]
                truncated_title = safe_title[:max_content_length - min_channel_length]
        
        final_filename = f"{truncated_channel}{fixed_part}{truncated_title}{extension}"
        
        # 安全检查
        if len(final_filename) > 255:
            # 紧急截断
            emergency_title = safe_title[:255 - fixed_length - min_channel_length]
            emergency_channel = safe_channel[:min_channel_length]
            final_filename = f"{emergency_channel}{fixed_part}{emergency_title}{extension}"
        
        return final_filename
    
    def create_episode_folder(self, channel_name: str, episode_title: str, episode_num: int, published_date: str = None) -> Path:
        """
        创建剧集文件夹
        
        Args:
            channel_name: 频道名称
            episode_title: 剧集标题
            episode_num: 剧集编号
            published_date: 剧集发布日期 (格式: YYYY-MM-DD)
        
        Returns:
            Path: 剧集文件夹路径
        """
        # 清理频道名和剧集标题
        safe_channel = self.sanitize_filename(channel_name)
        safe_title = self.sanitize_filename(episode_title)
        
        # 限制文件夹名长度以确保路径不会过长
        max_channel_length = 50
        max_title_length = 100
        
        if len(safe_channel) > max_channel_length:
            safe_channel = safe_channel[:max_channel_length]
        
        if len(safe_title) > max_title_length:
            safe_title = safe_title[:max_title_length]
        
        # 创建频道文件夹（第一层）
        channel_dir = self.root_output_dir / safe_channel
        channel_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用发布日期创建日期文件夹（第二层）
        if published_date and published_date != '未知日期':
            # Apple Podcast已经格式化为YYYY-MM-DD，直接使用
            date_folder = published_date
        else:
            # 没有发布日期时使用今天的日期
            date_folder = datetime.now().strftime('%Y-%m-%d')
        
        date_dir = channel_dir / date_folder
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建剧集文件夹（第三层）- 不带剧集编号前缀
        episode_dir = date_dir / safe_title
        episode_dir.mkdir(parents=True, exist_ok=True)
        
        return episode_dir

    def download_episode(self, episode: Dict, episode_num: int, channel_name: str, quiet: bool = False) -> tuple[bool, Path]:
        """
        下载单个剧集
        
        Args:
            episode: 剧集信息
            episode_num: 剧集编号（1基）
            channel_name: 频道名称
            quiet: 是否静默处理
        
        Returns:
            tuple[bool, Path]: (下载是否成功, 剧集文件夹路径)
        """
        if not episode['audio_url']:
            if not quiet:
                print(f"❌ 剧集{episode_num}没有可用音频链接")
            return False, None
        
        try:
            # 创建剧集文件夹
            episode_dir = self.create_episode_folder(channel_name, episode['title'], episode_num, episode.get('published_date'))
            
            # 音频文件名
            filename = "audio.mp3"
            filepath = episode_dir / filename
            
            # 检查文件是否已存在
            if filepath.exists():
                if not quiet:
                    print(f"⚠️  文件已存在，跳过: {episode_dir.name}/{filename}")
                return True, episode_dir
            
            if not quiet:
                print(f"📥 正在下载: {episode['title']}")
            
            # 下载文件
            response = self.session.get(episode['audio_url'], stream=True)
            response.raise_for_status()
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 带进度条下载
            with open(filepath, 'wb') as f:
                if total_size > 0 and not quiet:
                    with tqdm(
                        total=total_size, 
                        unit='B', 
                        unit_scale=True, 
                        desc=f"第{episode_num}集"
                    ) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
                else:
                    # 没有文件大小信息时直接下载，或静默模式下直接下载
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            if not quiet:
                print(f"✅ 下载完成")
            return True, episode_dir
            
        except Exception as e:
            if not quiet:
                print(f"❌ 下载第{episode_num}集失败: {e}")
            # 下载失败时删除可能的不完整文件
            if 'filepath' in locals() and filepath.exists():
                filepath.unlink()
            return False, None
    
    def get_file_size_mb(self, filepath):
        """获取文件大小（MB）"""
        if not os.path.exists(filepath):
            return 0
        size_bytes = os.path.getsize(filepath)
        return size_bytes / (1024 * 1024)
    
    def compress_audio_file(self, input_file: Path, output_file: Path, quiet: bool = False) -> bool:
        """
        智能两级压缩音频文件至Groq API限制以下
        首选64k保证质量，如果仍>25MB则降至48k
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
        
        Returns:
            bool: 压缩是否成功
        """
        try:
            if quiet:
                print("🔧 正在压缩...")
            else:
                print(f"🔧 正在压缩音频文件: {input_file.name}")
                
                # 第一级压缩：64k (优先保证质量)
                print("📊 第一级压缩: 16KHz单声道, 64kbps MP3")
            
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
                '-ar', '16000',        # 降采样到16KHz
                '-ac', '1',            # 单声道
                '-b:a', '64k',         # 64kbps码率
                '-y',                  # 覆盖输出文件
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
            if not quiet:
                print(f"📊 64k压缩后大小: {compressed_size_mb:.1f}MB")
            
            if compressed_size_mb <= 25:
                # 64k压缩满足要求，使用64k结果
                temp_64k_file.rename(output_file)
                if not quiet:
                    print(f"✅ 64k压缩完成: {output_file.name} ({compressed_size_mb:.1f}MB)")
                return True
            else:
                # 64k压缩后仍>25MB，进行第二级48k压缩
                if not quiet:
                    print(f"⚠️  64k压缩后仍超25MB，进行第二级48k压缩...")
                    print("📊 第二级压缩: 16KHz单声道, 48kbps MP3")
                
                cmd_48k = [
                    'ffmpeg',
                    '-i', str(input_file),
                    '-ar', '16000',        # 降采样到16KHz
                    '-ac', '1',            # 单声道
                    '-b:a', '48k',         # 48kbps码率
                    '-y',                  # 覆盖输出文件
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
                if not quiet:
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
    
    def transcribe_with_groq(self, audio_file: Path, quiet: bool = False) -> dict:
        """
        使用Groq API转录音频文件
        
        Args:
            audio_file: 音频文件路径
        
        Returns:
            dict: 转录结果
        """
        try:
            if not quiet:
                print(f"🚀 Groq API转录: {audio_file.name}")
                print("🧠 使用模型: whisper-large-v3")
            
            start_time = time.time()
            
            # 打开音频文件并转录
            with open(audio_file, "rb") as file:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=file,
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    temperature=0.0
                )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # 处理响应
            text = transcription.text if hasattr(transcription, 'text') else transcription.get('text', '')
            language = getattr(transcription, 'language', 'en') if hasattr(transcription, 'language') else transcription.get('language', 'en')
            
            file_size_mb = self.get_file_size_mb(audio_file)
            speed_ratio = file_size_mb / processing_time * 60 if processing_time > 0 else 0
            
            if not quiet:
                print(f"✅ Groq转录完成! 用时: {processing_time:.1f}秒")
            
            return {
                'text': text,
                'language': language,
                'processing_time': processing_time,
                'speed_ratio': speed_ratio,
                'method': 'Groq API whisper-large-v3'
            }
            
        except Exception as e:
            # print(f"❌ Groq转录失败: {e}")
            return None
    
    def transcribe_with_mlx(self, audio_file: Path, quiet: bool = False) -> dict:
        """
        使用MLX Whisper转录音频文件
        
        Args:
            audio_file: 音频文件路径
        
        Returns:
            dict: 转录结果
        """
        try:
            if not quiet:
                print(f"🎯 MLX Whisper转录: {audio_file.name}")
                print("🧠 使用模型: mlx-community/whisper-medium")
            
            start_time = time.time()
            
            # 在静默模式下隐藏 MLX Whisper 的输出
            if quiet:
                import contextlib
                import io
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
    
    def transcribe_audio_smart(self, audio_file: Path, episode_title: str, channel_name: str, episode_dir: Path, auto_transcribe: bool = False) -> bool:
        """
        智能音频转录：根据文件大小选择最佳转录方式
        
        Args:
            audio_file: 音频文件路径
            episode_title: 剧集标题
            channel_name: 频道名称
            episode_dir: 剧集文件夹路径
        
        Returns:
            bool: 转录是否成功
        """
        if not TRANSCRIPTION_AVAILABLE:
            print("❌ 没有可用的转录服务")
            return False
        
        try:
            # 转录文件路径
            # 生成包含剧集标题的转录文件名
            safe_channel = self.sanitize_filename(channel_name)
            safe_title = self.sanitize_filename(episode_title)
            transcript_filename = self.ensure_transcript_filename_length(safe_channel, safe_title)
            transcript_filepath = episode_dir / transcript_filename
            
            # 检查转录文件是否已存在
            if transcript_filepath.exists():
                print(f"⚠️  转录文件已存在，跳过: {episode_dir.name}/{transcript_filename}")
                return True
            
            if not auto_transcribe:
                print(f"🎙️  开始转录: {episode_title}")
                
                # 检查文件大小
                file_size_mb = self.get_file_size_mb(audio_file)
                print(f"📊 音频文件大小: {file_size_mb:.1f}MB")
            else:
                file_size_mb = self.get_file_size_mb(audio_file)
            
            groq_limit = 25  # MB
            transcript_result = None
            compressed_file = None
            original_size = file_size_mb
            final_size = file_size_mb
            
            # 智能转录策略
            if file_size_mb <= groq_limit and GROQ_AVAILABLE:
                # 情况1: 文件<25MB, 直接用Groq, 失败则MLX兜底
                if not auto_transcribe:
                    print("✅ 文件大小在Groq限制内，使用极速转录")
                transcript_result = self.transcribe_with_groq(audio_file, quiet=auto_transcribe)
                
                # Groq失败则MLX兜底
                if not transcript_result and MLX_WHISPER_AVAILABLE:
                    if not auto_transcribe:
                        print("🔄 Groq失败，切换本地MLX Whisper...")
                    transcript_result = self.transcribe_with_mlx(audio_file, quiet=auto_transcribe)
            
            elif file_size_mb > groq_limit:
                # 情况2: 文件>25MB, 需压缩
                if not auto_transcribe:
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
                
                if self.compress_audio_file(audio_file, compressed_file, quiet=auto_transcribe):
                    compressed_size = self.get_file_size_mb(compressed_file)
                    final_size = compressed_size
                    if not auto_transcribe:
                        print(f"📊 压缩后大小: {compressed_size:.1f}MB")
                    
                    if compressed_size <= groq_limit and GROQ_AVAILABLE:
                        # 情况2a: 压缩后在Groq限制内, 失败则MLX兜底
                        if not auto_transcribe:
                            print("✅ 压缩后在Groq限制内，使用极速转录")
                        transcript_result = self.transcribe_with_groq(compressed_file, quiet=auto_transcribe)
                        
                        # Groq失败则MLX兜底
                        if not transcript_result and MLX_WHISPER_AVAILABLE:
                            if not auto_transcribe:
                                print("🔄 Groq失败，切换本地MLX Whisper...")
                            transcript_result = self.transcribe_with_mlx(compressed_file, quiet=auto_transcribe)
                    else:
                        # 情况2b: 压缩后仍超限, 用MLX
                        if not auto_transcribe:
                            print("⚠️  压缩后仍超出限制，使用MLX本地转录")
                        if MLX_WHISPER_AVAILABLE:
                            if auto_transcribe:
                                print("💻 本地转录...")
                            transcript_result = self.transcribe_with_mlx(compressed_file, quiet=auto_transcribe)
                        else:
                            if not auto_transcribe:
                                print("❌ MLX Whisper不可用，无法转录大文件")
                            return False
                else:
                    # 压缩失败，尝试MLX
                    print("❌ 压缩失败，尝试本地MLX转录")
                    if MLX_WHISPER_AVAILABLE:
                        transcript_result = self.transcribe_with_mlx(audio_file)
                    else:
                        print("❌ MLX Whisper不可用，转录失败")
                        return False
            
            else:
                # 情况3: Groq不可用，用MLX
                print("⚠️  Groq API不可用，使用本地MLX转录")
                if MLX_WHISPER_AVAILABLE:
                    transcript_result = self.transcribe_with_mlx(audio_file)
                else:
                    print("❌ MLX Whisper不可用，转录失败")
                    return False
            
            # 处理转录结果
            if not transcript_result:
                print("❌ 所有转录方式均失败")
                return False
            
            # 保存转录结果
            with open(transcript_filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {episode_title}\n\n")
                f.write(f"**频道:** {channel_name}\n\n")
                f.write("---\n\n")
                f.write(transcript_result['text'])
            
            if not auto_transcribe:
                print(f"✅ 转录完成: {episode_dir.name}/{transcript_filename}")
            
            # 清理文件
            try:
                # 删除原音频文件
                audio_file.unlink()
                if not auto_transcribe:
                    print(f"🗑️  已删除音频文件: {audio_file.name}")
                
                # 删除压缩文件（如有）
                if compressed_file and compressed_file.exists():
                    compressed_file.unlink()
                    if not auto_transcribe:
                        print(f"🗑️  已删除压缩文件: {compressed_file.name}")
                    
            except Exception as e:
                if not auto_transcribe:
                    print(f"⚠️  删除文件失败: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ 转录流程失败: {e}")
            # 清理可能的不完整文件
            if transcript_filepath.exists():
                transcript_filepath.unlink()
            return False
    
    def download_episodes(self, episodes: List[Dict], channel_name: str):
        """
        批量下载剧集
        
        Args:
            episodes: 剧集列表
            channel_name: 频道名称
        """
        if not episodes:
            print("❌ 没有可下载的剧集")
            return
        
        print(f"\n💾 下载选项:")
        print("格式说明:")
        print("  - 下载单集: 输入数字，如 '3'")
        print("  - 下载多集: 用逗号分隔，如 '1,3,5'")
        print("  - 下载范围: 用连字符，如 '1-10'")
        print("  - 组合使用: 如 '1,3-5,8'")
        
        user_input = input(f"\n请选择要下载的剧集 (1-{len(episodes)}) 或按回车跳过: ").strip()
        
        if not user_input:
            print("跳过下载")
            return
        
        # 解析用户选择
        selected_indices = self.parse_episode_selection(user_input, len(episodes))
        
        if not selected_indices:
            print("❌ 没有有效的剧集被选中")
            return
        
        # print(f"\n准备下载{len(selected_indices)}集播客...")  # 隐藏此消息
        
        # 下载结果统计
        success_count = 0
        total_count = len(selected_indices)
        downloaded_files = []  # (audio_file_path, episode_title, episode_dir)
        
        # 下载选中剧集
        for i, episode_index in enumerate(selected_indices, 1):
            episode = episodes[episode_index]
            episode_num = episode_index + 1  # 转回1基编号
            
            success, episode_dir = self.download_episode(episode, episode_num, channel_name)
            if success and episode_dir:
                success_count += 1
                # 构建已下载文件路径
                audio_file = episode_dir / "audio.mp3"
                downloaded_files.append((audio_file, episode['title'], episode_dir))
        
        # 隐藏下载汇总
        # print(f"\n📊 下载完成! 成功: {success_count}/{total_count}")
        # if success_count < total_count:
        #     print(f"⚠️  {total_count - success_count}个文件下载失败")
        
        # 询问是否转录
        if success_count > 0 and TRANSCRIPTION_AVAILABLE:
            self.transcribe_downloaded_files(downloaded_files, channel_name, auto_transcribe=True)
    
    def transcribe_downloaded_files(self, downloaded_files: List[tuple], channel_name: str, auto_transcribe: bool = False):
        """
        转录已下载文件
        
        Args:
            downloaded_files: [(文件路径, 标题, 剧集文件夹), ...]
            channel_name: 频道名称
            auto_transcribe: 是否自动转录，不询问用户
        """
        if not auto_transcribe:
            print(f"\n🎙️  转录选项:")
            transcribe_choice = input("是否要转录刚刚下载的音频文件? (y/n): ").strip().lower()
            if transcribe_choice not in ['y', 'yes', '是']:
                print("跳过转录")
                return
        
        # 转录文件
        success_count = 0
        total_count = len(downloaded_files)
        
        if auto_transcribe:
            print("\n⚡️ 极速转录...")
        else:
            print(f"\n🚀 开始智能转录{total_count}个文件...")
            if GROQ_AVAILABLE:
                print("💡 将自动选择最佳转录方式: Groq API（极速）或MLX Whisper（本地）")
            else:
                print("💡 使用MLX Whisper本地转录")
        
        successful_transcripts = []  # 存储成功转录的信息 (episode_title, channel_name, episode_dir)
        
        for i, (audio_file, episode_title, episode_dir) in enumerate(downloaded_files, 1):
            if not audio_file.exists():
                if not auto_transcribe:
                    print(f"❌ 文件不存在: {audio_file}")
                continue
            
            if not auto_transcribe:
                print(f"\n[{i}/{total_count}] ", end="")
            if self.transcribe_audio_smart(audio_file, episode_title, channel_name, episode_dir, auto_transcribe):
                success_count += 1
                successful_transcripts.append((episode_title, channel_name, episode_dir))
        
        if auto_transcribe:
            print("✅ 转录完成")
        else:
            print(f"\n📊 转录完成! 成功: {success_count}/{total_count}")
            if success_count > 0:
                print(f"📁 转录文件保存在各剧集文件夹内: {self.root_output_dir.absolute()}")
        
        # 自动生成摘要（不再询问用户）
        if success_count > 0 and self.gemini_client and successful_transcripts:
            # 默认使用中文摘要
            language_choice = 'ch'
            
            print("\n🧠 开始总结...")
            
            summary_success_count = 0
            
            for i, (episode_title, channel_name, episode_dir) in enumerate(successful_transcripts, 1):
                if not auto_transcribe:
                    print(f"\n[{i}/{len(successful_transcripts)}] 处理: {episode_title}")
                
                # 读取转录文件
                safe_channel = self.sanitize_filename(channel_name)
                safe_title = self.sanitize_filename(episode_title)
                transcript_filename = self.ensure_transcript_filename_length(safe_channel, safe_title)
                transcript_filepath = episode_dir / transcript_filename
                
                if not transcript_filepath.exists():
                    if not auto_transcribe:
                        print(f"❌ 转录文件不存在: {episode_dir.name}/{transcript_filename}")
                    continue
                
                try:
                    # 读取转录内容
                    with open(transcript_filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 提取实际转录文本（跳过元数据）
                    if "## 转录内容" in content:
                        transcript_text = content.split("## 转录内容")[1].strip()
                    elif "## Transcript Content" in content:
                        transcript_text = content.split("## Transcript Content")[1].strip()
                    elif "---" in content:
                        # 备用: ---后内容
                        parts = content.split("---", 1)
                        if len(parts) > 1:
                            transcript_text = parts[1].strip()
                        else:
                            transcript_text = content
                    else:
                        transcript_text = content
                    
                    if len(transcript_text.strip()) < 100:
                        if not auto_transcribe:
                            print("⚠️  转录内容过短，跳过摘要生成")
                        continue
                    
                    # 生成摘要
                    summary = self.generate_summary(transcript_text, episode_title)
                    if not summary:
                        if not auto_transcribe:
                            print("❌ 摘要生成失败")
                        continue
                    
                    # 翻译为中文
                    final_summary = summary
                    if language_choice == 'ch':
                        translated_summary = self.translate_to_chinese(summary)
                        if translated_summary:
                            final_summary = translated_summary
                            if not auto_transcribe:
                                print("✅ 摘要已翻译为中文")
                        else:
                            if not auto_transcribe:
                                print("⚠️  翻译失败，使用英文摘要")
                            language_choice = 'en'  # 回退英文
                    
                    # 保存摘要
                    summary_path = self.save_summary(final_summary, episode_title, channel_name, language_choice, episode_dir)
                    if summary_path:
                        if not auto_transcribe:
                            print(f"✅ 摘要已保存: {episode_dir.name}/summary.md")
                        summary_success_count += 1
                    else:
                        if not auto_transcribe:
                            print("❌ 摘要保存失败")
                        
                except Exception as e:
                    if not auto_transcribe:
                        print(f"❌ 摘要处理出错: {e}")
                    continue
            
            print("✅ 总结完成")
            
            # 无论自动还是手动模式，都提供可视化选项
            if summary_success_count > 0:
                self.ask_for_visualization(successful_transcripts, language_choice)
        
        elif not self.gemini_client and successful_transcripts and not auto_transcribe:
            print(f"\n⚠️  Gemini API不可用，无法生成摘要")
            print(f"💡 如需启用摘要，请在.env文件中设置GEMINI_API_KEY")
            
            # Ask about visualization for transcript only
            self.ask_for_visualization(successful_transcripts, 'ch')
    
    def ask_for_visualization(self, successful_transcripts: List[tuple], language: str):
        """
        询问用户是否要生成可视化故事
        
        Args:
            successful_transcripts: 成功转录的(episode_title, channel_name, episode_dir)元组列表
            language: 语言偏好 ('ch' 为中文)
        """
        if not successful_transcripts:
            return
        
        visualize_choice = input("\n🎨 可视化故事生成?(y/n): ").strip().lower()
        
        if visualize_choice not in ['y', 'yes', '是']:
            return
        
        # Ask whether to use transcript or summary
        print("📄 内容来源:")
        content_choice = input("基于转录文本还是摘要生成可视化? (t/s): ").strip().lower()
        
        if content_choice not in ['t', 's']:
            print("选择无效，跳过可视化生成。")
            return
        
        # Import visual module
        try:
            from .visual_ch import generate_visual_story
        except ImportError:
            print("❌ 未找到可视化模块。请确保visual_ch.py在podlens文件夹中。")
            return
        
        # Process each successful transcript/summary
        visual_success_count = 0
        
        print("\n🎨 添加色彩...")
        
        for i, (episode_title, channel_name, episode_dir) in enumerate(successful_transcripts, 1):
            # Build file paths
            safe_channel = self.sanitize_filename(channel_name)
            safe_title = self.sanitize_filename(episode_title)
            
            if content_choice == 't':
                # Use transcript
                source_filename = self.ensure_transcript_filename_length(safe_channel, safe_title)
                content_type = "转录文本"
            else:
                # Use summary
                source_filename = self.ensure_summary_filename_length(safe_channel, safe_title)
                content_type = "摘要"
            
            source_filepath = episode_dir / source_filename
            
            if not source_filepath.exists():
                print(f"❌ {content_type}文件未找到: {episode_dir.name}/{source_filename}")
                continue
            
            # Set output path for visual story
            visual_filename = self.ensure_visual_filename_length(safe_channel, safe_title)
            visual_output_path = episode_dir / visual_filename
            
            # Generate visual story
            if generate_visual_story(str(source_filepath), str(visual_output_path)):
                visual_success_count += 1
        
        print("✅ 可视化完成")

    def generate_summary(self, transcript: str, title: str) -> str:
        """
        使用Gemini API生成摘要
        
        Args:
            transcript: 转录文本
            title: 剧集标题
        
        Returns:
            str: 生成的摘要，失败返回None
        """
        if not self.gemini_client:
            print("❌ Gemini API不可用，无法生成摘要")
            return None
        
        try:
            # print("✨ 正在生成摘要...")  # 隐藏详细信息
            
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
            
            转录文本:
            {transcript}
            """
            
            response = self.gemini_client.GenerativeModel("gemini-2.5-flash-preview-05-20").generate_content(prompt)
            
            # 处理响应
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                print("❌ Gemini API响应格式异常")
                return None
                
        except Exception as e:
            print(f"❌ 摘要生成失败: {e}")
            return None
    
    def translate_to_chinese(self, text: str) -> str:
        """
        翻译文本为中文
        
        Args:
            text: 待翻译文本
        
        Returns:
            str: 中文翻译，失败返回None
        """
        if not self.gemini_client:
            print("❌ Gemini API不可用，无法翻译")
            return None
        
        try:
            # print("🔄 正在翻译为中文...")  # 隐藏详细信息
            
            prompt = f"Translate everything to Chinese accurately without missing anything:\n\n{text}"
            
            response = self.gemini_client.GenerativeModel("gemini-2.5-flash-preview-05-20").generate_content(prompt)
            
            # 处理响应
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                print("❌ Gemini API响应格式异常")
                return None
                
        except Exception as e:
            print(f"❌ 翻译失败: {e}")
            return None
    
    def save_summary(self, summary: str, title: str, channel_name: str, language: str = "en", episode_dir: Path = None) -> str:
        """
        保存摘要到文件
        
        Args:
            summary: 摘要内容
            title: 剧集标题
            channel_name: 频道名称
            language: 语言标识
            episode_dir: 剧集文件夹路径
        
        Returns:
            str: 保存的文件路径
        """
        try:
            # 构建摘要文件名
            if episode_dir:
                # 生成包含剧集标题的摘要文件名
                safe_channel = self.sanitize_filename(channel_name)
                safe_title = self.sanitize_filename(title)
                summary_filename = self.ensure_summary_filename_length(safe_channel, safe_title)
                summary_filepath = episode_dir / summary_filename
            else:
                # 兼容老版本调用
                safe_channel = self.sanitize_filename(channel_name)
                safe_title = self.sanitize_filename(title)
                summary_filename = self.ensure_summary_filename_length(safe_channel, safe_title)
                summary_filepath = self.root_output_dir / summary_filename
            
            with open(summary_filepath, 'w', encoding='utf-8') as f:
                f.write(f"# 摘要: {title}\n\n" if language == "ch" else f"# Summary: {title}\n\n")
                f.write(f"**频道:** {channel_name}\n\n" if language == "ch" else f"**Channel:** {channel_name}\n\n")
                f.write(f"**摘要生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" if language == "ch" else f"**Summary Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**语言:** {'中文' if language == 'ch' else 'English'}\n\n")
                f.write("---\n\n")
                f.write("## 摘要内容\n\n" if language == "ch" else "## Summary Content\n\n")
                f.write(summary)
            
            return str(summary_filepath)
            
        except Exception as e:
            print(f"❌ 摘要保存失败: {e}")
            return None

    def ensure_output_filename_length(self, prefix: str, safe_channel: str, safe_title: str, extension: str = ".md") -> str:
        """
        确保输出文件名（转录/摘要）不超过文件系统限制（255字符）
        
        Args:
            prefix: 文件前缀（如"Transcript_", "Summary_"）
            safe_channel: 清理后的频道名（YouTube可能为空）
            safe_title: 清理后的标题
            extension: 文件扩展名（默认：.md）
        
        Returns:
            str: 符合长度限制的最终文件名
        """
        # 计算固定部分长度：前缀 + 扩展名
        fixed_length = len(prefix) + len(extension)
        
        # 最大可用内容长度
        max_content_length = 255 - fixed_length
        
        # 如果没有频道名（YouTube格式）
        if not safe_channel:
            if len(safe_title) <= max_content_length:
                return f"{prefix}{safe_title}{extension}"
            else:
                truncated_title = safe_title[:max_content_length]
                return f"{prefix}{truncated_title}{extension}"
        
        # Apple Podcast格式：prefix + channel + "_" + title + extension
        separator = "_"
        combined_content = f"{safe_channel}{separator}{safe_title}"
        
        if len(combined_content) <= max_content_length:
            return f"{prefix}{combined_content}{extension}"
        
        # 需要截断：优先保留标题，但确保频道名有最小表示
        min_channel_length = 15
        min_title_length = 20
        
        if min_channel_length + len(separator) + min_title_length > max_content_length:
            # 极端情况：分割可用空间
            available_space = max_content_length - len(separator)
            half_space = available_space // 2
            truncated_channel = safe_channel[:half_space]
            truncated_title = safe_title[:available_space - len(truncated_channel)]
        else:
            # 正常情况：优先保留标题
            remaining_space = max_content_length - min_channel_length - len(separator)
            if len(safe_title) <= remaining_space:
                truncated_title = safe_title
                truncated_channel = safe_channel[:max_content_length - len(separator) - len(safe_title)]
            else:
                truncated_channel = safe_channel[:min_channel_length]
                truncated_title = safe_title[:max_content_length - len(separator) - min_channel_length]
        
        return f"{prefix}{truncated_channel}{separator}{truncated_title}{extension}"
    
    def ensure_transcript_filename_length(self, safe_channel: str, safe_title: str) -> str:
        """确保转录文件名长度"""
        return self.ensure_output_filename_length("Transcript_", safe_channel, safe_title)
    
    def ensure_summary_filename_length(self, safe_channel: str, safe_title: str) -> str:
        """确保摘要文件名长度"""
        return self.ensure_output_filename_length("Summary_", safe_channel, safe_title)
    
    def ensure_visual_filename_length(self, safe_channel: str, safe_title: str) -> str:
        """确保可视化文件名长度"""
        return self.ensure_output_filename_length("Visual_", safe_channel, safe_title, ".html")

    def auto_process_latest_episode(self, podcast_name: str, progress_tracker=None) -> tuple[bool, str]:
        """
        自动化处理播客最新剧集 - 无用户交互
        
        Args:
            podcast_name: 播客名称
            progress_tracker: 进度跟踪器（用于重复检查）
            
        Returns:
            tuple[bool, str]: (处理是否成功, episode标题)
        """
        try:
            # 搜索频道（静默）
            channels = self.search_podcast_channel(podcast_name, quiet=True)
            if not channels:
                return False, ""
            
            selected_channel = channels[0]  # 自动选择第一个匹配频道
            if not selected_channel['feed_url']:
                return False, ""
            
            # 获取最新剧集（静默）
            episodes = self.get_recent_episodes(selected_channel['feed_url'], 5, quiet=True)
            if not episodes:
                return False, ""
            
            # 循环处理所有episodes，从最新开始
            processed_count = 0
            last_episode_title = ""
            
            for i, episode in enumerate(episodes):
                episode_title = episode['title']
                last_episode_title = episode_title
                
                # 检查是否已处理过
                if progress_tracker and progress_tracker.is_episode_processed(podcast_name, episode_title):
                    # print(f"⏭️  {podcast_name} 剧集已处理过，跳过: {episode_title[:50]}...")
                    continue
                    
                print(f"📥 处理新剧集: {episode_title[:50]}...")
                
                # 下载处理（静默下载过程）
                success, episode_dir = self.download_episode(episode, i+1, selected_channel['name'], quiet=True)
                if not success or not episode_dir:
                    continue
                
                # 自动转录
                audio_filepath = episode_dir / "audio.mp3"
                if audio_filepath.exists():
                    transcribe_success = self.transcribe_audio_smart(
                        audio_filepath, episode_title, 
                        selected_channel['name'], episode_dir, auto_transcribe=True
                    )
                    if transcribe_success:
                        # 自动总结 - 模拟transcribe_downloaded_files的处理逻辑
                        if self.gemini_client:
                            # 使用与原始代码相同的summary生成逻辑
                            self.auto_generate_summary_for_episode(
                                episode_title, selected_channel['name'], episode_dir
                            )
                        
                        # 标记为已处理
                        if progress_tracker:
                            progress_tracker.mark_episode_processed(podcast_name, episode_title)
                        processed_count += 1
            
            return processed_count > 0, last_episode_title
            
        except Exception as e:
            return False, ""
    
    def auto_generate_summary_for_episode(self, episode_title: str, channel_name: str, episode_dir: Path) -> bool:
        """
        为单个剧集自动生成总结（模拟transcribe_downloaded_files的逻辑）
        
        Args:
            episode_title: 剧集标题
            channel_name: 频道名称
            episode_dir: 剧集目录
            
        Returns:
            bool: 总结是否成功
        """
        try:
            # 读取转录文件
            safe_channel = self.sanitize_filename(channel_name)
            safe_title = self.sanitize_filename(episode_title)
            transcript_filename = self.ensure_transcript_filename_length(safe_channel, safe_title)
            transcript_filepath = episode_dir / transcript_filename
            
            if not transcript_filepath.exists():
                return False
            
            # 读取转录内容
            with open(transcript_filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取实际转录文本（跳过元数据）- 与原始代码完全相同的逻辑
            if "## 转录内容" in content:
                transcript_text = content.split("## 转录内容")[1].strip()
            elif "## Transcript Content" in content:
                transcript_text = content.split("## Transcript Content")[1].strip()
            elif "---" in content:
                # 备用: ---后内容
                parts = content.split("---", 1)
                if len(parts) > 1:
                    transcript_text = parts[1].strip()
                else:
                    transcript_text = content
            else:
                transcript_text = content
            
            if len(transcript_text.strip()) < 100:
                return False
            
            # 生成摘要
            summary = self.generate_summary(transcript_text, episode_title)
            if not summary:
                return False
            
            # 翻译为中文（中文版默认行为）
            language_choice = 'ch'
            final_summary = summary
            translated_summary = self.translate_to_chinese(summary)
            if translated_summary:
                final_summary = translated_summary
            else:
                language_choice = 'en'  # 回退英文
            
            # 保存摘要
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
        """在YouTube上搜索播客剧集，使用频道视频页面"""
        return self.searcher.search_youtube_podcast(podcast_name, num_episodes)
    
    def auto_process_channel_latest_video(self, channel_name: str, progress_tracker=None) -> tuple[bool, str]:
        """
        自动化处理频道最新视频 - 无用户交互
        
        Args:
            channel_name: 频道名称（不含@符号）
            progress_tracker: 进度跟踪器（用于重复检查）
            
        Returns:
            tuple[bool, str]: (处理是否成功, 视频标题)
        """
        try:
            # 搜索频道最新视频
            episodes = self.searcher.search_youtube_podcast(channel_name, num_episodes=10)
            if not episodes:
                return False, ""
            
            # 循环处理所有videos，从最新开始
            processed_count = 0
            last_video_title = ""
            
            for episode in episodes:
                video_title = episode.get('title', 'Unknown')
                last_video_title = video_title
                
                # 检查是否已处理过
                if progress_tracker and progress_tracker.is_video_processed(channel_name, video_title):
                    # print(f"⏭️  @{channel_name} 视频已处理过，跳过: {video_title[:50]}...")
                    continue
                    
                video_url = episode.get('url', '')
                if not video_url:
                    continue
                
                # 提取视频ID
                import re
                video_id_match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', video_url)
                if not video_id_match:
                    continue
                
                video_id = video_id_match.group(1)
                
                # 获取视频信息
                video_info = self.searcher.get_video_info(video_id)
                title = episode.get('title', video_info.get('title', 'Unknown'))
                channel_name_from_video = video_info.get('channel_name', channel_name)
                published_date = episode.get('published_date', 'Recent')
                
                print(f"📥 处理新视频: {title[:50]}...")
                
                # 创建episode目录
                episode_dir = self.extractor.create_episode_folder(
                    channel_name_from_video, 
                    title, 
                    published_date
                )
                
                # 尝试提取转录
                transcript = self.extractor.extract_youtube_transcript(
                    video_id, 
                    video_url, 
                    title, 
                    episode_dir=episode_dir
                )
                
                if transcript:
                    # 保存转录
                    transcript_filename = self.extractor.save_transcript(
                        transcript, 
                        title, 
                        channel_name_from_video, 
                        published_date, 
                        episode_dir
                    )
                    
                    # 生成总结
                    if self.summarizer.gemini_client:
                        summary = self.summarizer.generate_summary(transcript, title)
                        if summary:
                            # 翻译总结为中文（自动化中文版）
                            chinese_summary = self.summarizer.translate_to_chinese(summary)
                            final_summary = chinese_summary if chinese_summary else summary
                            
                            self.summarizer.save_summary(
                                final_summary, 
                                title, 
                                episode_dir, 
                                channel_name_from_video, 
                                episode_dir
                            )
                    
                    # 标记为已处理
                    if progress_tracker:
                        progress_tracker.mark_video_processed(channel_name, video_title)
                    processed_count += 1
            
            return processed_count > 0, last_video_title
            
        except Exception as e:
            print(f"❌ 自动处理YouTube视频失败: {e}")
            return False, ""

    def run(self):
        """Main application loop for YouTube"""
        
        while True:
            # 修改询问信息类型的提示
            print("\n请选择youtube资源类型:")
            print("- name: 频道名称(@name)")
            print("- link: 视频链接")
            print("- script: 直接提供文本内容")
            print("\n示例：")
            print("  name: lex fridman, or lexfridman (频道的@name)")
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
                
                # 自动设置为获取转录文本和摘要
                want_transcripts = True
                want_summaries = True
            
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
                    
                    # Get episode selection
                    episode_selection = input(f"\n您对哪些节目感兴趣？(1-{len(episodes)}，如 '1,3,5' 或 '1-3' 或 'all'): ").strip()
                    
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
                            print("节目选择无效，请重试。")
                            continue
                    
                    if not selected_episodes:
                        print("未选择有效的节目。")
                        continue
                    
                    print(f"\n✅ 已选择 {len(selected_episodes)} 期节目")
                
                # 自动设置为获取转录文本和摘要
                want_transcripts = True
                want_summaries = True
            
            # 中文版默认使用中文输出和翻译
            want_chinese = True
            
            # 处理每个节目
            for episode in selected_episodes:
                print(f"\n🎥 正在处理: {episode['title']}")
                print()  # 空行
                
                transcript_content = None
                episode_dir = None
                
                if episode['platform'] == 'script':
                    # Use the script content directly
                    transcript_content = transcript
                    print("⚡️ 极速转录...")
                    print("✅ 转录完成")
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
                        
                        print("⚡️ 极速转录...")
                        transcript_content = self.extractor.extract_youtube_transcript(
                            video_id, 
                            episode.get('url'), 
                            episode['title'],
                            episode_dir
                        )
                        if transcript_content:
                            print("✅ 转录完成")
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
                        print("✅ 转录完成")
                        print()  # 空行
                
                if not transcript_content:
                    print("❌ 无法提取该节目的转录文本")
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
                        print("🧠 开始总结...")
                        summary = self.summarizer.generate_summary(transcript_content, episode['title'])
                        if summary:
                            # Translate summary to Chinese if requested
                            final_summary = summary
                            if want_chinese:
                                translated_summary = self.summarizer.translate_to_chinese(summary)
                                if translated_summary:
                                    final_summary = translated_summary
                                else:
                                    print("⚠️  翻译失败，使用原始摘要")
                            
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
                            print("✅ 总结完成")
                            print()  # 空行
                        else:
                            print("❌ 无法生成摘要")
                    else:
                        print("⚠️  跳过摘要 - 无有效转录内容")
            
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
        
        print(f"\n🎨 可视化故事生成?(y/n):")
        visualize_choice = input().strip().lower()
        
        if visualize_choice not in ['y', 'yes', '是']:
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
            print(f"❌ 未找到可视化模块。请确保{visual_module}在podlens文件夹中。")
            return
        
        # Process each episode
        visual_success_count = 0
        
        print("\n🎨 添加色彩...")
        
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
                    content_type = "转录文本"
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
                    content_type = "摘要"
                
                source_filepath = episode_dir / source_filename
            else:
                # For other platforms, use the old logic
                safe_title = re.sub(r'[^\w\s-]', '', title).strip()
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                
                if content_choice == 't':
                    source_filename = self.extractor.ensure_transcript_filename_length(safe_title)
                    content_type = "转录文本"
                else:
                    source_filename = self.extractor.ensure_summary_filename_length(safe_title)
                    content_type = "摘要"
                
                source_filepath = self.extractor.output_dir / source_filename
            
            if not source_filepath.exists():
                continue
            
            # Generate visual story
            if generate_visual_story(str(source_filepath)):
                visual_success_count += 1
        
        if visual_success_count > 0:
            print("✅ 可视化完成")

