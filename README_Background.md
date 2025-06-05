# PodLens 后台服务 / Background Service

## 🚀 快速开始 / Quick Start

### 安装和启动 / Install & Start
```bash
# 安装依赖
pip install schedule

# 启动后台服务
podlens-ch --background                    # 每小时自动运行
```

### 播客列表管理 / Podcast Management
```bash
podlens-ch --background --action list                    # 查看列表
podlens-ch --background --action add --podcast "All-in"  # 添加播客
podlens-ch --background --action remove --podcast "..."  # 删除播客
podlens-ch --background --action status                  # 查看状态
```

## 📝 播客列表文件 / Podcast List

系统自动创建 `.podlist` 文件，可直接编辑：
```
# PodLens 播客列表
All-in
The Tim Ferriss Show
Lex Fridman Podcast
```

## 🔄 工作原理 / How It Works

1. **每小时检查**: 自动检查每个播客的最新剧集
2. **智能对比**: 与本地记录对比，只处理新剧集
3. **单剧集处理**: 每次只获取和处理最新的一个剧集
4. **完整流程**: 搜索→下载→转录→摘要一条龙服务

## 📁 输出结构 / Output Structure

```
outputs/
├── podcast_name_episode_title.mp3         # 音频文件
├── podcast_name_episode_title_transcript.md  # 转录
├── podcast_name_episode_title_summary.md     # 摘要
└── logs/
    └── podlens.log                        # 处理日志
```

## ⚙️ 高级功能 / Advanced Features

### 实时列表修改 / Real-time List Updates
- 后台运行时可随时编辑 `.podlist` 文件
- 下次检查自动使用最新列表

### Python API
```python
from podlens import BackgroundService

service = BackgroundService(language="ch")
service.start_background_service()
```

### 状态监控 / Monitoring
```bash
tail -f logs/podlens.log                    # 查看日志
cat .podcast_progress.json                  # 查看各播客进度
```

## 🎯 主要特性 / Key Features

- ✅ **每小时检查**: 及时获取最新内容
- ✅ **智能对比**: 自动跳过已处理剧集
- ✅ **单剧集处理**: 专注最新内容，避免重复
- ✅ **完整流程**: 从搜索到摘要全自动
- ✅ **实时管理**: 随时修改播客列表

## 🔧 故障排除 / Troubleshooting

```bash
# 检查依赖
pip install schedule

# 查看日志
tail -20 logs/podlens.log

# 重置进度
rm .podcast_progress.json
```

---

**每小时更新，专注最新** - 智能播客跟踪服务！
**Hourly updates, focus on latest** - Smart podcast tracking service! 