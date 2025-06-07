#!/usr/bin/env python3
"""
PodLens Email Service - Core Email Notification Service
Integrates Gmail SMTP, AI Summary Generation and Automation Management
"""

import os
import smtplib
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
import re
import json
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

# Hardcoded Gmail configuration - dedicated email account
PODLENS_EMAIL = "podlensnews@gmail.com"
PODLENS_APP_PASSWORD = "nlkz yzfs ontl qnte"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
else:
    model = None

class EmailService:
    """PodLens Email Service Core Class"""
    
    def __init__(self):
        self.config_dir = Path('.podlens')
        self.setting_file = self.config_dir / 'setting'
        self.ensure_config_dir()
    
    def ensure_config_dir(self):
        """Ensure configuration directory exists"""
        self.config_dir.mkdir(exist_ok=True)
    
    def load_email_settings(self) -> Dict:
        """Load email settings"""
        settings = {
            'email_function': False,
            'user_email': '',
            'notification_times': []
        }
        
        if not self.setting_file.exists():
            return settings
        
        try:
            with open(self.setting_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == 'email_function':
                            settings[key] = value.lower() in ('true', '1', 'yes')
                        elif key == 'user_email':
                            settings[key] = value
                        elif key == 'notification_times':
                            # Parse time list, e.g. "08:00,18:00"
                            if value:
                                settings[key] = [t.strip() for t in value.split(',')]
        except Exception as e:
            print(f"⚠️  Failed to read email settings: {e}")
        
        return settings
    
    def save_email_settings(self, email_function: bool, user_email: str = '', notification_times: List[str] = None):
        """Save email settings to configuration file"""
        if notification_times is None:
            notification_times = []
        
        # Read existing settings first
        existing_lines = []
        new_email_section = []
        
        if self.setting_file.exists():
            with open(self.setting_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line_stripped = line.strip()
                    # Skip email-related setting lines and comments
                    if (not any(line_stripped.startswith(key + ' =') for key in ['email_function', 'user_email', 'notification_times']) 
                        and line_stripped not in ["# Email notification settings", "# 邮件通知设置"]):
                        existing_lines.append(line.rstrip())
        
        # Prepare new email setting lines
        new_email_section = [
            "",  # Empty line separator
            "# Email notification settings",
            f"email_function = {str(email_function).lower()}",
            f"user_email = {user_email}",
            f"notification_times = {','.join(notification_times)}" if notification_times else "notification_times ="
        ]
        
        # Write to file
        try:
            with open(self.setting_file, 'w', encoding='utf-8') as f:
                # Write existing content, removing trailing empty lines
                for i, line in enumerate(existing_lines):
                    f.write(line + '\n')
                
                # Ensure only one empty line before email settings
                if existing_lines and existing_lines[-1].strip():
                    f.write('\n')
                
                # Write email settings (skip first empty line as we added it above)
                for line in new_email_section[1:]:
                    f.write(line + '\n')
        except Exception as e:
            print(f"❌ Failed to save email settings: {e}")
            return False
        
        return True
    
    def scan_todays_summaries(self) -> List[Dict]:
        """Scan all summary files created today"""
        today = datetime.now().strftime('%Y-%m-%d')
        outputs_dir = Path('outputs')
        summaries = []
        
        if not outputs_dir.exists():
            return summaries
        
        # Iterate through all channels
        for channel_dir in outputs_dir.iterdir():
            if not channel_dir.is_dir():
                continue
            
            # Iterate through date directories
            for date_dir in channel_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                
                # Check if it's today's date
                if date_dir.name == today or self._check_if_created_today(date_dir):
                    # Iterate through episode directories
                    for episode_dir in date_dir.iterdir():
                        if not episode_dir.is_dir():
                            continue
                        
                        # Look for summary files
                        for file in episode_dir.iterdir():
                            if file.name.startswith('Summary_') and file.name.endswith('.md'):
                                if self._check_if_created_today(file):
                                    summaries.append({
                                        'channel': channel_dir.name,
                                        'episode': episode_dir.name,
                                        'file_path': file,
                                        'file_name': file.name
                                    })
        
        return summaries
    
    def _check_if_created_today(self, file_path: Path) -> bool:
        """Check if file was created today"""
        try:
            stat = file_path.stat()
            file_date = datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d')
            today = datetime.now().strftime('%Y-%m-%d')
            return file_date == today
        except:
            return False
    
    def _read_summary_content(self, file_path: Path) -> str:
        """Read summary file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Failed to read file {file_path}: {e}")
            return ""
    
    def _markdown_to_html(self, text: str) -> str:
        """Convert basic markdown format to HTML"""
        if not text:
            return text
        
        # Convert headers ### → <h3>, ## → <h2>, # → <h1>
        text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        
        # Convert bold **text** to <strong>text</strong>
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        
        # Convert italic *text* to <em>text</em>
        text = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', text)
        
        # Convert bullet lists
        lines = text.split('\n')
        result_lines = []
        in_list = False
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('* ') or stripped.startswith('- ') or stripped.startswith('• '):
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                content = stripped[2:] if stripped.startswith(('* ', '- ')) else stripped[2:]
                result_lines.append(f'<li>{content}</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                result_lines.append(line)
        
        if in_list:
            result_lines.append('</ul>')
        
        # Convert newlines to <br> tags (except for HTML tags)
        text = '\n'.join(result_lines)
        text = re.sub(r'\n(?![<ul>|</ul>|<li>|</li>|<h[1-6]>|</h[1-6]>])', '<br>\n', text)
        
        return text
    
    def generate_daily_digest(self, summaries: List[Dict]) -> str:
        """Generate daily digest using Gemini"""
        if not summaries:
            return "No new content processed today."
        
        if not model:
            return f"Processed {len(summaries)} episodes today, but AI summary feature is not configured."
        
        # Prepare prompt
        content_for_prompt = []
        for summary in summaries:
            content = self._read_summary_content(summary['file_path'])
            if content:
                content_for_prompt.append(f"""
Channel: {summary['channel']}
Episode: {summary['episode']}
Summary Content:
{content[:2000]}...
""")
        
        prompt = f"""
Please generate a concise daily digest for the following {len(summaries)} podcast/video contents.

Content as follows:
{''.join(content_for_prompt)}

Requirements:
1. Summarize core viewpoints of each episode in 1-2 sentences
2. Group by channel for display using ### Channel Name format
3. For each episode under the channel, show "Episode: Episode_Name" followed by summary
4. Highlight today's key information and insights
5. Keep total length within 300 words
6. Use English output
7. Use markdown format for better structure:
   - Use ### for channel names
   - Use "* Episode: episode_name: summary content" format for each episode
   - Add a "**Today's Key Insights:**" section at the end with main takeaways (use ** for bold)

Please generate the daily content with proper markdown formatting:
"""
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"❌ Gemini API call failed: {e}")
            return f"Processed {len(summaries)} episodes today, but AI summary generation failed."
    
    def create_html_email(self, digest_content: str, summaries: List[Dict]) -> str:
        """Create HTML email content"""
        today = datetime.now().strftime('%B %d, %Y')
        digest_html = self._markdown_to_html(digest_content)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>PodLens Daily Digest - {today}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 20px;
        }}
        .digest {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }}
        .summary-list {{
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
        }}
        .summary-item {{
            padding: 15px;
            border-bottom: 1px solid #e9ecef;
            margin-bottom: 15px;
        }}
        .summary-item:last-child {{
            border-bottom: none;
            margin-bottom: 0;
        }}
        .channel-name {{
            font-weight: bold;
            color: #667eea;
            font-size: 14px;
        }}
        .episode-name {{
            font-weight: 600;
            margin: 5px 0;
            color: #495057;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
            text-align: center;
            color: #6c757d;
            font-size: 12px;
        }}
        ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        li {{
            margin: 5px 0;
        }}
        h1, h2, h3 {{
            color: #495057;
            margin: 15px 0 10px 0;
        }}
        h3 {{
            font-size: 16px;
            font-weight: 600;
            border-bottom: 1px solid #e9ecef;
            padding-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎧 PodLens Daily Digest</h1>
        <p>{today}</p>
    </div>
    
    <div class="digest">
        <h2>📊 Today's Summary</h2>
        <p>{digest_html}</p>
    </div>
    
    <div class="summary-list">
        <h2>📝 Processing Details</h2>
        <p><strong>Processed {len(summaries)} content(s) today:</strong></p>
"""
        
        # Group by channel for display
        channels = {}
        for summary in summaries:
            channel = summary['channel']
            if channel not in channels:
                channels[channel] = []
            channels[channel].append(summary)
        
        for channel, channel_summaries in channels.items():
            html_content += f"""
        <div class="summary-item">
            <div class="channel-name">📺 {channel}</div>
"""
            for summary in channel_summaries:
                html_content += f"""
            <div class="episode-name">• {summary['episode']}</div>
"""
            html_content += """
        </div>
"""
        
        html_content += f"""
    </div>
    
    <div class="footer">
        <p>📧 This email is automatically generated and sent by PodLens</p>
        <p>🔗 Generated at {datetime.now().strftime('%H:%M:%S')}</p>
    </div>
</body>
</html>
"""
        return html_content
    
    def send_email(self, recipient_email: str, html_content: str, summaries: List[Dict]) -> bool:
        """Send email"""
        today = datetime.now().strftime('%B %d, %Y')
        subject = f"🎧 PodLens Daily Digest - {today} ({len(summaries)} new content(s))"
        
        try:
            # Create email object
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = PODLENS_EMAIL
            msg['To'] = recipient_email
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Connect to Gmail SMTP server and send email
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(PODLENS_EMAIL, PODLENS_APP_PASSWORD)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"❌ Email sending failed: {e}")
            return False
    
    def send_daily_digest(self, recipient_email: str) -> bool:
        """Main function to send daily digest email"""
        print(f"🔍 Scanning today's content and preparing to send email to {recipient_email}...")
        
        # Scan today's summaries
        summaries = self.scan_todays_summaries()
        print(f"📊 Found {len(summaries)} summaries for today")
        
        if not summaries:
            print("ℹ️  No new content today, skipping email sending")
            return True
        
        # Generate digest
        digest_content = self.generate_daily_digest(summaries)
        print(f"🤖 AI digest generation complete: {len(digest_content)} characters")
        
        # Create HTML email
        html_content = self.create_html_email(digest_content, summaries)
        
        # Send email
        success = self.send_email(recipient_email, html_content, summaries)
        
        if success:
            print(f"✅ Email sent successfully! Recipient: {recipient_email}")
        else:
            print(f"❌ Email sending failed! Recipient: {recipient_email}")
        
        return success
    
    def test_email_service(self, recipient_email: str) -> bool:
        """Test email service"""
        print(f"🧪 Testing email service, sending test email to {recipient_email}...")
        
        # Create test email content
        today = datetime.now().strftime('%B %d, %Y %H:%M:%S')
        test_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 20px; }}
        .test-box {{ background: #e3f2fd; padding: 20px; border-radius: 8px; text-align: center; }}
    </style>
</head>
<body>
    <div class="test-box">
        <h2>🧪 PodLens Email Service Test</h2>
        <p>This is a test email to verify email service configuration.</p>
        <p><strong>Test Time:</strong> {today}</p>
        <p>✅ If you receive this email, the email service is working properly!</p>
    </div>
</body>
</html>
"""
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🧪 PodLens Email Service Test - {today}"
            msg['From'] = PODLENS_EMAIL
            msg['To'] = recipient_email
            
            html_part = MIMEText(test_html, 'html', 'utf-8')
            msg.attach(html_part)
            
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(PODLENS_EMAIL, PODLENS_APP_PASSWORD)
                server.send_message(msg)
            
            print(f"✅ Test email sent successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Test email sending failed: {e}")
            return False

class CronManager:
    """Cron Task Manager"""
    
    def __init__(self):
        self.current_user = os.getenv('USER', 'user')
        self.project_path = Path.cwd().absolute()
    
    def setup_email_cron(self, notification_times: List[str]) -> bool:
        """Setup email notification cron tasks"""
        try:
            # Remove existing PodLens email tasks
            self.remove_email_cron()
            
            if not notification_times:
                print("ℹ️  No notification times set, skipping cron configuration")
                return True
            
            # Dynamically get current Python path
            import sys
            python_path = sys.executable
            
            # Create cron tasks for each time
            cron_commands = []
            for time_str in notification_times:
                try:
                    hour, minute = time_str.split(':')
                    hour = int(hour)
                    minute = int(minute)
                    
                    cron_command = f"{minute} {hour} * * * cd \"{self.project_path}\" && {python_path} -c \"from podlens.email_service_en import send_daily_digest_from_config; send_daily_digest_from_config()\" >> .podlens/podlens_email.log 2>&1"
                    cron_commands.append(cron_command)
                    
                except ValueError:
                    print(f"⚠️  Invalid time format: {time_str}, skipping")
                    continue
            
            if not cron_commands:
                print("❌ No valid notification times")
                return False
            
            # Add to crontab
            existing_crontab = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            existing_lines = existing_crontab.stdout.split('\n') if existing_crontab.returncode == 0 else []
            
            # Filter out empty lines
            existing_lines = [line for line in existing_lines if line.strip()]
            
            # Add new tasks
            all_lines = existing_lines + cron_commands
            
            # Write new crontab
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
            process.communicate('\n'.join(all_lines) + '\n')
            
            if process.returncode == 0:
                print(f"✅ Successfully configured {len(cron_commands)} email notification tasks")
                for i, time_str in enumerate(notification_times):
                    print(f"   📅 Daily email at {time_str}")
                return True
            else:
                print("❌ Cron task configuration failed")
                return False
                
        except Exception as e:
            print(f"❌ Cron configuration error: {e}")
            return False
    
    def remove_email_cron(self) -> bool:
        """Remove email-related cron tasks"""
        try:
            existing_crontab = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if existing_crontab.returncode != 0:
                return True  # No existing crontab
            
            lines = existing_crontab.stdout.split('\n')
            # Filter out PodLens email-related tasks
            filtered_lines = [line for line in lines if 'podlens.email_service' not in line and 'email_service_en' not in line and '.podlens/podlens_email.log' not in line and 'podlens_email.log' not in line]
            
            # Update crontab if there are changes
            if len(filtered_lines) != len(lines):
                process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
                process.communicate('\n'.join(filtered_lines) + '\n')
                return process.returncode == 0
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to remove cron tasks: {e}")
            return False
    
    def check_email_cron_status(self) -> List[str]:
        """Check current email cron task status"""
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode != 0:
                return []
            
            lines = result.stdout.split('\n')
            email_crons = [line for line in lines if 'podlens.email_service' in line or 'email_service_en' in line]
            return email_crons
            
        except Exception as e:
            print(f"❌ Failed to check cron status: {e}")
            return []

# Global email service instances
email_service = EmailService()
cron_manager = CronManager()

def send_daily_digest_from_config():
    """Read settings from config file and send daily digest (for cron calls)"""
    settings = email_service.load_email_settings()
    if settings['email_function'] and settings['user_email']:
        email_service.send_daily_digest(settings['user_email'])
    else:
        print("ℹ️  Email function not enabled or email not configured")