#!/usr/bin/env python3
"""
PodLens Automation Interface - 全流程自动化机器接口
Provides programmatic interface for automated podcast processing without user interaction
"""

import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv

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

# Import language-specific modules
from .apple_podcast_ch import ApplePodcastExplorer as ApplePodcastExplorer_CH
from .apple_podcast_en import ApplePodcastExplorer as ApplePodcastExplorer_EN
from .youtube_ch import YouTubeSearcher as YouTubeSearcher_CH, TranscriptExtractor as TranscriptExtractor_CH, SummaryGenerator as SummaryGenerator_CH
from .youtube_en import YouTubeSearcher as YouTubeSearcher_EN, TranscriptExtractor as TranscriptExtractor_EN, SummaryGenerator as SummaryGenerator_EN


class PodlensAutomation:
    """
    全流程自动化播客处理引擎
    Automated podcast processing engine for machine usage
    """
    
    def __init__(self, language: str = "ch"):
        """
        初始化自动化引擎
        
        Args:
            language: 语言偏好 ('ch' 为中文, 'en' 为英文)
        """
        self.language = language
        
        # Initialize platform-specific components based on language
        if language == "ch":
            self.apple_explorer = ApplePodcastExplorer_CH()
            self.youtube_searcher = YouTubeSearcher_CH()
            self.youtube_extractor = TranscriptExtractor_CH()
            self.youtube_summarizer = SummaryGenerator_CH()
        else:
            self.apple_explorer = ApplePodcastExplorer_EN()
            self.youtube_searcher = YouTubeSearcher_EN()
            self.youtube_extractor = TranscriptExtractor_EN()
            self.youtube_summarizer = SummaryGenerator_EN()
        
        # Create output directory
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
    
    def process_apple_podcast(
        self,
        podcast_name: str,
        num_episodes: int = 1,
        episode_indices: Optional[List[int]] = None,
        enable_transcription: bool = True,
        enable_summary: bool = True,
        summary_language: str = "auto",
        enable_visualization: bool = False,
        visualization_source: str = "summary"  # "transcript" or "summary"
    ) -> Dict:
        """
        自动化处理 Apple Podcast
        
        Args:
            podcast_name: 播客频道名称
            num_episodes: 获取的剧集数量
            episode_indices: 要处理的剧集索引列表（从0开始），None 表示处理最新的剧集
            enable_transcription: 是否启用转录
            enable_summary: 是否启用摘要生成
            summary_language: 摘要语言 ('auto', 'en', 'ch')
            enable_visualization: 是否启用可视化故事生成
            visualization_source: 可视化内容来源
            
        Returns:
            Dict: 处理结果统计
        """
        result = {
            "platform": "Apple Podcast",
            "podcast_name": podcast_name,
            "channels_found": 0,
            "episodes_processed": 0,
            "downloads_success": 0,
            "transcripts_success": 0,
            "summaries_success": 0,
            "visualizations_success": 0,
            "errors": [],
            "output_files": []
        }
        
        try:
            print(f"🎧 开始自动化处理 Apple Podcast: {podcast_name}")
            
            # 1. 搜索播客频道
            print(f"🔍 搜索播客频道...")
            channels = self.apple_explorer.search_podcast_channel(podcast_name)
            result["channels_found"] = len(channels)
            
            if not channels:
                error_msg = f"未找到匹配的播客频道: {podcast_name}"
                result["errors"].append(error_msg)
                print(f"❌ {error_msg}")
                return result
            
            # 自动选择第一个匹配的频道
            selected_channel = channels[0]
            print(f"✅ 自动选择频道: {selected_channel['name']}")
            
            if not selected_channel['feed_url']:
                error_msg = f"频道没有可用的 RSS 订阅链接"
                result["errors"].append(error_msg)
                print(f"❌ {error_msg}")
                return result
            
            # 2. 获取剧集列表
            print(f"📻 获取最新 {num_episodes} 期剧集...")
            episodes = self.apple_explorer.get_recent_episodes(selected_channel['feed_url'], num_episodes)
            
            if not episodes:
                error_msg = "未找到可用剧集"
                result["errors"].append(error_msg)
                print(f"❌ {error_msg}")
                return result
            
            # 确定要处理的剧集
            if episode_indices is None:
                # 默认处理第一集（最新）
                episode_indices = [0]
            
            # 验证索引范围
            valid_indices = [i for i in episode_indices if 0 <= i < len(episodes)]
            if not valid_indices:
                error_msg = f"无效的剧集索引: {episode_indices}"
                result["errors"].append(error_msg)
                print(f"❌ {error_msg}")
                return result
            
            result["episodes_processed"] = len(valid_indices)
            
            # 3. 下载和处理剧集
            downloaded_files = []
            
            for i, episode_index in enumerate(valid_indices):
                episode = episodes[episode_index]
                episode_num = episode_index + 1
                
                print(f"\n[{i+1}/{len(valid_indices)}] 处理剧集: {episode['title']}")
                
                # 下载剧集
                if self.apple_explorer.download_episode(episode, episode_num, selected_channel['name']):
                    result["downloads_success"] += 1
                    
                    # 构建文件路径
                    safe_channel = self.apple_explorer.sanitize_filename(selected_channel['name'])
                    safe_title = self.apple_explorer.sanitize_filename(episode['title'])
                    filename = self.apple_explorer.ensure_filename_length(safe_channel, episode_num, safe_title)
                    audio_filepath = self.apple_explorer.media_dir / filename
                    
                    downloaded_files.append((audio_filepath, episode['title']))
                else:
                    result["errors"].append(f"下载失败: {episode['title']}")
            
            # 4. 转录处理
            successful_transcripts = []
            if enable_transcription and downloaded_files:
                print(f"\n🎙️ 开始转录 {len(downloaded_files)} 个音频文件...")
                
                for audio_file, episode_title in downloaded_files:
                    if audio_file.exists():
                        if self.apple_explorer.transcribe_audio_smart(audio_file, episode_title, selected_channel['name']):
                            result["transcripts_success"] += 1
                            successful_transcripts.append((episode_title, selected_channel['name']))
                            
                            # 添加转录文件到输出列表
                            safe_channel = self.apple_explorer.sanitize_filename(selected_channel['name'])
                            safe_title = self.apple_explorer.sanitize_filename(episode_title)
                            transcript_filename = self.apple_explorer.ensure_transcript_filename_length(safe_channel, safe_title)
                            transcript_path = self.apple_explorer.transcript_dir / transcript_filename
                            result["output_files"].append(str(transcript_path))
                        else:
                            result["errors"].append(f"转录失败: {episode_title}")
            
            # 5. 摘要生成
            if enable_summary and successful_transcripts and self.apple_explorer.gemini_client:
                print(f"\n✨ 开始生成摘要...")
                
                # 确定摘要语言
                if summary_language == "auto":
                    summary_lang = "ch" if self.language == "ch" else "en"
                else:
                    summary_lang = summary_language
                
                for episode_title, channel_name in successful_transcripts:
                    print(f"📄 生成摘要: {episode_title}")
                    
                    # 读取转录文件
                    safe_channel = self.apple_explorer.sanitize_filename(channel_name)
                    safe_title = self.apple_explorer.sanitize_filename(episode_title)
                    transcript_filename = self.apple_explorer.ensure_transcript_filename_length(safe_channel, safe_title)
                    transcript_filepath = self.apple_explorer.transcript_dir / transcript_filename
                    
                    if transcript_filepath.exists():
                        try:
                            with open(transcript_filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # 提取转录文本
                            transcript_text = self._extract_transcript_content(content)
                            
                            if len(transcript_text.strip()) >= 100:
                                # 生成摘要
                                summary = self.apple_explorer.generate_summary(transcript_text, episode_title)
                                
                                if summary:
                                    # 处理翻译
                                    final_summary = summary
                                    if summary_lang == 'ch' and self.language == 'en':
                                        translated = self.apple_explorer.translate_to_chinese(summary)
                                        if translated:
                                            final_summary = translated
                                    
                                    # 保存摘要
                                    summary_path = self.apple_explorer.save_summary(
                                        final_summary, episode_title, channel_name, summary_lang
                                    )
                                    if summary_path:
                                        result["summaries_success"] += 1
                                        result["output_files"].append(summary_path)
                                    else:
                                        result["errors"].append(f"摘要保存失败: {episode_title}")
                                else:
                                    result["errors"].append(f"摘要生成失败: {episode_title}")
                            else:
                                result["errors"].append(f"转录内容过短: {episode_title}")
                                
                        except Exception as e:
                            result["errors"].append(f"摘要处理错误 {episode_title}: {str(e)}")
            
            # 6. 可视化故事生成
            if enable_visualization and successful_transcripts:
                print(f"\n🎨 开始生成可视化故事...")
                
                # 导入可视化模块
                try:
                    if self.language == "ch":
                        from .visual_ch import generate_visual_story
                    else:
                        from .visual_en import generate_visual_story
                    
                    for episode_title, channel_name in successful_transcripts:
                        print(f"🖼️ 生成可视化: {episode_title}")
                        
                        # 确定源文件
                        safe_channel = self.apple_explorer.sanitize_filename(channel_name)
                        safe_title = self.apple_explorer.sanitize_filename(episode_title)
                        
                        if visualization_source == "summary" and enable_summary:
                            source_filename = self.apple_explorer.ensure_summary_filename_length(safe_channel, safe_title)
                        else:
                            source_filename = self.apple_explorer.ensure_transcript_filename_length(safe_channel, safe_title)
                        
                        source_filepath = self.apple_explorer.transcript_dir / source_filename
                        
                        if source_filepath.exists():
                            if generate_visual_story(str(source_filepath)):
                                result["visualizations_success"] += 1
                                
                                # 构建可视化文件路径
                                visual_filename = f"Visual_{safe_title}.html"
                                if len(visual_filename) > 255:
                                    visual_filename = f"Visual_{safe_title[:240]}.html"
                                visual_path = self.apple_explorer.transcript_dir / visual_filename
                                result["output_files"].append(str(visual_path))
                            else:
                                result["errors"].append(f"可视化生成失败: {episode_title}")
                        else:
                            result["errors"].append(f"可视化源文件未找到: {episode_title}")
                
                except ImportError:
                    result["errors"].append("可视化模块未找到")
            
            print(f"\n📊 处理完成!")
            print(f"✅ 成功下载: {result['downloads_success']}")
            print(f"✅ 成功转录: {result['transcripts_success']}")
            print(f"✅ 成功摘要: {result['summaries_success']}")
            print(f"✅ 成功可视化: {result['visualizations_success']}")
            
            if result["errors"]:
                print(f"⚠️ 错误数量: {len(result['errors'])}")
            
            return result
            
        except Exception as e:
            error_msg = f"处理过程中发生异常: {str(e)}"
            result["errors"].append(error_msg)
            print(f"❌ {error_msg}")
            return result
    
    def process_youtube(
        self,
        search_query: str,
        num_videos: int = 1,
        video_indices: Optional[List[int]] = None,
        enable_transcription: bool = True,
        enable_summary: bool = True,
        summary_language: str = "auto",
        enable_visualization: bool = False,
        visualization_source: str = "summary"
    ) -> Dict:
        """
        自动化处理 YouTube 视频
        
        Args:
            search_query: YouTube 搜索关键词
            num_videos: 搜索结果数量
            video_indices: 要处理的视频索引列表（从0开始），None 表示处理第一个视频
            enable_transcription: 是否启用转录
            enable_summary: 是否启用摘要生成
            summary_language: 摘要语言 ('auto', 'en', 'ch')
            enable_visualization: 是否启用可视化故事生成
            visualization_source: 可视化内容来源
            
        Returns:
            Dict: 处理结果统计
        """
        result = {
            "platform": "YouTube",
            "search_query": search_query,
            "videos_found": 0,
            "videos_processed": 0,
            "transcripts_success": 0,
            "summaries_success": 0,
            "visualizations_success": 0,
            "errors": [],
            "output_files": []
        }
        
        try:
            print(f"🎥 开始自动化处理 YouTube: {search_query}")
            
            # 1. 搜索视频
            print(f"🔍 搜索 YouTube 视频...")
            videos = self.youtube_searcher.search_youtube_podcast(search_query, num_videos)
            result["videos_found"] = len(videos)
            
            if not videos:
                error_msg = f"未找到匹配的视频: {search_query}"
                result["errors"].append(error_msg)
                print(f"❌ {error_msg}")
                return result
            
            # 确定要处理的视频
            if video_indices is None:
                video_indices = [0]  # 默认处理第一个视频
            
            # 验证索引范围
            valid_indices = [i for i in video_indices if 0 <= i < len(videos)]
            if not valid_indices:
                error_msg = f"无效的视频索引: {video_indices}"
                result["errors"].append(error_msg)
                print(f"❌ {error_msg}")
                return result
            
            result["videos_processed"] = len(valid_indices)
            
            # 2. 处理视频
            successful_transcripts = []
            
            for i, video_index in enumerate(valid_indices):
                video = videos[video_index]
                video_id = video['video_id']
                video_url = video['url']
                title = video['title']
                
                print(f"\n[{i+1}/{len(valid_indices)}] 处理视频: {title}")
                
                # 尝试提取转录
                if enable_transcription:
                    transcript_path = self.youtube_extractor.extract_youtube_transcript(
                        video_id, video_url, title
                    )
                    
                    if transcript_path:
                        result["transcripts_success"] += 1
                        result["output_files"].append(transcript_path)
                        successful_transcripts.append({"title": title, "transcript_path": transcript_path})
                        print(f"✅ 转录成功: {title}")
                    else:
                        result["errors"].append(f"转录失败: {title}")
                        print(f"❌ 转录失败: {title}")
            
            # 3. 生成摘要
            if enable_summary and successful_transcripts:
                print(f"\n✨ 开始生成摘要...")
                
                # 确定摘要语言
                if summary_language == "auto":
                    summary_lang = "ch" if self.language == "ch" else "en"
                else:
                    summary_lang = summary_language
                
                for item in successful_transcripts:
                    title = item["title"]
                    transcript_path = item["transcript_path"]
                    
                    print(f"📄 生成摘要: {title}")
                    
                    try:
                        # 读取转录内容
                        with open(transcript_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        transcript_text = self._extract_transcript_content(content)
                        
                        if len(transcript_text.strip()) >= 100:
                            # 生成摘要
                            summary = self.youtube_summarizer.generate_summary(transcript_text, title)
                            
                            if summary:
                                # 处理翻译
                                final_summary = summary
                                if summary_lang == 'ch':
                                    translated = self.youtube_summarizer.translate_to_chinese(summary)
                                    if translated:
                                        final_summary = translated
                                
                                # 保存摘要
                                summary_path = self.youtube_summarizer.save_summary(
                                    final_summary, title, self.output_dir
                                )
                                if summary_path:
                                    result["summaries_success"] += 1
                                    result["output_files"].append(summary_path)
                                    # 添加摘要路径到转录项目中，用于可视化
                                    item["summary_path"] = summary_path
                                else:
                                    result["errors"].append(f"摘要保存失败: {title}")
                            else:
                                result["errors"].append(f"摘要生成失败: {title}")
                        else:
                            result["errors"].append(f"转录内容过短: {title}")
                            
                    except Exception as e:
                        result["errors"].append(f"摘要处理错误 {title}: {str(e)}")
            
            # 4. 可视化故事生成
            if enable_visualization and successful_transcripts:
                print(f"\n🎨 开始生成可视化故事...")
                
                try:
                    if self.language == "ch":
                        from .visual_ch import generate_visual_story
                    else:
                        from .visual_en import generate_visual_story
                    
                    for item in successful_transcripts:
                        title = item["title"]
                        
                        # 确定源文件
                        if visualization_source == "summary" and "summary_path" in item:
                            source_path = item["summary_path"]
                        else:
                            source_path = item["transcript_path"]
                        
                        print(f"🖼️ 生成可视化: {title}")
                        
                        if os.path.exists(source_path):
                            if generate_visual_story(source_path):
                                result["visualizations_success"] += 1
                                
                                # 构建可视化文件路径
                                safe_title = self.youtube_summarizer.sanitize_filename(title)
                                visual_filename = f"Visual_{safe_title}.html"
                                if len(visual_filename) > 255:
                                    visual_filename = f"Visual_{safe_title[:240]}.html"
                                visual_path = self.output_dir / visual_filename
                                result["output_files"].append(str(visual_path))
                            else:
                                result["errors"].append(f"可视化生成失败: {title}")
                        else:
                            result["errors"].append(f"可视化源文件未找到: {title}")
                
                except ImportError:
                    result["errors"].append("可视化模块未找到")
            
            print(f"\n📊 处理完成!")
            print(f"✅ 成功转录: {result['transcripts_success']}")
            print(f"✅ 成功摘要: {result['summaries_success']}")
            print(f"✅ 成功可视化: {result['visualizations_success']}")
            
            if result["errors"]:
                print(f"⚠️ 错误数量: {len(result['errors'])}")
            
            return result
            
        except Exception as e:
            error_msg = f"处理过程中发生异常: {str(e)}"
            result["errors"].append(error_msg)
            print(f"❌ {error_msg}")
            return result
    
    def _extract_transcript_content(self, content: str) -> str:
        """
        从文件内容中提取转录文本
        
        Args:
            content: 文件内容
            
        Returns:
            str: 提取的转录文本
        """
        # 尝试多种格式的内容提取
        if "## 转录内容" in content:
            return content.split("## 转录内容")[1].strip()
        elif "## Transcript Content" in content:
            return content.split("## Transcript Content")[1].strip()
        elif "---" in content:
            parts = content.split("---", 1)
            if len(parts) > 1:
                return parts[1].strip()
            else:
                return content
        else:
            return content


# 便捷函数
def process_apple_podcast_auto(
    podcast_name: str,
    num_episodes: int = 1,
    episode_index: int = 0,
    language: str = "ch",
    **kwargs
) -> Dict:
    """
    便捷函数：自动化处理单个 Apple Podcast 剧集
    
    Args:
        podcast_name: 播客名称
        num_episodes: 获取剧集数量
        episode_index: 要处理的剧集索引（从0开始）
        language: 语言偏好
        **kwargs: 其他处理选项
        
    Returns:
        Dict: 处理结果
    """
    automation = PodlensAutomation(language=language)
    return automation.process_apple_podcast(
        podcast_name=podcast_name,
        num_episodes=num_episodes,
        episode_indices=[episode_index],
        **kwargs
    )


def process_youtube_auto(
    search_query: str,
    num_videos: int = 1,
    video_index: int = 0,
    language: str = "ch",
    **kwargs
) -> Dict:
    """
    便捷函数：自动化处理单个 YouTube 视频
    
    Args:
        search_query: 搜索关键词
        num_videos: 搜索结果数量
        video_index: 要处理的视频索引（从0开始）
        language: 语言偏好
        **kwargs: 其他处理选项
        
    Returns:
        Dict: 处理结果
    """
    automation = PodlensAutomation(language=language)
    return automation.process_youtube(
        search_query=search_query,
        num_videos=num_videos,
        video_indices=[video_index],
        **kwargs
    ) 