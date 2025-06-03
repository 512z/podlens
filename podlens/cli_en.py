#!/usr/bin/env python3
"""
PodLens English CLI Interface
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from .apple_podcast_en import ApplePodcastExplorer, MLX_WHISPER_AVAILABLE, MLX_DEVICE, GROQ_AVAILABLE
from .youtube_en import Podnet

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

# Check Gemini API availability
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_AVAILABLE = bool(GEMINI_API_KEY)


def show_logo():
    """Display ASCII logo"""
    gray = "\033[90m"  # Gray color
    reset = "\033[0m"  # Reset color
    print(f"{gray}  ██████╗  ██████╗ ██████╗ ██╗     ███████╗███╗   ██╗███████╗{reset}")
    print(f"{gray}  ██╔══██╗██╔═══██╗██╔══██╗██║     ██╔════╝████╗  ██║██╔════╝{reset}")
    print(f"{gray}  ██████╔╝██║   ██║██║  ██║██║     █████╗  ██╔██╗ ██║███████╗{reset}")
    print(f"{gray}  ██╔═══╝ ██║   ██║██║  ██║██║     ██╔══╝  ██║╚██╗██║╚════██║{reset}")
    print(f"{gray}  ██║     ╚██████╔╝██████╔╝███████╗███████╗██║ ╚████║███████║{reset}")
    print(f"{gray}  ╚═╝      ╚═════╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝{reset}")


def show_status():
    """Display system status in English"""
    # Dynamically check API availability after environment loading
    import os
    
    # Re-check API availability
    groq_available = bool(os.getenv('GROQ_API_KEY'))
    gemini_available = bool(os.getenv('GEMINI_API_KEY'))
    
    if MLX_WHISPER_AVAILABLE:
        print(f"🎯 MLX Whisper available, using device: {MLX_DEVICE}")
    else:
        print("⚠️  MLX Whisper not available")
    
    if groq_available:
        print("🚀 Groq API available, ultra-fast transcription enabled")
    else:
        print("⚠️  Groq API not available")
        print("💡 Get free API key and add to .env: GROQ_API_KEY= https://console.groq.com/")
    
    if gemini_available:
        print("🤖 Gemini API available, AI summary enabled")
    else:
        print("⚠️  Gemini API not available")
        print("💡 Get free API key and add to .env: GEMINI_API_KEY= https://aistudio.google.com/app/apikey")


def main():
    """Main function"""
    show_logo()
    print()
    print("🎧🎥 Media Transcription & Summary Tool")
    print()
    print("=" * 50)
    print("Supports Apple Podcast and YouTube platforms")
    print("=" * 50)
    print()
    show_status()
    
    while True:
        # Let the user choose the information source
        print("\n📡 Please select information source:")
        print("1. Apple Podcast")
        print("2. YouTube")
        print("0. Exit")
        
        choice = input("\nPlease enter your choice (1/2/0): ").strip()
        
        if choice == '0':
            print("👋 Goodbye!")
            break
        elif choice == '1':
            # Apple Podcast processing logic
            print("\n🎧 You selected Apple Podcast")
            print("=" * 40)
            apple_main()
        elif choice == '2':
            # YouTube processing logic
            print("\n🎥 You selected YouTube")
            print("=" * 40)
            youtube_main()
        else:
            print("❌ Invalid selection, please enter 1, 2, or 0")


def apple_main():
    """Apple Podcast main processing function"""
    explorer = ApplePodcastExplorer()
    
    while True:
        # Get user input
        podcast_name = input("\nPlease enter the podcast channel name you want to search (or press Enter to return to main menu): ").strip()
        
        if not podcast_name:
            print("🔙 Back to main menu")
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
            print("❌ This channel does not have an available RSS feed URL")
            continue
        
        # Ask user how many episodes to preview
        episode_limit_input = input("Please select the number of episodes to preview (default 10): ").strip()
        if episode_limit_input:
            try:
                episode_limit = int(episode_limit_input)
                episode_limit = max(1, min(episode_limit, 50))  # Limit between 1-50
            except ValueError:
                print("Invalid input, using default value 10")
                episode_limit = 10
        else:
            episode_limit = 10
        
        episodes = explorer.get_recent_episodes(selected_channel['feed_url'], episode_limit)
        
        # Display episodes
        explorer.display_episodes(episodes, selected_channel['name'])
        
        # Ask if user wants to download
        explorer.download_episodes(episodes, selected_channel['name'])
        
        # Ask if user wants to continue
        continue_search = input("\nContinue searching other channels? (y/n): ").strip().lower()
        if continue_search not in ['y', 'yes']:
            print("🔙 Back to main menu")
            break


def youtube_main():
    """YouTube main processing function"""
    podnet = Podnet()
    podnet.run()


if __name__ == "__main__":
    main() 