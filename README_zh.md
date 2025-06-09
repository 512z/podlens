# 🎧 PodLens - 免费Podwise: 智能播客&youtube转录与学习工具

🧠 播客透镜, 为知识探索者打造, 更有效地从音频内容中学习。

🤖 现已支持24x7自动化服务 & 📧 智能邮件摘要 & 📒 同步到 Notion！

一个快速、免费的AI驱动工具，可以:
- 🎙️ 转录来自 Apple Podcast 和 YouTube 平台的音频内容
- 📝 生成摘要
- 📊 可视化展示
- 🌏 支持中文/英文双语界面

**中文版 README** | [English README](README.md)

![终端演示](demo/terminal_ch.gif)


## ✨ 主要功能

- 🤖 **24x7智能自动化**: 一键设置即可忘记，自动监控您喜爱的播客和YouTube频道，每小时自动处理新发布的节目 - **autopod**
- 🎯 **交互式手动模式**: 按需处理功能，通过直观的命令行界面即时转录和分析特定节目 - **pod**
- 📧 **智能邮件摘要**: 每日自动邮件报告，包含AI生成的洞察和处理内容概览
- 📒 **同步到 Notion**: 自动同步处理内容到 Notion 中，使用您自己的 Notion 页面和 token
- ⚡ **超高速智能转录**: 多种AI驱动方法（Groq API高速处理，MLX Whisper处理大文件）配备智能回退机制
- 🍎 **Apple Podcast & YouTube集成**: 无缝支持两大主流平台，智能检测新节目
- 🧠 **AI驱动的深度分析**: 使用Google Gemini AI生成智能摘要和洞察，结构化主题分析
- 🎨 **交互式视觉故事**: 将内容转化为精美的响应式HTML可视化页面，包含数据图表和现代UI设计
- 🌍 **双语支持**: 全中文/英文界面，智能语言检测和切换
- 🗂️ **智能文件组织**: 基于节目的文件夹结构，自动文件管理和重复检测

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

**Notion API (Sync to Notion):**

  - 访问: https://www.notion.so/my-integrations
  - 点击 **"+ New integration"**
  - 填写信息:
    - **Name**: `Markdown Uploader` (or any name)
    - **Workspace**: Select your workspace
    - **Type**: Internal integration
  - 点击 **"Submit"**
  - **获取 Notion token**: 复制生成的 **"Internal Integration Secret"** (以 `secret_` 开头)
  - **获取 Notion page id**: 复制 Notion 页面 URL 中 `pagename-` 后的页面 ID: https://www.notion.so/pagename-<your-page-id>


## 🚀 使用方法

### 交互模式
```bash
# 英文版
podlens

# 中文版  
pod
```

### 自动化服务（NEW！）
```bash
# 英文版24x7自动化服务
autopodlens

# 中文版24x7自动化服务  
autopod

# 检查自动化状态
autopodlens --status  # 英文版
autopod --status      # 中文版
```

### 邮件服务（NEW！）

```bash
# 邮件通知设置
autopod --email your@email.com --time 08:00,18:00

# 邮件时间设置
autopod(or autopodlens) --time 08:00,18:00

# 检查邮件服务状态  
autopod --email-status

# 同步邮件配置
autopod --email-sync

# 禁用邮件服务
autopod --email-disable
```

### Notion 同步服务（NEW！）
```bash
# Notion token 和 page id 设置
autopod(or autopodlens) --notiontoken <your_notion_token> --notionpage <your_notion_page_id>

# 同步到 Notion
autopod(or autopodlens) --notion
```

**您也可以在`.podlens/setting`文件中更改邮件服务 & Notion 同步设置，然后使用'--email-sync'同步设置。**

### 配置文件（自动生成）
- `my_pod.md` - 配置监控的播客（自动创建）
- `my_tube.md` - 配置监控的YouTube频道（自动创建）
- `.podlens/setting` - 自动化频率和监控设置（自动创建）
- `.podlens/status.json` - 服务状态和已处理剧集跟踪（自动创建）

首次运行自动化服务时，PodLens将自动创建配置文件：

**`.podlens/setting`**（自动创建）：
```markdown
# PodLens 自动化设置
# 运行频率（小时），支持小数，如0.5表示30分钟
run_frequency = 1.0

# 是否监控Apple Podcast (my_pod.md)
monitor_podcast = true

# 是否监控YouTube (my_tube.md)
monitor_youtube = true

# 邮件通知设置
email_function = true
user_email = example@gmail.com
notification_times = 08:00,18:00
```

**`my_pod.md`**（自动生成示例）：
```markdown
# PodLens播客订阅列表
# 此文件管理您想要自动处理的播客频道。

## 使用方法
# - 每行一个播客名称
# - 支持Apple Podcast上可搜索到的播客名称
# - 以`#`开头的行为注释，将被忽略
# - 空行也将被忽略

## 示例播客
thoughts on the market
# 或：thoughts on the market - morgan stanley

## 商业播客


## 科技播客
```

**`my_tube.md`**（自动生成示例）：
```markdown  
# YouTube频道订阅列表

# 此文件管理您想要自动处理的YouTube频道。

## 使用方法
# - 每行一个频道名称（无需@符号）
# - 频道名称是YouTube URL中@后的部分
# - 示例：https://www.youtube.com/@Bloomberg_Live/videos → 填入Bloomberg_Live
# - 以`#`开头的行为注释，将被忽略
# - 空行也将被忽略

## 示例频道
Bloomberg_Live


## 商业频道


## 科技频道

```

只需编辑这些文件来添加或删除您喜欢的播客和YouTube频道。

### 交互界面示例:

```
🎧🎥 媒体转录与摘要工具
==================================================
支持 Apple Podcast 和 YouTube 平台
==================================================

📡 请选择信息来源：
1. Apple Podcast
2. YouTube
0. 退出

请输入您的选择 (1/2/0): 1

🎧 您选择了 Apple Podcast
请输入您要搜索的播客频道名称: thoughts on the market

📥 正在下载: 剧集标题...
⚡️ 极速转录...
🧠 开始总结...
🎨 可视化故事生成?(y/n): 
```

### 自动化服务示例
```bash
# 启动自动化服务
$ autopod
🤖 启动 PodLens 24x7 智能自动化服务

🎧 已创建播客配置文件: my_pod.md
📺 已创建YouTube频道配置文件: my_tube.md
⏰ 运行频率: 每小时
🎧 监控播客数量: 1
📺 监控YouTube频道数量: 1
按 Ctrl+Z 停止服务

⏰ 开始每小时检查
🔍 检查播客: thoughts on the market
📥 处理新剧集: Standing by Our Outlook...
✅ thoughts on the market 处理完成
🔍 检查YouTube频道: @Bloomberg_Live
📥 处理新视频: Jennifer Doudna on Future of Gene Editing \u0026 I...
✅ @Bloomberg_Live 处理完成
✅ 检查完成 - 播客: 1/1, YouTube: 1/1
```

### Notion 同步服务示例
```bash
📒 正在写入您的notion
✅ Jennifer_Doudna_on_Future_of_G...: 100%|███████████████████████████████████| 2/2 [00:15<00:00,  7.52s/文件]
✅ 导入成功!
```

## 📋 工作流程示例

### Apple Podcast 工作流程

1.  **搜索频道**: 输入播客名称 (例如："thoughts on the market")
2.  **选择频道**: 从搜索结果中选择
3.  **浏览单集**: 查看最近的单集
4.  **选择剧集**: 选择要处理的剧集
5.  **自动处理**: 自动下载、转录和AI摘要
6.  **创建可视化**: 可选的交互式HTML故事，具有现代UI和数据可视化

### YouTube 工作流程

1.  **输入来源**:
      - 频道名称 (例如："Bloomberg_Live")
      - 直接视频 URL
      - 字幕文本文件
2.  **选择剧集**: 选择要处理的视频
3.  **自动处理**: 自动提取字幕和AI摘要
4.  **创建可视化**: 可选的交互式HTML故事，具有现代UI和数据可视化

### 自动化工作流程（NEW！）
1.  **启动服务**: 运行`autopodlens`（英文版）或`autopod`（中文版）- 配置文件自动创建
2.  **配置**: 编辑自动生成的`my_pod.md`和`my_tube.md`，添加您的订阅
3.  **24x7监控**: 服务每小时检查新内容
4.  **自动处理**: 新剧集自动转录和摘要
5.  **智能去重**: 已处理的内容自动跳过

## 📁 输出结构

```
your-project/
├── outputs/           # 基于剧集的组织内容
│   └── [频道名称]/
│       └── [日期]/
│           └── [剧集标题]/
│               ├── audio.mp3        # 下载的音频文件（处理后删除）
│               ├── Transcript_[详情].md    # 转录稿
│               ├── Summary_[详情].md       # AI生成的摘要
│               └── Visual_[详情].html      # 交互式可视化
├── .podlens/         # 自动化配置
│   ├── setting       # 服务频率和监控设置
│   └── status.json   # 已处理剧集跟踪
├── my_pod.md         # 监控播客配置
├── my_tube.md        # 监控YouTube频道配置
└── .env              # 您的API密钥
```

## 🛠️ 高级功能

### 剧集式文件组织
- **专用文件夹**: 每个剧集都有自己的文件夹，便于清晰组织
- **一致结构**: 所有相关文件（音频、转录、摘要、可视化）都在一个地方

### 24x7自动化服务  
- **智能监控**: 通过`my_pod.md`和`my_tube.md`配置文件自动跟踪播客和YouTube频道
- **智能去重**: 基于`.podlens/status.json`跟踪，已处理的剧集自动跳过
- **每小时处理**: 服务每小时检查新内容并自动处理
- **频道格式**: YouTube频道使用简单名称（如`Bloomberg_Live`对应`@Bloomberg_Live`）
- **剧集组织**: 基于日期的文件夹结构，详细文件命名便于导航
- **状态跟踪**: 使用`--status`标志查看服务状态和处理历史

### 智能邮件摘要服务
- **每日摘要**: 自动邮件报告，包含AI生成的洞察和处理内容概览
- **灵活调度**: 多个每日通知时间（例如：08:00, 18:00）  
- **丰富HTML格式**: 美观的邮件布局，包含频道分组和关键洞察
- **智能内容**: AI驱动的每日摘要，突出重要信息
- **轻松管理**: 简单的设置、状态检查和配置命令

![PodLens Email Example](demo/email_ch.png)

### Notion 同步服务
- **自动同步**: 自动同步处理内容到 Notion 中，使用您自己的 Notion 页面和 token
- **智能去重**: 已处理的内容自动跳过

### 智能转录逻辑

  - **小文件 (\<25MB)**: Groq API 超快速转录
  - **大文件 (\>25MB)**: 自动压缩 + 回退到 MLX Whisper
  - **回退链**: Groq → MLX Whisper → 错误处理

[智能转录逻辑](demo/Transcript_en.md)

### AI 摘要功能

  - **顺序分析**: 按顺序生成主题大纲
  - **关键见解**: 重要观点和引言
  - **技术术语**: 专业术语解释
  - **批判性思维**: 第一性原理分析

![AI 摘要示例](demo/summary_ch.png)
[查看示例摘要](demo/Summary_ch.md)


### 交互式可视化功能

  - **现代网页设计**: 使用 Tailwind CSS 构建美观、响应式的 HTML 页面
  - **数据可视化**: 自动为数值内容（百分比、指标、比较）生成图表
  - **交互元素**: 由 Alpine.js 驱动的平滑动画、可折叠区域和实时搜索
  - **专业风格**: 毛玻璃效果、渐变强调色和 Apple 风格的简洁设计
  - **内容智能**: AI 自动从转录稿和摘要中识别关键数据点并进行可视化
  - **双输入支持**: 可从转录稿或摘要生成可视化内容


![可视化演示](demo/visual_demo_ch.png)
[查看示例可视化](demo/Visual_ch.html)

## 🙏 致谢

本项目的开发离不开众多开源项目、技术和社区的支持。我们向以下为 PodLens 做出贡献的各方表示衷心的感谢：

### 核心 AI 技术

  - **[OpenAI Whisper](https://github.com/openai/whisper)** - 革命性的自动语音识别模型，为音频转录奠定了基础
  - **[MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper)** - Apple 优化的 MLX 实现，可在 Apple Silicon 上实现快速本地转录
  - **[Groq](https://groq.com/)** - 超快速 AI 推理平台，通过 API 提供闪电般的 Whisper 转录速度
  - **[Google Gemini](https://ai.google.dev/)** - 驱动我们智能摘要功能的先进 AI 模型

### 媒体处理与提取

  - **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - 功能强大的 YouTube 视频/音频下载器，youtube-dl 的继任者
  - **[youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)** - 用于提取 YouTube 视频字幕的优雅 Python 库

