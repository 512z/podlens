# PodLens API 使用指南

## 快速开始

### 1. 环境配置

在项目根目录创建 `.env` 文件：
```env
GROQ_API_KEY=your_groq_api_key      # 免费获取: https://console.groq.com/
GEMINI_API_KEY=your_gemini_api_key  # 免费获取: https://aistudio.google.com/app/apikey
```

### 2. 基本使用

```python
# 方式一：简单函数调用
from podlens import process_apple_podcast_auto

result = process_apple_podcast_auto("All-in")
print(f"转录成功: {result['transcripts_success']}")
```

```python
# 方式二：完整控制
from podlens import PodlensAutomation

automation = PodlensAutomation(language="ch")
result = automation.process_apple_podcast(
    podcast_name="All-in",
    enable_transcription=True,
    enable_summary=True,
    summary_language="ch"
)
```

## API 参考

### Apple Podcast 处理

```python
process_apple_podcast_auto(
    podcast_name: str,              # 播客名称
    num_episodes: int = 1,          # 获取剧集数量
    episode_index: int = 0,         # 处理第几集(0=最新)
    language: str = "ch",           # 界面语言 "ch"/"en"
    enable_transcription: bool = True,    # 启用转录
    enable_summary: bool = True,          # 启用摘要
    summary_language: str = "auto",       # 摘要语言 "ch"/"en"/"auto"
    enable_visualization: bool = False    # 启用可视化
)
```

### YouTube 处理

```python
process_youtube_auto(
    search_query: str,              # 搜索关键词
    num_videos: int = 1,            # 搜索结果数量
    video_index: int = 0,           # 处理第几个视频
    language: str = "ch",           # 界面语言
    **kwargs                        # 其他参数同上
)
```

### 高级用法

```python
from podlens import PodlensAutomation

automation = PodlensAutomation(language="ch")

# 批量处理
podcasts = ["All-in", "The Tim Ferriss Show"]
for podcast in podcasts:
    result = automation.process_apple_podcast(podcast)

# 处理特定剧集
result = automation.process_apple_podcast(
    podcast_name="All-in",
    num_episodes=10,              # 获取10期
    episode_indices=[0, 1, 2],    # 处理前3期
    enable_visualization=True
)
```

## 返回结果

```python
{
    "platform": "Apple Podcast",
    "podcast_name": "All-in",
    "channels_found": 1,          # 找到频道数
    "episodes_processed": 1,      # 处理剧集数
    "downloads_success": 1,       # 下载成功数
    "transcripts_success": 1,     # 转录成功数
    "summaries_success": 1,       # 摘要成功数
    "visualizations_success": 0,  # 可视化成功数
    "errors": [],                 # 错误列表
    "output_files": [             # 输出文件路径
        "outputs/Transcript_All-in_Episode.md",
        "outputs/Summary_All-in_Episode.md"
    ]
}
```

## 输出文件

- **转录文件**: `outputs/Transcript_*.md` - 完整音频转录
- **摘要文件**: `outputs/Summary_*.md` - AI生成的智能摘要  
- **可视化**: `outputs/Visual_*.html` - 交互式故事页面

## 常见用法

### 1. 处理单个播客最新一期
```python
from podlens import process_apple_podcast_auto
result = process_apple_podcast_auto("All-in")
```

### 2. 生成中文摘要
```python
result = process_apple_podcast_auto(
    "All-in",
    enable_summary=True,
    summary_language="ch"
)
```

### 3. 批量处理
```python
from podlens import PodlensAutomation
automation = PodlensAutomation()

podcasts = ["All-in", "Lex Fridman Podcast"]
for podcast in podcasts:
    result = automation.process_apple_podcast(podcast)
    print(f"{podcast}: 成功转录 {result['transcripts_success']} 期")
```

### 4. YouTube视频处理
```python
from podlens import process_youtube_auto
result = process_youtube_auto("Lex Fridman podcast 2024")
```

## 故障排除

| 错误信息 | 解决方案 |
|---------|---------|
| `❌ Gemini API不可用` | 检查 `.env` 中的 `GEMINI_API_KEY` |
| `❌ 未找到匹配的播客` | 确认播客名称拼写正确 |
| `❌ 下载失败` | 检查网络连接 |
| `❌ 转录失败` | 检查音频文件大小和格式 |

## 注意事项

1. **API配额**: Groq和Gemini都有免费配额，大量使用请注意限制
2. **存储空间**: 音频文件较大，确保有足够磁盘空间
3. **处理时间**: 转录和摘要需要时间，大文件请耐心等待
4. **网络要求**: 需要稳定网络连接下载音频文件

## 完整示例

```python
#!/usr/bin/env python3
from podlens import PodlensAutomation

# 创建自动化引擎
automation = PodlensAutomation(language="ch")

# 处理播客并生成完整输出
result = automation.process_apple_podcast(
    podcast_name="All-in",
    enable_transcription=True,
    enable_summary=True,
    summary_language="ch",
    enable_visualization=True
)

# 检查结果
if result['transcripts_success'] > 0:
    print("✅ 处理成功!")
    for file_path in result['output_files']:
        print(f"📁 {file_path}")
else:
    print("❌ 处理失败:", result['errors'])
``` 