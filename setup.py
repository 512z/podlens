#!/usr/bin/env python3
"""
PodLens - 播客转录与摘要工具 / Podcast Transcription and Summary Tool
支持 Apple Podcast 和 YouTube 平台，提供中英文双语界面
Supports Apple Podcast and YouTube platforms with bilingual Chinese/English interface
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="podlens",
    version="1.1.6",
    author="Dunyuan Zha",
    author_email="henryzha@outlook.com",
    description="智能播客转录与摘要工具，支持 Apple Podcast 和 YouTube / Intelligent Podcast & Youtube Transcription & Understanding AI Agent",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/512z/podlens/tree/main",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Natural Language :: English",
        "Natural Language :: Chinese (Simplified)",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            # 双语命令入口点 / Bilingual command entry points
            "podlens-zh=podlens.cli_ch:main",     # 中文版 / Chinese version
            "podlens-en=podlens.cli_en:main",     # 英文版 / English version
            "podlens-ch=podlens.cli_ch:main",     # 中文版别名 / Chinese alias
            
            # 默认命令（英文版）/ Default command (English version)
            "podlens=podlens.cli_en:main",
        ],
    },
    keywords=[
        "podcast", "transcription", "summary", "youtube", "apple podcast", 
        "whisper", "ai", "bilingual", "chinese", "english", "播客", "转录", "摘要",
        "gemini", "groq", "mlx", "audio processing", "text generation"
    ],
    project_urls={
        "Homepage": "https://github.com/512z/podlens/tree/main",
    },
    include_package_data=True,
    zip_safe=False,
) 