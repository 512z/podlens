# 🎧 PodLens - Free Podwise: Podcast & Youtube Transcription & Summary AI Agent

🧠 For knowledge-seekers who want to learn from audio content more effectively.

🤖 Now with 24x7 automation service & 📧 smart email digest & 📒 sync to Notion!

A fast & cost-free & AI-powered tool that:
- 🎙️ transcribes audio content from Apple Podcast and YouTube platforms
- 📝 summarizes
- 📊 visualizes
- 🌏 features bilingual Chinese/English interface

[中文版 README](README_zh.md) | **English README**

![Terminal Demo](demo/terminal.gif)


## ✨ Key Features

- 🤖 **24x7 Intelligent Automation**: Set-and-forget service monitors your favorite podcasts and YouTube channels, automatically processing new episodes hourly - **autopodlens**
- 📧 **Smart Email Digest**: Daily automated email summaries with AI-generated insights and processed content overview
- 📝 **Sync to Notion**: Automatically sync processed content to Notion with your own Notion page and token
- 🎯 **Interactive Manual Mode**: On-demand processing with intuitive command-line interface for immediate transcription and analysis of specific episodes - **podlens** 
- ⚡ **Ultra-Fast Smart Transcription**: Multiple AI-powered methods (Groq API for speed, MLX Whisper for large files) with intelligent fallback chain
- 🍎 **Apple Podcast & YouTube Integration**: Seamless content extraction from both major platforms with smart episode detection
- 🧠 **AI-Powered Analysis**: Generate intelligent summaries and insights using Google Gemini AI with structured topic analysis
- 🎨 **Interactive Visual Stories**: Transform content into beautiful, responsive HTML visualizations with data charts and modern UI
- 🌍 **Bilingual Support**: Full Chinese/English interface with smart language detection and switching
- 🗂️ **Smart Organization**: Episode-based folder structure with automatic file management and duplicate detection


## 📦 Installation

```bash
pip install podlens
```

## 🔧 Configuration

### 1. Create .env Configuration File

Create a `.env` file in your working directory:

```bash
# .env file content
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 2. Get API Keys

**Groq API (Recommended - Ultra-fast transcription):**
- Visit: https://console.groq.com/
- Register and get free API key
- Benefits: Extremely fast Whisper large-V3 processing, generous free quota

**Gemini API (AI Summary):**
- Visit: https://aistudio.google.com/app/apikey
- Get free API key
- Used for generating intelligent summaries

**Notion API (Sync to Notion):**
- Visit: https://www.notion.so/my-integrations
- Click **"+ New integration"**
- Fill in the information:
   - **Name**: `Markdown Uploader` (or any name)
   - **Workspace**: Select your workspace
   - **Type**: Internal integration
- Click **"Submit"**
- **Get Notion token**: Copy the generated **"Internal Integration Secret"** (starts with `secret_`)
- **Get Notion page id**: Copy the page id after `pagename-` in the URL of your Notion page: https://www.notion.so/pagename-<your-page-id>

## 🚀 Usage

### Interactive Mode
```bash
# English version
podlens

# Chinese version  
pod
```

### Automation Service (NEW!)
```bash
# English version 24x7 automation service
autopodlens

# Chinese version 24x7 automation service  
autopod

# Check automation status
autopodlens --status  # English version
autopod --status      # Chinese version
```

### Email Service (NEW!)
```bash
# Email notification setup
autopod(or autopodlens) --email your@email.com --time 08:00,18:00

# Email time setup
autopod(or autopodlens) --time 08:00,18:00

# Check email service status  
autopod(or autopodlens) --email-status

# Sync email configuration
autopod(or autopodlens) --email-sync

# Disable email service
autopod(or autopodlens) --email-disable
```

### Notion Sync Service (NEW!)
```bash
# Notion token and page id setup
autopod(or autopodlens) --notiontoken <your_notion_token> --notionpage <your_notion_page_id>

# Upload to Notion
autopod(or autopodlens) --notion
```

**You can also change the email service & Notion sync settings in the `.podlens/setting` file, then use '--email-sync' to sync the settings.**

### Configuration Files (Auto-Generated)

- `my_pod.md` - Configure monitored podcasts (created automatically)
- `my_tube.md` - Configure monitored YouTube channels (created automatically)
- `.podlens/setting` - Automation frequency and monitoring settings (created automatically)
- `.podlens/status.json` - Service status and processed episodes tracking (created automatically)

When you first run the automation service, PodLens will automatically create configuration files:

**`.podlens/setting`** - Automation frequency and monitoring settings (created automatically)

```markdown
# PodLens Automation Settings
# Run frequency (hours), supports decimals, e.g. 0.5 means every 30 minutes
run_frequency = 1.0

# Monitor Apple Podcast (my_pod.md)
monitor_podcast = true

# Monitor YouTube (my_tube.md)
monitor_youtube = true

# Email notification settings
email_function = true
user_email = example@gmail.com
notification_times = 08:00,18:00
```

**`my_pod.md`** (auto-generated with examples):
```markdown
# PodLens Podcast Subscription List
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
```

**`my_tube.md`** (auto-generated with examples):
```markdown  
# YouTube Channel Subscription List

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

```

Simply edit these files to add or remove your preferred podcasts and YouTube channels.

### Interactive Interface:
```
🎧🎥 Media Transcription & Summary Tool
==================================================
Supports Apple Podcast and YouTube platforms
==================================================

📡 Please select information source:
1. Apple Podcast
2. YouTube  
0. Exit

Please enter your choice (1/2/0): 1

🎧 You selected Apple Podcast
Please enter the podcast channel name: thoughts on the market

📥 Downloading: Episode Title...
⚡️ Ultra-fast transcription...
🧠 Summarizing...
🎨 Visual Story Generation?(y/n): 
```

### Automation Service Example
```bash
# Start the automation service
$ autopodlens
🤖 Starting PodLens 24x7 Intelligent Automation Service

⏰ Running frequency: hourly
🎧 Monitoring podcasts: 1
📺 Monitoring YouTube channels: 1
Press Ctrl+Z to stop service

⏰ Starting hourly check
🔍 Checking podcast: thoughts on the market
📥 Processing new episode: Standing by Our Outlook...
✅ thoughts on the market processing complete
🔍 Checking YouTube channel: @Bloomberg_Live
📥 Processing new video: Jennifer Doudna on Future of Gene Editing \u0026 I...
✅ @Bloomberg_Live processing complete
✅ Check complete - Podcasts: 1/1, YouTube: 1/1
```

### Notion Sync Service Example
```bash
📒 Writing to your Notion...
✅ Jennifer_Doudna_on_Future_of_G...: 100%|██████████████████████████████████| 2/2 [00:29<00:00, 14.52s/files]
✅ Import successful!
```

## 📋 Workflow Example

### Apple Podcast Workflow
1. **Search Channel**: Enter podcast name (e.g., "thoughts on the market")
2. **Select Channel**: Choose from search results  
3. **Browse Episodes**: View recent episodes
4. **Select Episodes**: Choose episodes for processing
5. **Auto Processing**: Automatic download, transcription and AI summary
6. **Create Visualization**: Optional interactive HTML stories with modern UI and data visualizations

### YouTube Workflow  
1. **Input Source**: 
   - Channel name (e.g., "Bloomberg_Live")
   - Direct video URL
   - Transcript text file
2. **Select Episodes**: Choose videos to process
3. **Auto Processing**: Automatic transcript extraction and AI summary
4. **Create Visualization**: Optional interactive HTML stories with modern UI and data visualizations

### Automation Workflow (NEW!)
1. **Launch Service**: Run `autopodlens` (English) or `autopod` (Chinese) - configuration files auto-created
2. **Configure**: Edit the auto-generated `my_pod.md` and `my_tube.md` with your subscriptions
3. **24x7 Monitoring**: Service checks for new content every hour
4. **Auto Processing**: New episodes automatically transcribed and summarized
5. **Smart Deduplication**: Already processed content is skipped automatically

## 📁 Output Structure

```
your-project/
├── outputs/           # Episode-based organized content
│   └── [Channel Name]/
│       └── [Date]/
│           └── [Episode Title]/
│               ├── audio.mp3        # Downloaded audio file (will be deleted after processing)
│               ├── Transcript_[Details].md    # Transcription
│               ├── Summary_[Details].md       # AI-generated summary
│               └── Visual_[Details].html      # Interactive visualization
├── .podlens/         # Automation configuration
│   ├── setting       # Service frequency and monitoring settings
│   └── status.json   # Processed episodes tracking
├── my_pod.md         # Monitored podcasts configuration
├── my_tube.md        # Monitored YouTube channels configuration
└── .env              # Your API keys
```

## 🛠️ Advanced Features

### Episode-based File Organization
- **Dedicated Folders**: Each episode gets its own folder for clean organization
- **Consistent Structure**: All related files (audio, transcript, summary, visualization) in one place

### 24x7 Automation Service  
- **Smart Monitoring**: Automatic tracking of podcasts and YouTube channels via `my_pod.md` and `my_tube.md` configuration files
- **Intelligent Deduplication**: Already processed episodes are automatically skipped based on `.podlens/status.json` tracking
- **Hourly Processing**: Service checks for new content every hour and processes automatically
- **Channel Format**: YouTube channels use simple names (e.g., `Bloomberg_Live` for `@Bloomberg_Live`)
- **Episode Organization**: Date-based folder structure with detailed file naming for easy navigation
- **Status Tracking**: View service status and processing history with `--status` flag

### Smart Email Digest Service
- **Daily Summaries**: Automated email reports with AI-generated insights
- **Flexible Scheduling**: Multiple daily notification times (e.g., 08:00, 18:00)  
- **Rich HTML Format**: Beautiful email layout with channel groupings and key insights
- **Intelligent Content**: AI-powered daily digest highlighting important information
- **Easy Management**: Simple commands for setup, status check, and configuration

### Notion Sync Service
- **Automatic Sync**: Automatically sync processed content to Notion with your own Notion page and token
- **Smart Deduplication**: Already processed episodes are automatically skipped based on `.podlens/status.json` tracking

![PodLens Email Example](demo/email_en.jpg)

### Smart Transcription Logic
- **Small files (<25MB)**: Groq API ultra-fast transcription
- **Large files (>25MB)**: Automatic compression + fallback to MLX Whisper
- **Fallback chain**: Groq → MLX Whisper → Error handling

[PodLens Transcription Example](demo/Transcript_en.md)

### AI Summary Features
- **Sequential analysis**: Topic outline in order
- **Key insights**: Important takeaways and quotes
- **Technical terms**: Jargon explanation
- **Critical thinking**: First-principles analysis

![PodLens Summary Example](demo/summary.png)
[View Example Summary](demo/Summary_en.md)

### Interactive Visualization Features
- **Modern Web Design**: Beautiful, responsive HTML pages using Tailwind CSS
- **Data Visualizations**: Automatic charts and graphs for numerical content (percentages, metrics, comparisons)
- **Interactive Elements**: Smooth animations, collapsible sections, and real-time search powered by Alpine.js
- **Professional Styling**: Glassmorphism effects, gradient accents, and Apple-inspired clean design
- **Content Intelligence**: AI automatically identifies and visualizes key data points from transcripts and summaries
- **Dual Input Support**: Generate visualizations from either transcripts or summaries


![PodLens Visual Story Example](demo/visual_demo.png)
[View Example Visual Story](demo/Visual_en.html)


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## 🙏 Acknowledgements

This project stands on the shoulders of giants. We are deeply grateful to the following open source projects, technologies, and communities that made PodLens possible:

### Core AI Technologies
- **[OpenAI Whisper](https://github.com/openai/whisper)** - The foundational automatic speech recognition model that revolutionized audio transcription
- **[MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper)** - Apple's MLX-optimized implementation enabling fast local transcription on Apple Silicon
- **[Groq](https://groq.com/)** - Ultra-fast AI inference platform providing lightning-speed Whisper transcription via API
- **[Google Gemini](https://ai.google.dev/)** - Advanced AI model powering our intelligent summarization features

### Media Processing & Extraction
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Powerful YouTube video/audio downloader, successor to youtube-dl
- **[youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)** - Elegant Python library for extracting YouTube video transcripts


---

**🌟 Star this repo if you find it helpful!** 


