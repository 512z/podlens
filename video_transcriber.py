#!/usr/bin/env python3
"""
Local Video Transcriber - 本地视频转录工具
基于 PodLens 项目的成熟转录技术，支持本地视频文件转录

使用方法:
python video_transcriber.py 0.MOV
"""

import os
import sys
import time
import contextlib
import io
from pathlib import Path
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import transcription libraries
try:
    import mlx_whisper
    import mlx.core as mx
    MLX_WHISPER_AVAILABLE = True
    MLX_DEVICE = mx.default_device()
    print(f"🎯 MLX Whisper available, using device: {MLX_DEVICE}")
except ImportError:
    MLX_WHISPER_AVAILABLE = False
    print("⚠️  MLX Whisper not available")

try:
    from groq import Groq
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_AVAILABLE = bool(GROQ_API_KEY)
    if GROQ_AVAILABLE:
        print("🚀 Groq API available, ultra-fast transcription enabled")
    else:
        print("⚠️  Groq API key not set")
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️  Groq SDK not installed")


class VideoTranscriber:
    """本地视频转录器 - 复用PodLens成功验证的转录技术"""

    def __init__(self):
        self.whisper_model_name = "mlx-community/whisper-large-v3-turbo"

    def extract_audio_from_video(self, video_file: Path, output_audio: Path) -> bool:
        """从视频文件提取音频"""
        import subprocess

        try:
            print(f"🎵 从视频提取音频: {video_file.name}")

            # 使用ffmpeg提取音频
            cmd = [
                'ffmpeg',
                '-i', str(video_file),
                '-vn',  # 不要视频流
                '-acodec', 'mp3',  # 音频编码为mp3
                '-ar', '16000',  # 16kHz采样率
                '-ac', '1',  # 单声道
                '-b:a', '64k',  # 64k比特率
                '-y',  # 覆盖输出文件
                str(output_audio)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ 音频提取完成: {output_audio}")
                return True
            else:
                print(f"❌ 音频提取失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 音频提取错误: {e}")
            return False

    def get_file_size_mb(self, file_path: Path) -> float:
        """获取文件大小(MB)"""
        if not file_path.exists():
            return 0
        size_bytes = file_path.stat().st_size
        return size_bytes / (1024 * 1024)

    def transcribe_with_groq(self, audio_file: Path) -> Optional[Dict]:
        """使用Groq API转录音频文件 - 复用PodLens代码"""
        if not GROQ_AVAILABLE:
            return None

        try:
            print("🚀 使用Groq API进行超快转录...")
            client = Groq(api_key=GROQ_API_KEY)

            start_time = time.time()

            with open(audio_file, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=file,
                    model="whisper-large-v3",
                    # 自动检测语言，保持原始语言
                    response_format="json",
                    temperature=0.0
                )

            end_time = time.time()
            duration = end_time - start_time

            print(f"✅ Groq转录完成，用时: {duration:.1f}秒")

            return {
                'text': transcription.text,
                'method': 'Groq API',
                'duration': duration,
                'model': 'whisper-large-v3'
            }

        except Exception as e:
            print(f"❌ Groq转录失败: {e}")
            return None

    def transcribe_with_mlx(self, audio_file: Path) -> Optional[Dict]:
        """使用MLX Whisper转录音频文件 - 复用PodLens代码"""
        if not MLX_WHISPER_AVAILABLE:
            return None

        try:
            print("🎯 使用MLX Whisper进行本地转录...")
            start_time = time.time()

            # 静默模式运行，避免大量输出
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = mlx_whisper.transcribe(
                    str(audio_file),
                    path_or_hf_repo=self.whisper_model_name
                )

            end_time = time.time()
            duration = end_time - start_time

            print(f"✅ MLX转录完成，用时: {duration:.1f}秒")

            return {
                'text': result.get('text', ''),
                'method': 'MLX Whisper',
                'duration': duration,
                'model': self.whisper_model_name
            }

        except Exception as e:
            print(f"❌ MLX转录失败: {e}")
            return None

    def transcribe_audio_smart(self, audio_file: Path) -> Optional[str]:
        """智能音频转录：根据文件大小选择最佳转录方式 - 复用PodLens逻辑"""
        if not (GROQ_AVAILABLE or MLX_WHISPER_AVAILABLE):
            print("❌ 没有可用的转录服务")
            return None

        file_size_mb = self.get_file_size_mb(audio_file)
        print(f"📊 音频文件大小: {file_size_mb:.1f}MB")

        transcript_text = None

        # 智能选择转录方式
        if file_size_mb <= 25 and GROQ_AVAILABLE:
            # 小文件优先使用Groq（超快速）
            result = self.transcribe_with_groq(audio_file)
            if result:
                transcript_text = result['text']

        # 如果Groq失败或文件太大，使用MLX Whisper
        if not transcript_text and MLX_WHISPER_AVAILABLE:
            result = self.transcribe_with_mlx(audio_file)
            if result:
                transcript_text = result['text']

        return transcript_text

    def transcribe_video(self, video_file: Path) -> Optional[str]:
        """转录视频文件的完整流程"""
        if not video_file.exists():
            print(f"❌ 视频文件不存在: {video_file}")
            return None

        print(f"🎬 开始处理视频: {video_file.name}")

        # 创建输出目录
        output_dir = video_file.parent / "transcripts"
        output_dir.mkdir(exist_ok=True)

        # 音频文件路径
        audio_file = output_dir / f"{video_file.stem}_audio.mp3"

        # 1. 提取音频
        if not self.extract_audio_from_video(video_file, audio_file):
            return None

        try:
            # 2. 转录音频
            transcript_text = self.transcribe_audio_smart(audio_file)

            if transcript_text:
                # 3. 保存转录结果
                transcript_file = output_dir / f"{video_file.stem}_transcript.md"

                with open(transcript_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {video_file.name} 转录文本\n\n")
                    f.write(f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("## 转录内容\n\n")
                    f.write(transcript_text)

                print(f"✅ 转录完成！结果保存至: {transcript_file}")
                return transcript_text
            else:
                print("❌ 转录失败")
                return None

        finally:
            # 清理临时音频文件
            if audio_file.exists():
                audio_file.unlink()
                print("🧹 清理临时音频文件")


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python video_transcriber.py <视频文件>")
        print("示例: python video_transcriber.py 0.MOV")
        sys.exit(1)

    video_path = Path(sys.argv[1])

    # 检查依赖
    if not (GROQ_AVAILABLE or MLX_WHISPER_AVAILABLE):
        print("❌ 需要设置 GROQ_API_KEY 或安装 mlx-whisper")
        print("💡 在 .env 文件中设置: GROQ_API_KEY=your_key_here")
        sys.exit(1)

    # 开始转录
    transcriber = VideoTranscriber()
    result = transcriber.transcribe_video(video_path)

    if result:
        print("\n🎉 转录成功完成！")
        print(f"📝 转录文本预览:\n{result[:200]}...")
    else:
        print("\n❌ 转录失败")
        sys.exit(1)


if __name__ == "__main__":
    main()

