# 🎧 PodLens - 智能播客&youtube转录与学习工具

```

██████╗  ██████╗ ██████╗ ██╗     ███████╗███╗   ██╗███████╗
██╔══██╗██╔═══██╗██╔══██╗██║     ██╔════╝████╗  ██║██╔════╝
██████╔╝██║   ██║██║  ██║██║     █████╗  ██╔██╗ ██║███████╗
██╔═══╝ ██║   ██║██║  ██║██║     ██╔══╝  ██║╚██╗██║╚════██║
██║     ╚██████╔╝██████╔╝███████╗███████╗██║ ╚████║███████║
╚═╝      ╚═════╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝

````

**中文版 README** | [English README](README.md)

专为希望更有效地从音频内容中学习的知识探索者打造。

一款快速,免费且功能强大的播客转录和摘要工具，支持 Apple Podcast 和 YouTube 两大平台，具有中英双语界面，并集成了多种 AI 技术，可实现高质量的音频转录和智能摘要。

## ✨ 主要功能

- 🎯 **智能转录**: 多种转录方式（Groq API 超快速转录，MLX Whisper 本地转录）
- 🍎 **Apple Podcast**: 搜索播客频道，下载单集，自动转录
- 🎥 **YouTube 支持**: 提取字幕，音频下载后备转录
- 🤖 **AI 摘要**: 使用 Gemini AI 生成智能摘要
- 🎨 **交互式可视化**: 将内容转化为美观、交互式的 HTML 故事，并包含数据可视化
- 🌍 **双语支持**: 支持中文和英文输出
- 📁 **文件管理**: 自动整理输出文件
- 🔄 **语言切换**: 选择您偏好的界面语言

## 📝 注意：

*对于压缩后大于 25MB 的音频文件，将由 MLX Whisper 进行转录。该功能目前仅适用于 Mac 用户本地转录，Windows 用户尚无法使用。Windows 用户仍可对小于 25MB 的文件使用 Groq API 进行转录。*

## 📦 安装

```bash
pip install podlens
````

## 🔧 配置

### 1\. 创建 .env 配置文件

在您的工作目录中创建一个 `.env` 文件：

```bash
# .env 文件内容
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 2\. 获取 API 密钥

**Groq API (推荐 - 超快速转录):**

  - 访问: https://console.groq.com/
  - 注册并获取免费 API 密钥
  - 优点: 极速 Whisper large-V3 处理，免费额度充足

**Gemini API (AI 摘要):**

  - 访问: https://aistudio.google.com/app/apikey
  - 获取免费 API 密钥
  - 用于生成智能摘要

## 🚀 使用方法

### 英文版

```bash
podlens
```

### 中文版

```bash
podlens-zh
# 或
podlens-ch
```

### 交互界面示例:

```
🎧🎥 播客转录与摘要工具 (中文版)
==================================================
支持 Apple Podcast 和 YouTube 平台
==================================================

📡 请选择信息来源:
1. Apple Podcast
2. YouTube
0. 退出

请输入您的选择 (1/2/0):
```

## 🎯 可用命令

| 命令 | 描述 |
|---------|-------------|
| `podlens` | 启动默认界面 (英文) |
| `podlens-en` | 启动英文界面 |
| `podlens-zh` 或 `podlens-ch` | 启动中文界面 |

## 📋 工作流程示例

### Apple Podcast 工作流程

1.  **搜索频道**: 输入播客名称 (例如："Lex Fridman")
2.  **选择频道**: 从搜索结果中选择
3.  **浏览单集**: 查看最近的单集
4.  **下载与转录**: 选择要处理的单集
5.  **生成摘要**: 可选的 AI 驱动摘要
6.  **创建可视化**: 生成具有现代用户界面和数据可视化的交互式 HTML 故事

### YouTube 工作流程

1.  **输入来源**:
      - 频道名称 (例如："Lex Fridman")
      - 直接视频 URL
      - 字幕文本文件
2.  **选择单集**: 选择要处理的视频
3.  **提取内容**: 自动提取字幕
4.  **生成摘要**: AI 驱动分析
5.  **创建可视化**: 生成具有现代用户界面和数据可视化的交互式 HTML 故事

## 📁 输出结构

```
your-project/
├── outputs/           # 转录稿、摘要和交互式可视化文件
│   ├── Transcript_*.md      # 原始转录稿
│   ├── Summary_*.md         # AI 生成的摘要
│   └── Visual_*.html        # 交互式 HTML 故事
├── media/            # 下载的音频文件 (临时)
└── .env             # 您的 API 密钥
```

## 🛠️ 高级功能

### 智能转录逻辑

  - **小文件 (\<25MB)**: Groq API 超快速转录
  - **大文件 (\>25MB)**: 自动压缩 + 回退到 MLX Whisper
  - **回退链**: Groq → MLX Whisper → 错误处理

### AI 摘要功能

  - **顺序分析**: 按顺序生成主题大纲
  - **关键见解**: 重要观点和引言
  - **技术术语**: 专业术语解释
  - **批判性思维**: 第一性原理分析

### 交互式可视化功能

  - **现代网页设计**: 使用 Tailwind CSS 构建美观、响应式的 HTML 页面
  - **数据可视化**: 自动为数值内容（百分比、指标、比较）生成图表
  - **交互元素**: 由 Alpine.js 驱动的平滑动画、可折叠区域和实时搜索
  - **专业风格**: 毛玻璃效果、渐变强调色和 Apple 风格的简洁设计
  - **内容智能**: AI 自动从转录稿和摘要中识别关键数据点并进行可视化
  - **双输入支持**: 可从转录稿或摘要生成可视化内容


## 🙏 致谢

本项目的成功离不开众多开源项目、技术和社区的支持。我们向以下为 PodLens 做出贡献的各方表示衷心的感谢：

### 核心 AI 技术

  - **[OpenAI Whisper](https://github.com/openai/whisper)** - 革命性的自动语音识别模型，为音频转录奠定了基础
  - **[MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper)** - Apple 优化的 MLX 实现，可在 Apple Silicon 上实现快速本地转录
  - **[Groq](https://groq.com/)** - 超快速 AI 推理平台，通过 API 提供闪电般的 Whisper 转录速度
  - **[Google Gemini](https://ai.google.dev/)** - 驱动我们智能摘要功能的先进 AI 模型

### 媒体处理与提取

  - **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - 功能强大的 YouTube 视频/音频下载器，youtube-dl 的继任者
  - **[youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)** - 用于提取 YouTube 视频字幕的优雅 Python 库

