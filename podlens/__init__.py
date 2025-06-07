"""
Podlens - 智能播客转录与摘要工具 / Intelligent Podcast Transcription and Summary Tool

支持 Apple Podcast 和 YouTube 平台，提供中英文双语界面
Supports Apple Podcast and YouTube platforms with bilingual Chinese/English interface
"""

__version__ = "1.0.0"

# 中文版导入 / Chinese version imports
from .apple_podcast_ch import ApplePodcastExplorer as ApplePodcastExplorer_CH
from .youtube_ch import (
    YouTubeSearcher as YouTubeSearcher_CH,
    TranscriptExtractor as TranscriptExtractor_CH, 
    SummaryGenerator as SummaryGenerator_CH,
    Podnet as Podnet_CH
)

# 英文版导入 / English version imports  
from .apple_podcast_en import ApplePodcastExplorer as ApplePodcastExplorer_EN
from .youtube_en import (
    YouTubeSearcher as YouTubeSearcher_EN,
    TranscriptExtractor as TranscriptExtractor_EN,
    SummaryGenerator as SummaryGenerator_EN, 
    Podnet as Podnet_EN
)

# 向后兼容的默认导出（中文版）/ Backward compatible default exports (Chinese version)
ApplePodcastExplorer = ApplePodcastExplorer_CH
YouTubeSearcher = YouTubeSearcher_CH
TranscriptExtractor = TranscriptExtractor_CH
SummaryGenerator = SummaryGenerator_CH
Podnet = Podnet_CH

# 语言选择器 / Language selector
def get_chinese_version():
    """获取中文版本的所有类 / Get Chinese version of all classes"""
    return {
        'ApplePodcastExplorer': ApplePodcastExplorer_CH,
        'YouTubeSearcher': YouTubeSearcher_CH,
        'TranscriptExtractor': TranscriptExtractor_CH,
        'SummaryGenerator': SummaryGenerator_CH,
        'Podnet': Podnet_CH
    }

def get_english_version():
    """获取英文版本的所有类 / Get English version of all classes"""
    return {
        'ApplePodcastExplorer': ApplePodcastExplorer_EN,
        'YouTubeSearcher': YouTubeSearcher_EN,
        'TranscriptExtractor': TranscriptExtractor_EN,
        'SummaryGenerator': SummaryGenerator_EN,
        'Podnet': Podnet_EN
    }

# 自动化接口导入 / Automation interface imports
from .auto_ch import (
    AutoEngine as AutomationEngine_CH,
    start_automation as start_automation_ch,
    show_status as show_automation_status_ch
)

from .auto_en import (
    AutoEngine as AutomationEngine_EN,
    start_automation as start_automation_en,
    show_status as show_automation_status_en
)

# 默认导出中文版（向后兼容）/ Default export Chinese version (backward compatible)
AutomationEngine = AutomationEngine_CH
start_automation = start_automation_ch
show_automation_status = show_automation_status_ch

# 公开的API / Public API
__all__ = [
    # 中文版 / Chinese version
    'ApplePodcastExplorer_CH',
    'YouTubeSearcher_CH', 
    'TranscriptExtractor_CH',
    'SummaryGenerator_CH',
    'Podnet_CH',
    
    # 英文版 / English version
    'ApplePodcastExplorer_EN',
    'YouTubeSearcher_EN',
    'TranscriptExtractor_EN', 
    'SummaryGenerator_EN',
    'Podnet_EN',
    
    # 默认导出（向后兼容）/ Default exports (backward compatible)
    'ApplePodcastExplorer',
    'YouTubeSearcher',
    'TranscriptExtractor',
    'SummaryGenerator', 
    'Podnet',
    
    # 辅助函数 / Helper functions
    'get_chinese_version',
    'get_english_version',
    
    # 自动化接口 / Automation interface
    'AutomationEngine_CH',
    'AutomationEngine_EN', 
    'start_automation_ch',
    'start_automation_en',
    'show_automation_status_ch',
    'show_automation_status_en',
    
    # 默认导出（向后兼容）/ Default exports (backward compatible)
    'AutomationEngine',
    'start_automation',
    'show_automation_status'
] 