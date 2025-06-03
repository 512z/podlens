# 🎧 PodLens - Intelligent Podcast & Youtube Transcription & Summary Tool

🧠 For knowledge-seekers who want to learn from audio content more effectively.

A fast & cost-free & powerful tool that:
- 🎙️ transcribes audio content from Apple Podcast and YouTube platforms
- 📝 summarizes
- 📊 visualizes
- 🌏 features bilingual Chinese/English interface

[中文版 README](README_zh.md) | **English README**

![Terminal Demo](demo/terminal.gif)


## ✨ Key Features

- 🎯 **Smart Transcription**: Multiple transcription methods (Groq API ultra-fast transcription, MLX Whisper local transcription)
- 🍎 **Apple Podcast**: Search podcast channels, download episodes, automatic transcription
- 🎥 **YouTube Support**: Extract transcripts, audio download fallback for transcription
- 🤖 **AI Summary**: Generate intelligent summaries using Gemini AI
- 🎨 **Interactive Visualization**: Transform content into beautiful, interactive HTML stories with data visualizations
- 🌍 **Bilingual**: Supports both Chinese and English output
- 📁 **File Management**: Automatically organize output files
- 🔄 **Language Switching**: Choose your preferred interface language

## 📝 Note:

*For audio files larger than 25MB after compression, the transcription will be done by MLX Whisper, which is local for Mac users, and not yet available for Windows users. Windows user can still use Groq API for transcription for files smaller than 25MB.*

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

## 🚀 Usage

### English Version
```bash
podlens
```

### Chinese Version  
```bash
podlens-zh
# or
podlens-ch
```

### Interactive Interface:
```
🎧🎥 Podcast Transcription & Summary Tool (English Version)
==================================================
Supports Apple Podcast and YouTube platforms
==================================================

📡 Please select information source:
1. Apple Podcast
2. YouTube  
0. Exit

Please enter your choice (1/2/0): 
```

## 🎯 Available Commands

| Command | Description |
|---------|-------------|
| `podlens` | Launch default interface (English) |
| `podlens-en` | Launch English interface |
| `podlens-zh` or `podlens-ch` | Launch Chinese interface |


## 📋 Workflow Example

### Apple Podcast Workflow
1. **Search Channel**: Enter podcast name (e.g., "Lex Fridman")
2. **Select Channel**: Choose from search results
3. **Browse Episodes**: View recent episodes
4. **Download & Transcribe**: Select episodes for processing
5. **Generate Summary**: Optional AI-powered summary
6. **Create Visualization**: Generate interactive HTML stories with modern UI and data visualizations

### YouTube Workflow  
1. **Input Source**: 
   - Channel name (e.g., "Lex Fridman")
   - Direct video URL
   - Transcript text file
2. **Select Episodes**: Choose videos to process
3. **Extract Content**: Automatic transcript extraction
4. **Generate Summary**: AI-powered analysis
5. **Create Visualization**: Generate interactive HTML stories with modern UI and data visualizations

## 📁 Output Structure

```
your-project/
├── outputs/           # Transcripts, summaries, and interactive visualizations
│   ├── Transcript_*.md      # Original transcriptions
│   ├── Summary_*.md         # AI-generated summaries  
│   └── Visual_*.html        # Interactive HTML stories
├── media/            # Downloaded audio files (temporary)
└── .env             # Your API keys
```

## 🛠️ Advanced Features

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


