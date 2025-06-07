#!/usr/bin/env python3
"""
PodLens Email Service - 核心邮件通知服务
集成Gmail SMTP、AI摘要生成和自动化管理
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

# 加载环境变量
load_dotenv()

# 硬编码的Gmail配置 - 专用邮件账户
PODLENS_EMAIL = "podlensnews@gmail.com"
PODLENS_APP_PASSWORD = "nlkz yzfs ontl qnte"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# 配置Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
else:
    model = None

class EmailService:
    """PodLens邮件服务核心类"""
    
    def __init__(self):
        self.config_dir = Path('.podlens')
        self.setting_file = self.config_dir / 'setting'
        self.ensure_config_dir()
    
    def ensure_config_dir(self):
        """确保配置目录存在"""
        self.config_dir.mkdir(exist_ok=True)
    
    def load_email_settings(self) -> Dict:
        """加载邮件设置"""
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
                            # 解析时间列表，如 "08:00,18:00"
                            if value:
                                settings[key] = [t.strip() for t in value.split(',')]
        except Exception as e:
            print(f"⚠️  读取邮件设置失败: {e}")
        
        return settings
    
    def save_email_settings(self, email_function: bool, user_email: str = '', notification_times: List[str] = None):
        """保存邮件设置到配置文件"""
        if notification_times is None:
            notification_times = []
        
        # 先读取现有设置
        existing_lines = []
        new_email_section = []
        
        if self.setting_file.exists():
            with open(self.setting_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line_stripped = line.strip()
                    # 跳过邮件相关的设置行和注释
                    if (not any(line_stripped.startswith(key + ' =') for key in ['email_function', 'user_email', 'notification_times']) 
                        and line_stripped != "# 邮件通知设置"):
                        existing_lines.append(line.rstrip())
        
        # 准备新的邮件设置行
        new_email_section = [
            "",  # 空行分隔
            "# 邮件通知设置",
            f"email_function = {str(email_function).lower()}",
            f"user_email = {user_email}",
            f"notification_times = {','.join(notification_times)}" if notification_times else "notification_times ="
        ]
        
        # 写入文件
        try:
            with open(self.setting_file, 'w', encoding='utf-8') as f:
                # 写入现有内容，去除尾部多余空行
                for i, line in enumerate(existing_lines):
                    f.write(line + '\n')
                
                # 确保邮件设置前只有一个空行分隔
                if existing_lines and existing_lines[-1].strip():
                    f.write('\n')
                
                # 写入邮件设置（跳过第一个空行，因为已经在上面添加了）
                for line in new_email_section[1:]:
                    f.write(line + '\n')
        except Exception as e:
            print(f"❌ 保存邮件设置失败: {e}")
            return False
        
        return True
    
    def scan_todays_summaries(self) -> List[Dict]:
        """扫描今天创建的所有summary文件"""
        today = datetime.now().strftime('%Y-%m-%d')
        outputs_dir = Path('outputs')
        summaries = []
        
        if not outputs_dir.exists():
            return summaries
        
        # 遍历所有频道
        for channel_dir in outputs_dir.iterdir():
            if not channel_dir.is_dir():
                continue
            
            # 遍历日期目录
            for date_dir in channel_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                
                # 检查是否是今天的日期
                if date_dir.name == today or self._check_if_created_today(date_dir):
                    # 遍历episode目录
                    for episode_dir in date_dir.iterdir():
                        if not episode_dir.is_dir():
                            continue
                        
                        # 查找summary文件
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
        """检查文件是否是今天创建的"""
        try:
            stat = file_path.stat()
            file_date = datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d')
            today = datetime.now().strftime('%Y-%m-%d')
            return file_date == today
        except:
            return False
    
    def _read_summary_content(self, file_path: Path) -> str:
        """读取summary文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ 读取文件失败 {file_path}: {e}")
            return ""
    
    def _markdown_to_html(self, text: str) -> str:
        """将基本markdown格式转换为HTML"""
        if not text:
            return text
        
        # 转换标题 ### → <h3>, ## → <h2>, # → <h1>
        text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        
        # 转换粗体 **text** 为 <strong>text</strong>
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        
        # 转换斜体 *text* 为 <em>text</em>
        text = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', text)
        
        # 转换项目列表
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
        
        # 将换行符转换为<br>标签（除HTML标签外）
        text = '\n'.join(result_lines)
        text = re.sub(r'\n(?![<ul>|</ul>|<li>|</li>|<h[1-6]>|</h[1-6]>])', '<br>\n', text)
        
        return text
    
    def generate_daily_digest(self, summaries: List[Dict]) -> str:
        """使用Gemini生成日报摘要"""
        if not summaries:
            return "今日暂无新内容处理。"
        
        if not model:
            return f"今日处理了{len(summaries)}个节目，但AI摘要功能未配置。"
        
        # 准备prompt
        content_for_prompt = []
        for summary in summaries:
            content = self._read_summary_content(summary['file_path'])
            if content:
                content_for_prompt.append(f"""
频道: {summary['channel']}
节目: {summary['episode']}
摘要内容:
{content[:2000]}...
""")
        
        prompt = f"""
请为以下{len(summaries)}个播客/视频内容生成一份简洁的日报摘要。

内容如下:
{''.join(content_for_prompt)}

要求:
1. 每个节目用1-2句话概括核心观点
2. 按频道分组展示，使用### 频道名称格式
3. 在每个频道下显示"节目: 节目名称"然后跟随摘要内容
4. 突出今日的关键信息和洞察
5. 总长度控制在300字内
6. 使用中文输出
7. 使用markdown格式增强结构:
   - 使用### 标记频道名称
   - 使用"* 节目: 节目名称: 摘要内容"格式显示每个节目
   - 在最后添加"**今日关键信息与洞察:**"部分总结要点（使用**加粗）

请生成带有适当markdown格式的日报内容:
"""
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"❌ Gemini API调用失败: {e}")
            return f"今日处理了{len(summaries)}个节目，但AI摘要生成失败。"
    
    def create_html_email(self, digest_content: str, summaries: List[Dict]) -> str:
        """创建HTML邮件内容"""
        today = datetime.now().strftime('%Y年%m月%d日')
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
        <h1>🎧 PodLens 日报</h1>
        <p>{today}</p>
    </div>
    
    <div class="digest">
        <h2>📊 今日摘要</h2>
        <p>{digest_html}</p>
    </div>
    
    <div class="summary-list">
        <h2>📝 处理详情</h2>
        <p><strong>今日共处理 {len(summaries)} 个内容：</strong></p>
"""
        
        # 按频道分组显示
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
        <p>📧 此邮件由 PodLens 自动生成并发送</p>
        <p>🔗 Generated at {datetime.now().strftime('%H:%M:%S')}</p>
    </div>
</body>
</html>
"""
        return html_content
    
    def send_email(self, recipient_email: str, html_content: str, summaries: List[Dict]) -> bool:
        """发送邮件"""
        today = datetime.now().strftime('%Y年%m月%d日')
        subject = f"🎧 PodLens日报 - {today} ({len(summaries)}个新内容)"
        
        try:
            # 创建邮件对象
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = PODLENS_EMAIL
            msg['To'] = recipient_email
            
            # 添加HTML内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 连接Gmail SMTP服务器并发送邮件
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(PODLENS_EMAIL, PODLENS_APP_PASSWORD)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False
    
    def send_daily_digest(self, recipient_email: str) -> bool:
        """发送每日摘要邮件的主函数"""
        print(f"🔍 扫描今日内容并准备发送邮件给 {recipient_email}...")
        
        # 扫描今日摘要
        summaries = self.scan_todays_summaries()
        print(f"📊 找到 {len(summaries)} 个今日摘要")
        
        if not summaries:
            print("ℹ️  今日暂无新内容，跳过邮件发送")
            return True
        
        # 生成摘要
        digest_content = self.generate_daily_digest(summaries)
        print(f"🤖 AI摘要生成完成: {len(digest_content)} 字符")
        
        # 创建HTML邮件
        html_content = self.create_html_email(digest_content, summaries)
        
        # 发送邮件
        success = self.send_email(recipient_email, html_content, summaries)
        
        if success:
            print(f"✅ 邮件发送成功！收件人: {recipient_email}")
        else:
            print(f"❌ 邮件发送失败！收件人: {recipient_email}")
        
        return success
    
    def test_email_service(self, recipient_email: str) -> bool:
        """测试邮件服务"""
        print(f"🧪 测试邮件服务，发送测试邮件到 {recipient_email}...")
        
        # 创建测试邮件内容
        today = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
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
        <h2>🧪 PodLens 邮件服务测试</h2>
        <p>这是一封测试邮件，用于验证邮件服务配置。</p>
        <p><strong>测试时间:</strong> {today}</p>
        <p>✅ 如果您收到此邮件，说明邮件服务已正常工作！</p>
    </div>
</body>
</html>
"""
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🧪 PodLens邮件服务测试 - {today}"
            msg['From'] = PODLENS_EMAIL
            msg['To'] = recipient_email
            
            html_part = MIMEText(test_html, 'html', 'utf-8')
            msg.attach(html_part)
            
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(PODLENS_EMAIL, PODLENS_APP_PASSWORD)
                server.send_message(msg)
            
            print(f"✅ 测试邮件发送成功！")
            return True
            
        except Exception as e:
            print(f"❌ 测试邮件发送失败: {e}")
            return False

class CronManager:
    """Cron任务管理器"""
    
    def __init__(self):
        self.current_user = os.getenv('USER', 'user')
        self.project_path = Path.cwd().absolute()
    
    def setup_email_cron(self, notification_times: List[str]) -> bool:
        """设置邮件通知的cron任务"""
        try:
            # 移除现有的PodLens邮件任务
            self.remove_email_cron()
            
            if not notification_times:
                print("ℹ️  没有设置通知时间，跳过cron配置")
                return True
            
            # 动态获取当前Python路径
            import sys
            python_path = sys.executable
            
            # 为每个时间创建cron任务
            cron_commands = []
            for time_str in notification_times:
                try:
                    hour, minute = time_str.split(':')
                    hour = int(hour)
                    minute = int(minute)
                    
                    cron_command = f"{minute} {hour} * * * cd \"{self.project_path}\" && {python_path} -c \"from podlens.email_service_ch import send_daily_digest_from_config; send_daily_digest_from_config()\" >> .podlens/podlens_email.log 2>&1"
                    cron_commands.append(cron_command)
                    
                except ValueError:
                    print(f"⚠️  时间格式错误: {time_str}，跳过")
                    continue
            
            if not cron_commands:
                print("❌ 没有有效的通知时间")
                return False
            
            # 添加到crontab
            existing_crontab = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            existing_lines = existing_crontab.stdout.split('\n') if existing_crontab.returncode == 0 else []
            
            # 过滤掉空行
            existing_lines = [line for line in existing_lines if line.strip()]
            
            # 添加新任务
            all_lines = existing_lines + cron_commands
            
            # 写入新的crontab
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
            process.communicate('\n'.join(all_lines) + '\n')
            
            if process.returncode == 0:
                print(f"✅ 成功配置 {len(cron_commands)} 个邮件通知任务")
                for i, time_str in enumerate(notification_times):
                    print(f"   📅 每日 {time_str} 发送邮件")
                return True
            else:
                print("❌ Cron任务配置失败")
                return False
                
        except Exception as e:
            print(f"❌ Cron配置错误: {e}")
            return False
    
    def remove_email_cron(self) -> bool:
        """移除邮件相关的cron任务"""
        try:
            existing_crontab = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if existing_crontab.returncode != 0:
                return True  # 没有现有的crontab
            
            lines = existing_crontab.stdout.split('\n')
            # 过滤掉PodLens邮件相关的任务
            filtered_lines = [line for line in lines if 'podlens.email_service' not in line and 'email_service_ch' not in line and '.podlens/podlens_email.log' not in line and 'podlens_email.log' not in line]
            
            # 如果有变化，更新crontab
            if len(filtered_lines) != len(lines):
                process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
                process.communicate('\n'.join(filtered_lines) + '\n')
                return process.returncode == 0
            
            return True
            
        except Exception as e:
            print(f"❌ 移除cron任务失败: {e}")
            return False
    
    def check_email_cron_status(self) -> List[str]:
        """检查当前的邮件cron任务状态"""
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode != 0:
                return []
            
            lines = result.stdout.split('\n')
            email_crons = [line for line in lines if 'podlens.email_service' in line or 'email_service_ch' in line]
            return email_crons
            
        except Exception as e:
            print(f"❌ 检查cron状态失败: {e}")
            return []

# 全局邮件服务实例
email_service = EmailService()
cron_manager = CronManager()

def send_daily_digest_from_config():
    """从配置文件读取设置并发送每日摘要（供cron调用）"""
    settings = email_service.load_email_settings()
    if settings['email_function'] and settings['user_email']:
        email_service.send_daily_digest(settings['user_email'])
    else:
        print("ℹ️  邮件功能未启用或邮箱未配置")