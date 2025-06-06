#!/usr/bin/env python3
"""
PodLens Background Service - 后台定时播客获取服务
Automated hourly podcast fetching and processing
"""

import os
import time
import schedule
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import json
import logging
import hashlib

from .automation import PodlensAutomation


class PodcastListManager:
    """播客列表管理器"""
    
    def __init__(self, podlens_dir: Path):
        """
        初始化播客列表管理器
        
        Args:
            podlens_dir: .podlens 目录路径
        """
        self.podlens_dir = podlens_dir
        self.list_file = podlens_dir / "podlist"
        self.ensure_list_file()
    
    def ensure_list_file(self):
        """确保播客列表文件存在"""
        if not self.list_file.exists():
            # 创建默认播客列表
            default_podcasts = [
                "All-in",
                "The Tim Ferriss Show",
                "Lex Fridman Podcast"
            ]
            self.save_podcast_list(default_podcasts)
            print(f"📝 创建默认播客列表: {self.list_file}")
    
    def load_podcast_list(self) -> List[str]:
        """加载播客列表"""
        try:
            with open(self.list_file, 'r', encoding='utf-8') as f:
                podcasts = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            return podcasts
        except Exception as e:
            print(f"❌ 加载播客列表失败: {e}")
            return []
    
    def save_podcast_list(self, podcasts: List[str]):
        """保存播客列表"""
        try:
            with open(self.list_file, 'w', encoding='utf-8') as f:
                f.write("# PodLens 播客列表\n")
                f.write("# 每行一个播客名称，支持 Apple Podcast 搜索\n")
                f.write("# 以 # 开头的行为注释\n\n")
                for podcast in podcasts:
                    f.write(f"{podcast}\n")
            print(f"✅ 播客列表已保存: {self.list_file}")
        except Exception as e:
            print(f"❌ 保存播客列表失败: {e}")
    
    def add_podcast(self, podcast_name: str):
        """添加播客到列表"""
        podcasts = self.load_podcast_list()
        if podcast_name not in podcasts:
            podcasts.append(podcast_name)
            self.save_podcast_list(podcasts)
            print(f"✅ 已添加播客: {podcast_name}")
        else:
            print(f"⚠️  播客已存在: {podcast_name}")
    
    def remove_podcast(self, podcast_name: str):
        """从列表中移除播客"""
        podcasts = self.load_podcast_list()
        if podcast_name in podcasts:
            podcasts.remove(podcast_name)
            self.save_podcast_list(podcasts)
            print(f"✅ 已移除播客: {podcast_name}")
        else:
            print(f"⚠️  播客不存在: {podcast_name}")
    
    def list_podcasts(self):
        """显示播客列表"""
        podcasts = self.load_podcast_list()
        if podcasts:
            print("📻 当前播客列表:")
            for i, podcast in enumerate(podcasts, 1):
                print(f"  {i}. {podcast}")
        else:
            print("📻 播客列表为空")
        return podcasts


class PodcastProgressTracker:
    """播客进度跟踪器"""
    
    def __init__(self, podlens_dir: Path):
        """
        初始化播客进度跟踪器
        
        Args:
            podlens_dir: .podlens 目录路径
        """
        self.podlens_dir = podlens_dir
        self.progress_file = podlens_dir / "progress.json"
        self.podcast_progress = self.load_progress()
    
    def load_progress(self) -> Dict:
        """加载播客进度"""
        try:
            if self.progress_file.exists():
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"⚠️  加载播客进度失败: {e}")
            return {}
    
    def save_progress(self):
        """保存播客进度"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.podcast_progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存播客进度失败: {e}")
    
    def get_latest_episode_title(self, podcast_name: str) -> str:
        """获取已处理的最新剧集标题"""
        return self.podcast_progress.get(podcast_name, {}).get('latest_episode_title', '')
    
    def update_latest_episode(self, podcast_name: str, episode_title: str):
        """更新最新处理的剧集"""
        if podcast_name not in self.podcast_progress:
            self.podcast_progress[podcast_name] = {}
        
        self.podcast_progress[podcast_name].update({
            'latest_episode_title': episode_title,
            'last_updated': datetime.now().isoformat(),
            'total_processed': self.podcast_progress[podcast_name].get('total_processed', 0) + 1
        })
        self.save_progress()
    
    def get_podcast_summary(self, podcast_name: str) -> Dict:
        """获取播客处理摘要"""
        return self.podcast_progress.get(podcast_name, {
            'latest_episode_title': '从未处理',
            'last_updated': '从未处理',
            'total_processed': 0
        })


class BackgroundService:
    """后台服务主类"""
    
    def __init__(self, language: str = "ch"):
        """
        初始化后台服务
        
        Args:
            language: 处理语言
        """
        self.language = language
        
        # 创建 .podlens 系统目录
        self.podlens_dir = Path(".podlens")
        self.setup_podlens_directory()
        
        # 初始化各个组件
        self.automation = PodlensAutomation(language=language)
        self.list_manager = PodcastListManager(self.podlens_dir)
        self.progress_tracker = PodcastProgressTracker(self.podlens_dir)
        self.is_running = False
        
        # 设置日志
        self.setup_logging()
        
        # 创建状态文件
        self.status_file = self.podlens_dir / "status.json"
        self.load_global_status()
    
    def setup_podlens_directory(self):
        """设置 .podlens 系统目录"""
        try:
            self.podlens_dir.mkdir(exist_ok=True)
            
            # 创建子目录
            (self.podlens_dir / "logs").mkdir(exist_ok=True)
            (self.podlens_dir / "temp").mkdir(exist_ok=True)
            
            # 迁移旧文件到新目录
            self._migrate_old_files()
            
            # 创建 README 文件说明目录结构
            readme_file = self.podlens_dir / "README.md"
            if not readme_file.exists():
                readme_content = """# PodLens 系统目录

这个目录包含 PodLens 后台服务的所有系统文件。

## 文件说明

- `podlist`: 播客订阅列表
- `progress.json`: 播客处理进度跟踪
- `status.json`: 全局服务状态
- `logs/`: 日志文件目录
  - `background.log`: 后台服务日志
- `temp/`: 临时文件目录

## 注意事项

- 请勿手动修改 `progress.json` 和 `status.json` 文件
- 可以手动编辑 `podlist` 文件来管理播客订阅
- 日志文件会自动轮转，避免占用过多空间
"""
                with open(readme_file, 'w', encoding='utf-8') as f:
                    f.write(readme_content)
            
            print(f"📁 PodLens 系统目录已创建: {self.podlens_dir.absolute()}")
            
        except Exception as e:
            print(f"❌ 创建 .podlens 目录失败: {e}")
            raise
    
    def _migrate_old_files(self):
        """迁移旧的配置文件到新目录"""
        old_files = {
            ".podlist": "podlist",
            ".podcast_progress.json": "progress.json", 
            "podlens_status.json": "status.json"
        }
        
        migrated_files = []
        
        for old_file, new_file in old_files.items():
            old_path = Path(old_file)
            new_path = self.podlens_dir / new_file
            
            if old_path.exists() and not new_path.exists():
                try:
                    # 复制文件内容
                    import shutil
                    shutil.copy2(old_path, new_path)
                    
                    # 删除旧文件
                    old_path.unlink()
                    migrated_files.append(f"{old_file} -> .podlens/{new_file}")
                    
                except Exception as e:
                    print(f"⚠️  迁移文件 {old_file} 失败: {e}")
        
        if migrated_files:
            print("📦 已迁移旧配置文件:")
            for migration in migrated_files:
                print(f"  {migration}")
        
        # 迁移旧的日志目录
        old_logs_dir = Path("logs")
        new_logs_dir = self.podlens_dir / "logs"
        
        if old_logs_dir.exists() and old_logs_dir.is_dir():
            try:
                # 移动日志文件
                for log_file in old_logs_dir.glob("*.log"):
                    new_log_path = new_logs_dir / log_file.name
                    if not new_log_path.exists():
                        import shutil
                        shutil.move(str(log_file), str(new_log_path))
                        print(f"📄 已迁移日志文件: {log_file.name}")
                
                # 如果旧目录为空，删除它
                if not any(old_logs_dir.iterdir()):
                    old_logs_dir.rmdir()
                    print(f"🗑️  已删除空的旧日志目录: logs/")
                    
            except Exception as e:
                print(f"⚠️  迁移日志目录失败: {e}")
    
    def setup_logging(self):
        """设置日志记录"""
        log_dir = self.podlens_dir / "logs"
        log_file = log_dir / "background.log"
        
        # 配置日志格式
        log_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 文件处理器 - 写入到 .podlens/logs/background.log
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(log_formatter)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(log_formatter)
        
        # 配置主日志器
        self.logger = logging.getLogger('podlens_background')
        self.logger.setLevel(logging.INFO)
        
        # 清除现有处理器并添加新的
        self.logger.handlers.clear()
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 防止重复日志
        self.logger.propagate = False
        
        print(f"📄 日志配置完成: {log_file.absolute()}")
    
    def load_global_status(self):
        """加载全局状态信息"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    self.status = json.load(f)
            else:
                self.status = {
                    "service_started": datetime.now().isoformat(),
                    "last_run": None,
                    "total_runs": 0,
                    "total_success": 0,
                    "total_errors": 0,
                    "version": "1.0.0"
                }
                self.save_global_status()
        except Exception as e:
            self.logger.error(f"加载状态失败: {e}")
            self.status = {
                "service_started": datetime.now().isoformat(),
                "last_run": None, 
                "total_runs": 0, 
                "total_success": 0, 
                "total_errors": 0,
                "version": "1.0.0"
            }
    
    def save_global_status(self):
        """保存全局状态信息"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存状态失败: {e}")
    
    def get_latest_episode(self, podcast_name: str) -> Optional[Dict]:
        """获取播客的最新剧集"""
        try:
            # 搜索播客频道
            channels = self.automation.apple_explorer.search_podcast_channel(podcast_name)
            if not channels:
                self.logger.warning(f"未找到播客: {podcast_name}")
                return None
            
            # 使用第一个匹配的频道
            selected_channel = channels[0]
            if not selected_channel.get('feed_url'):
                self.logger.warning(f"播客 {podcast_name} 没有可用的RSS链接")
                return None
            
            # 只获取最新的1个剧集
            episodes = self.automation.apple_explorer.get_recent_episodes(
                selected_channel['feed_url'], 1
            )
            
            if not episodes:
                self.logger.warning(f"播客 {podcast_name} 没有找到剧集")
                return None
                
            latest_episode = episodes[0]
            episode_title = latest_episode.get('title', '未知标题')
            
            # 检查是否是新剧集
            last_processed_title = self.progress_tracker.get_latest_episode_title(podcast_name)
            
            if episode_title == last_processed_title:
                self.logger.info(f"✅ {podcast_name}: 最新剧集已处理过 - {episode_title[:50]}...")
                return None
            
            self.logger.info(f"📻 {podcast_name}: 发现新剧集 - {episode_title[:50]}...")
            return latest_episode
            
        except Exception as e:
            self.logger.error(f"获取播客 {podcast_name} 最新剧集失败: {e}")
            return None
    
    def process_podcast_episodes(self):
        """处理播客剧集 - 每小时运行一次"""
        self.logger.info("🚀 开始每小时播客检查")
        
        # 重新读取播客列表
        podcasts = self.list_manager.load_podcast_list()
        if not podcasts:
            self.logger.warning("播客列表为空，跳过处理")
            return
        
        self.logger.info(f"📻 检查 {len(podcasts)} 个播客的最新剧集")
        
        total_success = 0
        total_errors = 0
        
        for i, podcast_name in enumerate(podcasts, 1):
            self.logger.info(f"[{i}/{len(podcasts)}] 检查播客: {podcast_name}")
            
            try:
                # 获取最新剧集
                latest_episode = self.get_latest_episode(podcast_name)
                
                if not latest_episode:
                    continue
                
                episode_title = latest_episode.get('title', '未知标题')
                self.logger.info(f"  开始处理: {episode_title[:50]}...")
                
                try:
                    # 使用自动化接口处理这个剧集
                    result = self.automation.process_apple_podcast(
                        podcast_name=podcast_name,
                        num_episodes=1,
                        episode_indices=[0],  # 处理最新的
                        enable_transcription=True,
                        enable_summary=True,
                        summary_language=self.language,
                        enable_visualization=False
                    )
                    
                    if result['transcripts_success'] > 0:
                        # 更新进度
                        self.progress_tracker.update_latest_episode(podcast_name, episode_title)
                        total_success += 1
                        self.logger.info(f"  ✅ 处理成功: {episode_title[:50]}...")
                    else:
                        total_errors += 1
                        self.logger.error(f"  ❌ 处理失败: {episode_title[:50]}...")
                    
                    # 休息避免API限制
                    time.sleep(2)
                    
                except Exception as e:
                    total_errors += 1
                    self.logger.error(f"  ❌ 处理剧集异常: {e}")
                
            except Exception as e:
                total_errors += 1
                self.logger.error(f"❌ 处理播客 {podcast_name} 异常: {e}")
        
        # 更新全局状态
        self.status["last_run"] = datetime.now().isoformat()
        self.status["total_runs"] += 1
        self.status["total_success"] += total_success
        self.status["total_errors"] += total_errors
        self.save_global_status()
        
        self.logger.info(f"📊 每小时检查完成: 成功 {total_success}, 失败 {total_errors}")
    
    def start_background_service(self):
        """启动后台服务"""
        if self.is_running:
            print("⚠️  后台服务已在运行")
            return
        
        self.is_running = True
        
        print(f"🚀 启动 PodLens 后台服务")
        print(f"⏰ 运行频率: 每小时")
        print(f"📻 监控播客数量: {len(self.list_manager.load_podcast_list())}")
        print(f"📁 输出目录: outputs/")
        print(f"📄 状态文件: {self.status_file}")
        print("按 Ctrl+C 停止服务\n")
        
        # 设置每小时运行的定时任务
        schedule.every().hour.do(self.process_podcast_episodes)
        
        # 立即运行一次检查
        print("🔍 立即检查新剧集...")
        threading.Thread(target=self.process_podcast_episodes, daemon=True).start()
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            print("\n⏹️  收到停止信号，正在关闭后台服务...")
            self.is_running = False
        except Exception as e:
            self.logger.error(f"后台服务异常: {e}")
            self.is_running = False
    
    def stop_background_service(self):
        """停止后台服务"""
        self.is_running = False
        print("⏹️  后台服务已停止")
    
    def show_status(self):
        """显示服务状态"""
        print("📊 PodLens 后台服务状态:")
        print(f"  上次运行: {self.status.get('last_run', '从未运行')}")
        print(f"  总运行次数: {self.status.get('total_runs', 0)}")
        print(f"  总成功数: {self.status.get('total_success', 0)}")
        print(f"  总错误数: {self.status.get('total_errors', 0)}")
        print(f"  运行频率: 每小时")
        
        # 显示各播客状态
        podcasts = self.list_manager.load_podcast_list()
        if podcasts:
            print("\n📻 各播客最新状态:")
            for podcast in podcasts:
                summary = self.progress_tracker.get_podcast_summary(podcast)
                latest_title = summary.get('latest_episode_title', '从未处理')
                last_updated = summary.get('last_updated', '从未处理')
                
                if last_updated != '从未处理':
                    try:
                        dt = datetime.fromisoformat(last_updated)
                        last_updated = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
                
                # 显示最新剧集标题的前30个字符
                display_title = latest_title[:30] + "..." if len(latest_title) > 30 else latest_title
                print(f"  {podcast}:")
                print(f"    最新剧集: {display_title}")
                print(f"    处理时间: {last_updated}")
                print(f"    总处理数: {summary.get('total_processed', 0)}")


def main_background():
    """后台服务主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PodLens 后台服务管理")
    parser.add_argument("--action", choices=["start", "status", "list", "add", "remove"], 
                       default="start", help="执行的操作")
    parser.add_argument("--podcast", help="播客名称（用于添加/删除）")
    parser.add_argument("--language", choices=["ch", "en"], default="ch", help="处理语言")
    
    args = parser.parse_args()
    
    service = BackgroundService(language=args.language)
    
    if args.action == "start":
        service.start_background_service()
    elif args.action == "status":
        service.show_status()
    elif args.action == "list":
        service.list_manager.list_podcasts()
    elif args.action == "add":
        if args.podcast:
            service.list_manager.add_podcast(args.podcast)
        else:
            print("❌ 请指定播客名称: --podcast '播客名称'")
    elif args.action == "remove":
        if args.podcast:
            service.list_manager.remove_podcast(args.podcast)
        else:
            print("❌ 请指定播客名称: --podcast '播客名称'")


if __name__ == "__main__":
    main_background() 