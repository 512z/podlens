#!/usr/bin/env python3
"""
PodLens 中文版命令行界面
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from .apple_podcast_ch import ApplePodcastExplorer, MLX_WHISPER_AVAILABLE, MLX_DEVICE, GROQ_AVAILABLE
from .youtube_ch import Podnet

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

# Load environment variables
load_env_robust()

# 检查Gemini API可用性
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_AVAILABLE = bool(GEMINI_API_KEY)


def show_logo():
    """显示ASCII logo"""
    gray = "\033[90m"  # 灰色
    reset = "\033[0m"  # 重置颜色
    print(f"{gray}  ██████╗  ██████╗ ██████╗ ██╗     ███████╗███╗   ██╗███████╗{reset}")
    print(f"{gray}  ██╔══██╗██╔═══██╗██╔══██╗██║     ██╔════╝████╗  ██║██╔════╝{reset}")
    print(f"{gray}  ██████╔╝██║   ██║██║  ██║██║     █████╗  ██╔██╗ ██║███████╗{reset}")
    print(f"{gray}  ██╔═══╝ ██║   ██║██║  ██║██║     ██╔══╝  ██║╚██╗██║╚════██║{reset}")
    print(f"{gray}  ██║     ╚██████╔╝██████╔╝███████╗███████╗██║ ╚████║███████║{reset}")
    print(f"{gray}  ╚═╝      ╚═════╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝{reset}")


def show_status():
    """显示系统状态（中文）"""
    # Dynamically check API availability after environment loading
    import os
    
    # Re-check API availability
    groq_available = bool(os.getenv('GROQ_API_KEY'))
    gemini_available = bool(os.getenv('GEMINI_API_KEY'))
    
    if MLX_WHISPER_AVAILABLE:
        print(f"🎯 MLX Whisper 可用，使用设备: {MLX_DEVICE}")
    else:
        print("⚠️  MLX Whisper 不可用")
    
    if groq_available:
        print("🚀 Groq API 可用，已启用超快转录")
    else:
        print("⚠️  Groq API 不可用")
        print("💡 请获得免费api并加入.env: GROQ_API_KEY= https://console.groq.com/")
    
    if gemini_available:
        print("🤖 Gemini API 可用，已启用AI摘要功能")
    else:
        print("⚠️  Gemini API 不可用")
        print("💡 请获得免费api并加入.env: GEMINI_API_KEY= https://aistudio.google.com/app/apikey")


def main():
    """主函数"""
    show_logo()
    print()
    print("🎧🎥 媒体转录与摘要工具")
    print()
    print("=" * 50)
    print("支持 Apple Podcast 和 YouTube 平台")
    print("=" * 50)
    print()
    show_status()
    
    while True:
        # 让用户选择信息来源
        print("\n📡 请选择信息来源：")
        print("1. Apple Podcast")
        print("2. YouTube")
        print("0. 退出")
        
        choice = input("\n请输入您的选择 (1/2/0): ").strip()
        
        if choice == '0':
            print("👋 再见！")
            break
        elif choice == '1':
            # Apple Podcast 处理逻辑
            print("\n🎧 您选择了 Apple Podcast")
            print("=" * 40)
            apple_main()
        elif choice == '2':
            # YouTube 处理逻辑
            print("\n🎥 您选择了 YouTube")
            print("=" * 40)
            youtube_main()
        else:
            print("❌ 选择无效，请输入 1、2 或 0")


def apple_main():
    """Apple Podcast 主处理函数"""
    explorer = ApplePodcastExplorer()
    
    while True:
        # 获取用户输入
        podcast_name = input("\n请输入您要搜索的播客频道名称（或直接回车返回主菜单）: ").strip()
        
        if not podcast_name:
            print("🔙 返回主菜单")
            break
        
        # 搜索频道
        channels = explorer.search_podcast_channel(podcast_name)
        
        # 展示频道并让用户选择
        selected_index = explorer.display_channels(channels)
        
        if selected_index == -1:
            continue
        
        selected_channel = channels[selected_index]
        
        # 检查RSS订阅链接是否可用
        if not selected_channel['feed_url']:
            print("❌ 该频道没有可用的 RSS 订阅链接")
            continue
        
        # 询问用户要预览的节目数量
        episode_limit_input = input("请选择要预览的节目数量（默认 10）: ").strip()
        if episode_limit_input:
            try:
                episode_limit = int(episode_limit_input)
                episode_limit = max(1, min(episode_limit, 50))  # 限制在1-50之间
            except ValueError:
                print("输入无效，使用默认值 10")
                episode_limit = 10
        else:
            episode_limit = 10
        
        episodes = explorer.get_recent_episodes(selected_channel['feed_url'], episode_limit)
        
        # 展示剧集
        explorer.display_episodes(episodes, selected_channel['name'])
        
        # 询问用户是否要下载
        explorer.download_episodes(episodes, selected_channel['name'])
        
        # 询问用户是否要继续
        continue_search = input("\n继续搜索其他频道？(y/n): ").strip().lower()
        if continue_search not in ['y', 'yes']:
            print("🔙 返回主菜单")
            break


def youtube_main():
    """YouTube 主处理函数"""
    podnet = Podnet()
    podnet.run()


if __name__ == "__main__":
    main() 