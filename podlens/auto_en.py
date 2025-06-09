#!/usr/bin/env python3
"""
PodLens Automation Engine - English Version
Intelligent automated podcast and YouTube processing
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
import argparse
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
from .core_en import ApplePodcastExplorer, Podnet
# Import email service
from .email_service_en import email_service, cron_manager

class ConfigManager:
    """Configuration and status manager"""
    
    def __init__(self):
        # Create .podlens directory
        self.config_dir = Path('.podlens')
        self.config_dir.mkdir(exist_ok=True)
        
        # Configuration file paths
        self.status_file = self.config_dir / 'status.json'
        self.setting_file = self.config_dir / 'setting'
        
        # Subscription list file paths
        self.podlist_file = Path("my_pod.md")
        self.tubelist_file = Path("my_tube.md")
        
        # Default settings
        self.default_settings = {
            'run_frequency': 1.0,  # hours
            'monitor_podcast': True,
            'monitor_youtube': True
        }
    
    def load_settings(self) -> Dict:
        """Load settings, create default if not exists"""
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
                        
                        # Type conversion
                        if key == 'run_frequency':
                            settings[key] = float(value)
                        elif key in ['monitor_podcast', 'monitor_youtube']:
                            settings[key] = value.lower() in ('true', '1', 'yes')
                        else:
                            settings[key] = value
            
            # Merge with defaults
            result = self.default_settings.copy()
            result.update(settings)
            return result
            
        except Exception as e:
            print(f"⚠️  Failed to read settings file: {e}, using defaults")
            return self.default_settings.copy()
    
    def save_settings(self, settings: Dict):
        """Save settings to file"""
        try:
            with open(self.setting_file, 'w', encoding='utf-8') as f:
                f.write("# PodLens Automation Settings\n")
                f.write("# Run frequency (hours), supports decimals, e.g. 0.5 means 30 minutes\n")
                f.write(f"run_frequency = {settings['run_frequency']}\n\n")
                f.write("# Whether to monitor Apple Podcast (my_pod.md)\n")
                f.write(f"monitor_podcast = {str(settings['monitor_podcast']).lower()}\n\n")
                f.write("# Whether to monitor YouTube (my_tube.md)\n")
                f.write(f"monitor_youtube = {str(settings['monitor_youtube']).lower()}\n\n")
                f.write("# Email notification settings\n")
                f.write("email_function = false\n")
                f.write("user_email = #user@example.com\n")
                f.write("notification_times = #08:00,18:00\n\n")
                f.write("# Notion sync settings\n")
                
                # Use actual setting values instead of default template
                notion_token = settings.get('notion_token', '#your notion token found in https://www.notion.so/my-integrations')
                notion_page_id = settings.get('notion_page_id', '#your notion page id found in https://www.notion.so/page-pageid')
                
                f.write(f"notion_token = {notion_token}\n")
                f.write(f"notion_page_id = {notion_page_id}\n")
        except Exception as e:
            print(f"⚠️  Failed to save settings file: {e}")
    
    def load_status(self) -> Dict:
        """Load processing status"""
        if not self.status_file.exists():
            return {'podcast': {}, 'youtube': {}}
        
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Failed to read status file: {e}")
            return {'podcast': {}, 'youtube': {}}
    
    def save_status(self, status: Dict):
        """Save processing status"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save status file: {e}")
    
    def ensure_config_files(self):
        """Ensure configuration files exist"""
        if not self.podlist_file.exists():
            podlist_template = """# PodLens Podcast Subscription List
# This file manages the podcast channels you want to automatically process.

## How to Use
# - One podcast name per line
# - Supports podcast names searchable on Apple Podcast
# - Lines starting with `#` are comments and will be ignored
# - Empty lines will also be ignored

## Example Podcasts
thoughts on the market
# or: thoughts on the market - morgan stanley

## Business Podcasts


## Tech Podcasts


"""
            with open(self.podlist_file, 'w', encoding='utf-8') as f:
                f.write(podlist_template)
            print(f"🎧 Created podcast configuration file: {self.podlist_file}")
        
        if not self.tubelist_file.exists():
            tubelist_template = """# YouTube Channel Subscription List

# This file manages the YouTube channels you want to automatically process.

## How to Use
# - One channel name per line (no @ symbol needed)
# - Channel name is the part after @ in YouTube URL
# - Example: https://www.youtube.com/@Bloomberg_Live/videos → fill in Bloomberg_Live
# - Lines starting with `#` are comments and will be ignored
# - Empty lines will also be ignored

## Example Channels
Bloomberg_Live


## Business Channels


## Tech Channels


"""
            with open(self.tubelist_file, 'w', encoding='utf-8') as f:
                f.write(tubelist_template)
            print(f"📺 Created YouTube channel configuration file: {self.tubelist_file}")

    def parse_markdown_list(self, file_path: Path) -> List[str]:
        """Parse list items from markdown file (keeping user's original logic)"""
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
            print(f"❌ Failed to read file {file_path}: {e}")
        
        return items
    
    def load_podcast_list(self) -> List[str]:
        """Load podcast list"""
        return self.parse_markdown_list(self.podlist_file)
    
    def load_youtube_list(self) -> List[str]:
        """Load YouTube channel list"""
        return self.parse_markdown_list(self.tubelist_file)


class ProgressTracker:
    """Processing progress tracker"""
    
    def __init__(self):
        self.status_file = Path(".podlens/status.json")
        self.load_status()
    
    def load_status(self):
        """Load processing status"""
        try:
            # Ensure directory exists
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
            print(f"⚠️ Failed to load status file: {e}")
            self.status = {
                "podcasts": {},
                "youtube": {},
                "last_run": None,
                "total_runs": 0
            }
    
    def save_status(self):
        """Save processing status"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Failed to save status file: {e}")
    
    def is_episode_processed(self, podcast_name: str, episode_title: str) -> bool:
        """Check if episode has been processed"""
        if podcast_name not in self.status["podcasts"]:
            return False
        return episode_title in self.status["podcasts"][podcast_name]
    
    def is_video_processed(self, channel_name: str, video_title: str) -> bool:
        """Check if video has been processed"""
        if channel_name not in self.status["youtube"]:
            return False
        return video_title in self.status["youtube"][channel_name]
    
    def mark_episode_processed(self, podcast_name: str, episode_title: str):
        """Mark episode as processed"""
        if podcast_name not in self.status["podcasts"]:
            self.status["podcasts"][podcast_name] = []
        if episode_title not in self.status["podcasts"][podcast_name]:
            self.status["podcasts"][podcast_name].append(episode_title)
        self.save_status()
    
    def mark_video_processed(self, channel_name: str, video_title: str):
        """Mark video as processed"""
        if channel_name not in self.status["youtube"]:
            self.status["youtube"][channel_name] = []
        if video_title not in self.status["youtube"][channel_name]:
            self.status["youtube"][channel_name].append(video_title)
        self.save_status()


class AutoEngine:
    """Intelligent automation engine - directly reusing perfected scripts"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.progress_tracker = ProgressTracker()  # Add progress tracker
        self.is_running = False
        
        # Load settings
        self.settings = self.config_manager.load_settings()
        
        # Use perfected explorers
        self.apple_explorer = ApplePodcastExplorer()
        self.podnet = Podnet()
    
    def process_podcast(self, podcast_name: str) -> bool:
        """Process single podcast - using automation method"""
        try:
            print(f"🔍 Checking podcast: {podcast_name}")
            
            # Use automation method for processing (now pass progress_tracker for duplicate check)
            success, episode_title = self.apple_explorer.auto_process_latest_episode(podcast_name, self.progress_tracker)
            
            if success:
                print(f"✅ {podcast_name} processing complete")
                # Mark as processed (using actual episode title)
                self.progress_tracker.mark_episode_processed(podcast_name, episode_title)
                return True
            else:
                # Distinguish between "no new content" and "actual failure"
                if episode_title:  # If episode_title exists, episodes were found but all already processed
                    print(f"ℹ️  {podcast_name} no new content to process")
                else:  # If no episode_title, it's an actual failure (search failed, etc.)
                    print(f"❌ {podcast_name} processing failed")
                return False
                
        except Exception as e:
            print(f"❌ Exception processing podcast {podcast_name}: {e}")
            return False
    
    def process_youtube(self, channel_name: str) -> bool:
        """Process YouTube channel - using automation method"""
        try:
            print(f"🔍 Checking YouTube channel: @{channel_name}")
            
            # Use automation method for processing (now pass progress_tracker for duplicate check)
            success, video_title = self.podnet.auto_process_channel_latest_video(channel_name, self.progress_tracker)
            
            if success:
                print(f"✅ @{channel_name} processing complete")
                # Mark as processed (using actual video title)
                self.progress_tracker.mark_video_processed(channel_name, video_title)
                return True
            else:
                # Distinguish between "no new content" and "actual failure"
                if video_title:  # If video_title exists, videos were found but all already processed
                    print(f"ℹ️  @{channel_name} no new content to process")
                else:  # If no video_title, it's an actual failure (search failed, etc.)
                    print(f"❌ @{channel_name} processing failed")
                return False
                
        except Exception as e:
            print(f"❌ Exception processing YouTube channel @{channel_name}: {e}")
            return False
    
    def run_hourly_check(self):
        """Hourly check"""
        print("⏰ Starting hourly check")
        
        # Update running status
        self.progress_tracker.status["total_runs"] += 1
        self.progress_tracker.status["last_run"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.progress_tracker.save_status()
        
        # Process podcasts (only when enabled)
        if self.settings['monitor_podcast']:
            podcasts = self.config_manager.load_podcast_list()
            podcast_success = 0
            for podcast in podcasts:
                if self.process_podcast(podcast):
                    podcast_success += 1
                time.sleep(2)  # Avoid API limits
        else:
            podcasts = []
            podcast_success = 0
        
        # Process YouTube (only when enabled)
        if self.settings['monitor_youtube']:
            channels = self.config_manager.load_youtube_list()
            youtube_success = 0
            for channel in channels:
                if self.process_youtube(channel):
                    youtube_success += 1
                time.sleep(2)  # Avoid API limits
        else:
            channels = []
            youtube_success = 0
        
        print(f"✅ Check complete - Podcasts: {podcast_success}/{len(podcasts)}, YouTube: {youtube_success}/{len(channels)}")
        
        # Save final status
        self.progress_tracker.save_status()
    
    def start_24x7_service(self):
        """Start 24x7 service"""
        if self.is_running:
            print("⚠️ Automation service is already running")
            return
        
        print("🤖 Starting PodLens 24x7 Intelligent Automation Service\n")
        
        # Ensure configuration files exist
        self.config_manager.ensure_config_files()
        
        self.is_running = True
        
        # Adjust running frequency based on settings
        interval_minutes = int(self.settings['run_frequency'] * 60)
        if self.settings['run_frequency'] == 1.0:
            print(f"⏰ Running frequency: hourly")
        else:
            print(f"⏰ Running frequency: every {self.settings['run_frequency']} hours ({interval_minutes} minutes)")
        
        podcast_count = len(self.config_manager.load_podcast_list()) if self.settings['monitor_podcast'] else 0
        youtube_count = len(self.config_manager.load_youtube_list()) if self.settings['monitor_youtube'] else 0
        
        print(f"🎧 Monitoring podcasts: {podcast_count}")
        print(f"📺 Monitoring YouTube channels: {youtube_count}")
        print("Press Ctrl+Z to stop service\n")
        
        # Set scheduled task
        schedule.every(interval_minutes).minutes.do(self.run_hourly_check)
        
        # Run immediately once
        threading.Thread(target=self.run_hourly_check, daemon=True).start()
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n⏹️ Shutting down automation service...")
            self.is_running = False
        except Exception as e:
            print(f"❌ Automation service exception: {e}")
            self.is_running = False
    
    def show_status(self):
        """Display status"""
        print("📊 PodLens Intelligent Automation Service Status:")
        print(f"  Running frequency: {self.settings['run_frequency']} hours")
        print(f"  Monitor podcasts: {'Enabled' if self.settings['monitor_podcast'] else 'Disabled'}")
        print(f"  Monitor YouTube: {'Enabled' if self.settings['monitor_youtube'] else 'Disabled'}")
        
        if self.settings['monitor_podcast']:
            podcasts = self.config_manager.load_podcast_list()
            if podcasts:
                print(f"\n📻 Monitoring {len(podcasts)} podcasts:")
                for podcast in podcasts:
                    print(f"  - {podcast}")
        
        if self.settings['monitor_youtube']:
            channels = self.config_manager.load_youtube_list()
            if channels:
                print(f"\n📺 Monitoring {len(channels)} YouTube channels:")
                for channel in channels:
                    print(f"  - @{channel}")


def start_automation():
    """Start automation service"""
    engine = AutoEngine()
    engine.start_24x7_service()


def show_status():
    """Show automation status"""
    engine = AutoEngine()
    engine.show_status()


def show_automation_status():
    """Show automation service status (backward compatibility)"""
    show_status()


def setup_email_service(user_email: str, notification_times: List[str]) -> bool:
    """Setup email service"""
    print(f"📧 Configuring email service...")
    print(f"   Email: {user_email}")
    print(f"   Notification times: {', '.join(notification_times)}")
    
    # Save configuration
    success = email_service.save_email_settings(
        email_function=True,
        user_email=user_email,
        notification_times=notification_times
    )
    
    if not success:
        print("❌ Failed to save email configuration")
        return False
    
    # Setup cron tasks
    success = cron_manager.setup_email_cron(notification_times)
    if not success:
        print("❌ Failed to configure cron tasks")
        return False
    
    print("✅ Email service configured successfully!")
    print("📱 You will receive daily podcast summaries at specified times")
    return True

def show_email_status():
    """Show email service status"""
    settings = email_service.load_email_settings()
    cron_tasks = cron_manager.check_email_cron_status()
    
    print("📧 Email Service Status:")
    print(f"   Status: {'Enabled' if settings['email_function'] else 'Disabled'}")
    print(f"   Email address: {settings['user_email'] if settings['user_email'] else 'Not configured'}")
    print(f"   Notification times: {', '.join(settings['notification_times']) if settings['notification_times'] else 'Not set'}")
    print(f"   Cron tasks: {len(cron_tasks)} tasks")
    
    if cron_tasks:
        print("   Task details:")
        for task in cron_tasks:
            print(f"     - {task}")

def sync_email_config():
    """Automatically read configuration file and sync cron tasks"""
    print("🔄 Syncing email configuration...")
    
    # Read current configuration
    settings = email_service.load_email_settings()
    
    if not settings['email_function']:
        print("ℹ️  Email function not enabled, no sync needed")
        return True
    
    if not settings['user_email']:
        print("❌ Email address not found in configuration file")
        return False
    
    if not settings['notification_times']:
        print("❌ Notification times not found in configuration file")
        return False
    
    print(f"📧 Configuration found:")
    print(f"   Email: {settings['user_email']}")
    print(f"   Notification times: {', '.join(settings['notification_times'])}")
    
    # Sync cron tasks
    success = cron_manager.setup_email_cron(settings['notification_times'])
    
    if success:
        print("✅ Cron tasks synced successfully!")
        print("📱 Email service updated according to configuration file")
        return True
    else:
        print("❌ Failed to sync cron tasks")
        return False

def disable_email_service():
    """Disable email service"""
    print("🛑 Disabling email service...")
    
    # Remove cron tasks
    success = cron_manager.remove_email_cron()
    if success:
        print("✅ Email scheduled tasks removed")
    else:
        print("⚠️  Failed to remove scheduled tasks")
    
    # Update configuration
    email_service.save_email_settings(email_function=False)
    print("✅ Email service disabled")

def update_notion_settings(token=None, page_id=None):
    """Update Notion settings"""
    config_manager = ConfigManager()
    
    # Read existing settings
    settings = config_manager.load_settings()
    
    # Read existing Notion settings
    notion_token = settings.get('notion_token', '')
    notion_page_id = settings.get('notion_page_id', '')
    
    # Update settings
    if token:
        notion_token = token
        settings['notion_token'] = token
        print(f"✅ Notion token updated")
    
    if page_id:
        notion_page_id = page_id
        settings['notion_page_id'] = page_id
        print(f"✅ Notion page ID updated")
    
    # Save updated settings
    config_manager.save_settings(settings)
    
    return notion_token, notion_page_id

def run_notion_sync():
    """Execute Notion sync"""
    try:
        from .notion_en import main as notion_main
        notion_main()
    except ImportError as e:
        print(f"❌ Failed to import Notion module: {e}")
    except Exception as e:
        print(f"❌ Notion sync failed: {e}")

def main():
    """Main function for command line interface"""
    parser = argparse.ArgumentParser(description='PodLens Automation Service')
    parser.add_argument('--status', action='store_true', help='Show automation status')
    parser.add_argument('--email', metavar='EMAIL', help='Configure email service, specify recipient email')
    parser.add_argument('--time', metavar='TIME', help='Email notification times, format: 08:00,18:00')
    parser.add_argument('--email-sync', action='store_true', help='Sync email configuration to cron tasks')
    parser.add_argument('--email-status', action='store_true', help='Show email service status')
    parser.add_argument('--email-disable', action='store_true', help='Disable email service')
    parser.add_argument('--notion', action='store_true', help='Sync to Notion')
    parser.add_argument('--notiontoken', metavar='TOKEN', help='Configure Notion token')
    parser.add_argument('--notionpage', metavar='PAGE_ID', help='Configure Notion page ID')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.email:
        # Email configuration
        user_email = args.email
        notification_times = []
        
        if args.time:
            # Parse time parameters
            time_parts = args.time.split(',')
            for time_part in time_parts:
                time_part = time_part.strip()
                if ':' in time_part:
                    notification_times.append(time_part)
                else:
                    print(f"⚠️  Invalid time format: {time_part}, should be HH:MM format")
        
        if not notification_times:
            # Default times
            notification_times = ['08:00', '18:00']
            print("ℹ️  No notification times specified, using defaults: 08:00, 18:00")
        
        setup_email_service(user_email, notification_times)
    elif args.time and not args.email:
        # Update time only
        notification_times = []
        time_parts = args.time.split(',')
        for time_part in time_parts:
            time_part = time_part.strip()
            if ':' in time_part:
                notification_times.append(time_part)
            else:
                print(f"⚠️  Invalid time format: {time_part}, should be HH:MM format")
        
        if not notification_times:
            print("❌ No valid time format provided")
            return
        
        # Read existing email configuration
        current_settings = email_service.load_email_settings()
        
        if not current_settings['email_function'] or not current_settings['user_email']:
            print("❌ Please set email address first using --email parameter")
            print("💡 Example: autopodlens --email your@email.com --time 01:50")
            return
        
        # Reconfigure with existing email and new time
        print(f"🔄 Updating email notification times...")
        print(f"   Email: {current_settings['user_email']}")
        print(f"   New times: {', '.join(notification_times)}")
        
        setup_email_service(current_settings['user_email'], notification_times)
    elif args.email_sync:
        sync_email_config()
    elif args.email_status:
        show_email_status()
    elif args.email_disable:
        disable_email_service()
    elif args.notion:
        run_notion_sync()
    elif args.notiontoken:
        update_notion_settings(token=args.notiontoken)
    elif args.notionpage:
        update_notion_settings(page_id=args.notionpage)
    else:
        start_automation()


if __name__ == "__main__":
    main() 