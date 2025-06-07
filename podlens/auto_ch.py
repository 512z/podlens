#!/usr/bin/env python3
"""
PodLens 自动化引擎 - 直接复用完善的脚本
"""

import os
import time
import schedule
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import json
import sys
from dotenv import load_dotenv

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

# Import the automation-optimized core modules
from .core_ch import ApplePodcastExplorer, Podnet





class ConfigManager:
    """配置和状态管理器"""
    
    def __init__(self):
        # 创建 .podlens 目录
        self.config_dir = Path('.podlens')
        self.config_dir.mkdir(exist_ok=True)
        
        # 配置文件路径
        self.status_file = self.config_dir / 'status.json'
        self.setting_file = self.config_dir / 'setting'
        
        # 订阅列表文件路径（保持用户原有逻辑）
        self.podlist_file = Path("my_pod.md")
        self.tubelist_file = Path("my_tube.md")
        
        # 默认设置
        self.default_settings = {
            'run_frequency': 1.0,  # 小时
            'monitor_podcast': True,
            'monitor_youtube': True
        }
    
    def load_settings(self) -> Dict:
        """加载设置，如果不存在则创建默认设置"""
        if not self.setting_file.exists():
            self.save_settings(self.default_settings)
            return self.default_settings.copy()
        
        try:
            settings = {}
            with open(self.setting_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # 类型转换
                        if key == 'run_frequency':
                            settings[key] = float(value)
                        elif key in ['monitor_podcast', 'monitor_youtube']:
                            settings[key] = value.lower() in ('true', '1', 'yes')
                        else:
                            settings[key] = value
            
            # 合并默认设置
            result = self.default_settings.copy()
            result.update(settings)
            return result
            
        except Exception as e:
            print(f"⚠️  读取设置文件失败: {e}，使用默认设置")
            return self.default_settings.copy()
    
    def save_settings(self, settings: Dict):
        """保存设置到文件"""
        try:
            with open(self.setting_file, 'w', encoding='utf-8') as f:
                f.write("# PodLens 自动化设置\n")
                f.write("# 运行频率（小时），支持小数，如0.5表示30分钟\n")
                f.write(f"run_frequency = {settings['run_frequency']}\n\n")
                f.write("# 是否监控Apple Podcast (my_pod.md)\n")
                f.write(f"monitor_podcast = {str(settings['monitor_podcast']).lower()}\n\n")
                f.write("# 是否监控YouTube (my_tube.md)\n")
                f.write(f"monitor_youtube = {str(settings['monitor_youtube']).lower()}\n")
        except Exception as e:
            print(f"⚠️  保存设置文件失败: {e}")
    
    def load_status(self) -> Dict:
        """加载处理状态"""
        if not self.status_file.exists():
            return {'podcast': {}, 'youtube': {}}
        
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  读取状态文件失败: {e}")
            return {'podcast': {}, 'youtube': {}}
    
    def save_status(self, status: Dict):
        """保存处理状态"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  保存状态文件失败: {e}")
    
    def ensure_config_files(self):
        """确保配置文件存在"""
        if not self.podlist_file.exists():
            podlist_template = """# PodLens 播客订阅列表
# 这个文件用来管理您想要自动处理的播客频道。

## 使用方法
# - 每行一个播客名称
# - 支持 Apple Podcast 搜索的播客名称
# - 以 `#` 开头的行为注释，会被忽略
# - 空行也会被忽略

## 示例播客
thoughts on the market
# or: thoughts on the market - morgan stanley

## 商业播客


## 科技播客


"""
            with open(self.podlist_file, 'w', encoding='utf-8') as f:
                f.write(podlist_template)
            print(f"🎧 已创建播客配置文件: {self.podlist_file}")
        
        if not self.tubelist_file.exists():
            tubelist_template = """# YouTube 频道订阅列表

# 这个文件用来管理您想要自动处理的YouTube频道。

## 使用方法
# - 每行一个频道名称（不需要 @ 符号）
# - 频道名称就是 YouTube URL 中 @后面的部分
# - 例如：https://www.youtube.com/@Bloomberg_Live/videos → 填写 Bloomberg_Live
# - 以 `#` 开头的行为注释，会被忽略
# - 空行也会被忽略

## 示例频道
Bloomberg_Live


## 商业频道


## 科技频道


"""
            with open(self.tubelist_file, 'w', encoding='utf-8') as f:
                f.write(tubelist_template)
            print(f"📺 已创建YouTube频道配置文件: {self.tubelist_file}")

    def parse_markdown_list(self, file_path: Path) -> List[str]:
        """解析markdown文件中的列表项（保持用户原有逻辑）"""
        if not file_path.exists():
            return []
        
        items = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith('- '):
                        line = line[2:].strip()
                    elif line.startswith('* '):
                        line = line[2:].strip()
                    elif line.startswith('+ '):
                        line = line[2:].strip()
                    
                    if line:
                        items.append(line)
        except Exception as e:
            print(f"❌ 读取文件 {file_path} 失败: {e}")
        
        return items
    
    def load_podcast_list(self) -> List[str]:
        """加载播客列表"""
        return self.parse_markdown_list(self.podlist_file)
    
    def load_youtube_list(self) -> List[str]:
        """加载YouTube频道列表"""
        return self.parse_markdown_list(self.tubelist_file)


class ProgressTracker:
    """处理进度跟踪器"""
    
    def __init__(self):
        self.status_file = Path(".podlens/status.json")
        self.load_status()
    
    def load_status(self):
        """加载处理状态"""
        try:
            # 确保目录存在
            self.status_file.parent.mkdir(exist_ok=True)
            
            if self.status_file.exists():
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    self.status = json.load(f)
            else:
                self.status = {
                    "podcasts": {},
                    "youtube": {},
                    "last_run": None,
                    "total_runs": 0
                }
        except Exception as e:
            print(f"⚠️ 加载状态文件失败: {e}")
            self.status = {
                "podcasts": {},
                "youtube": {},
                "last_run": None,
                "total_runs": 0
            }
    
    def save_status(self):
        """保存处理状态"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存状态文件失败: {e}")
    
    def is_episode_processed(self, podcast_name: str, episode_title: str) -> bool:
        """检查剧集是否已处理"""
        if podcast_name not in self.status["podcasts"]:
            return False
        return episode_title in self.status["podcasts"][podcast_name]
    
    def is_video_processed(self, channel_name: str, video_title: str) -> bool:
        """检查视频是否已处理"""
        if channel_name not in self.status["youtube"]:
            return False
        return video_title in self.status["youtube"][channel_name]
    
    def mark_episode_processed(self, podcast_name: str, episode_title: str):
        """标记剧集已处理"""
        if podcast_name not in self.status["podcasts"]:
            self.status["podcasts"][podcast_name] = []
        if episode_title not in self.status["podcasts"][podcast_name]:
            self.status["podcasts"][podcast_name].append(episode_title)
        self.save_status()
    
    def mark_video_processed(self, channel_name: str, video_title: str):
        """标记视频已处理"""
        if channel_name not in self.status["youtube"]:
            self.status["youtube"][channel_name] = []
        if video_title not in self.status["youtube"][channel_name]:
            self.status["youtube"][channel_name].append(video_title)
        self.save_status()


class AutoEngine:
    """智能自动化引擎 - 直接复用完善的脚本"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.progress_tracker = ProgressTracker()  # 添加进度跟踪器
        self.is_running = False
        
        # 加载设置
        self.settings = self.config_manager.load_settings()
        
        # 使用完善的探索器
        self.apple_explorer = ApplePodcastExplorer()
        self.podnet = Podnet()
    
    def process_podcast(self, podcast_name: str) -> bool:
        """处理单个播客 - 使用自动化方法"""
        try:
            print(f"🔍 检查播客: {podcast_name}")
            
            # 使用自动化方法处理（现在传入progress_tracker来做重复检查）
            success, episode_title = self.apple_explorer.auto_process_latest_episode(podcast_name, self.progress_tracker)
            
            if success:
                print(f"✅ {podcast_name} 处理完成")
                # 标记为已处理（使用实际的episode标题）
                self.progress_tracker.mark_episode_processed(podcast_name, episode_title)
                return True
            else:
                print(f"❌ {podcast_name} 处理失败")
                return False
                
        except Exception as e:
            print(f"❌ 处理播客 {podcast_name} 异常: {e}")
            return False
    
    def process_youtube(self, channel_name: str) -> bool:
        """处理YouTube频道 - 使用自动化方法"""
        try:
            print(f"🔍 检查YouTube频道: @{channel_name}")
            
            # 使用自动化方法处理（现在传入progress_tracker来做重复检查）
            success, video_title = self.podnet.auto_process_channel_latest_video(channel_name, self.progress_tracker)
            
            if success:
                print(f"✅ @{channel_name} 处理完成")
                # 标记为已处理（使用实际的视频标题）
                self.progress_tracker.mark_video_processed(channel_name, video_title)
                return True
            else:
                print(f"❌ @{channel_name} 处理失败")
                return False
                
        except Exception as e:
            print(f"❌ 处理YouTube频道 @{channel_name} 异常: {e}")
            return False
    
    def run_hourly_check(self):
        """每小时检查"""
        print("⏰ 开始每小时检查")
        
        # 更新运行状态
        self.progress_tracker.status["total_runs"] += 1
        self.progress_tracker.status["last_run"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.progress_tracker.save_status()
        
        # 处理播客（只有启用时）
        if self.settings['monitor_podcast']:
            podcasts = self.config_manager.load_podcast_list()
            podcast_success = 0
            for podcast in podcasts:
                if self.process_podcast(podcast):
                    podcast_success += 1
                time.sleep(2)  # 避免API限制
        else:
            podcasts = []
            podcast_success = 0
        
        # 处理YouTube（只有启用时）
        if self.settings['monitor_youtube']:
            channels = self.config_manager.load_youtube_list()
            youtube_success = 0
            for channel in channels:
                if self.process_youtube(channel):
                    youtube_success += 1
                time.sleep(2)  # 避免API限制
        else:
            channels = []
            youtube_success = 0
        
        print(f"✅ 检查完成 - 播客: {podcast_success}/{len(podcasts)}, YouTube: {youtube_success}/{len(channels)}")
        
        # 保存最终状态
        self.progress_tracker.save_status()
    
    def start_24x7_service(self):
        """启动24x7服务"""
        if self.is_running:
            print("⚠️ 自动化服务已在运行")
            return
        
        print("🤖 启动 PodLens 24x7 智能自动化服务\n")
        
        # 确保配置文件存在
        self.config_manager.ensure_config_files()
        
        self.is_running = True
        
        # 根据设置调整运行频率
        interval_minutes = int(self.settings['run_frequency'] * 60)
        if self.settings['run_frequency'] == 1.0:
            print(f"⏰ 运行频率: 每小时")
        else:
            print(f"⏰ 运行频率: 每{self.settings['run_frequency']}小时 ({interval_minutes}分钟)")
        
        podcast_count = len(self.config_manager.load_podcast_list()) if self.settings['monitor_podcast'] else 0
        youtube_count = len(self.config_manager.load_youtube_list()) if self.settings['monitor_youtube'] else 0
        
        print(f"🎧 监控播客数量: {podcast_count}")
        print(f"📺 监控YouTube频道数量: {youtube_count}")
        print("按 Ctrl+Z 停止服务\n")
        
        # 设置定时任务
        schedule.every(interval_minutes).minutes.do(self.run_hourly_check)
        
        # 立即运行一次
        threading.Thread(target=self.run_hourly_check, daemon=True).start()
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n⏹️ 正在关闭自动化服务...")
            self.is_running = False
        except Exception as e:
            print(f"❌ 自动化服务异常: {e}")
            self.is_running = False
    
    def show_status(self):
        """显示状态"""
        print("📊 PodLens 智能自动化服务状态:")
        print(f"  运行频率: {self.settings['run_frequency']} 小时")
        print(f"  监控播客: {'启用' if self.settings['monitor_podcast'] else '禁用'}")
        print(f"  监控YouTube: {'启用' if self.settings['monitor_youtube'] else '禁用'}")
        
        if self.settings['monitor_podcast']:
            podcasts = self.config_manager.load_podcast_list()
            if podcasts:
                print(f"\n📻 监控的 {len(podcasts)} 个播客:")
                for podcast in podcasts:
                    print(f"  - {podcast}")
        
        if self.settings['monitor_youtube']:
            channels = self.config_manager.load_youtube_list()
            if channels:
                print(f"\n📺 监控的 {len(channels)} 个YouTube频道:")
                for channel in channels:
                    print(f"  - @{channel}")


def start_automation():
    """启动自动化服务"""
    engine = AutoEngine()
    engine.start_24x7_service()


def show_status():
    """显示自动化状态"""
    engine = AutoEngine()
    engine.show_status()


def show_automation_status():
    """显示自动化服务状态（向后兼容）"""
    show_status()


def main():
    """主函数用于命令行接口"""
    if len(sys.argv) > 1 and sys.argv[1] == '--status':
        show_status()
    else:
        start_automation()


if __name__ == "__main__":
    main() 