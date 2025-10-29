#!/usr/bin/env python3
"""
Simple Groq Audio Transcription Script
Usage: python transcribe_with_groq.py <audio_file>
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import Groq
try:
    from groq import Groq
except ImportError:
    print("❌ Groq SDK not installed. Please run: pip install groq")
    sys.exit(1)

class GroqTranscriber:
    def __init__(self):
        self.api_key = os.getenv('GROQ_API_KEY')
        if not self.api_key:
            print("❌ GROQ_API_KEY not found in environment variables")
            print("Please set it in .env file or export it:")
            print("export GROQ_API_KEY='your-api-key-here'")
            sys.exit(1)
        
        self.client = Groq(api_key=self.api_key)
        self.max_file_size_mb = 25  # Groq API limit
    
    def get_file_size_mb(self, filepath):
        """Get file size in MB"""
        return os.path.getsize(filepath) / (1024 * 1024)
    
    def compress_audio(self, input_file, output_file):
        """Compress audio to fit within Groq's size limit"""
        print("🔧 Compressing audio file...")
        
        # First try 64kbps
        cmd = [
            'ffmpeg',
            '-i', str(input_file),
            '-ar', '16000',      # 16KHz sampling rate
            '-ac', '1',          # Mono
            '-b:a', '64k',       # 64kbps bitrate
            '-y',                # Overwrite output
            str(output_file)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            compressed_size = self.get_file_size_mb(output_file)
            print(f"✅ Compressed to {compressed_size:.1f}MB")
            
            # If still too large, try 48kbps
            if compressed_size > self.max_file_size_mb:
                print("⚠️  Still too large, compressing further...")
                cmd[cmd.index('64k')] = '48k'
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                final_size = self.get_file_size_mb(output_file)
                print(f"✅ Final size: {final_size:.1f}MB")
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Compression failed: {e}")
            return False
        except FileNotFoundError:
            print("❌ ffmpeg not found. Please install ffmpeg:")
            print("   macOS: brew install ffmpeg")
            print("   Ubuntu: sudo apt install ffmpeg")
            return False
    
    def transcribe(self, audio_file):
        """Transcribe audio file using Groq API"""
        file_size_mb = self.get_file_size_mb(audio_file)
        print(f"📊 File size: {file_size_mb:.1f}MB")
        
        # Check if compression is needed
        if file_size_mb > self.max_file_size_mb:
            print(f"⚠️  File exceeds {self.max_file_size_mb}MB limit")
            compressed_file = audio_file.parent / f"compressed_{audio_file.name}"
            
            if not self.compress_audio(audio_file, compressed_file):
                return None
            
            # Use compressed file for transcription
            audio_file = compressed_file
            cleanup_compressed = True
        else:
            cleanup_compressed = False
        
        # Transcribe with Groq
        print("🚀 Starting Groq transcription...")
        start_time = time.time()
        
        try:
            with open(audio_file, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    file=file,
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    temperature=0.0
                )
            
            elapsed_time = time.time() - start_time
            
            # Extract text from response
            text = transcription.text if hasattr(transcription, 'text') else transcription.get('text', '')
            language = getattr(transcription, 'language', 'unknown')
            
            print(f"✅ Transcription completed in {elapsed_time:.1f} seconds")
            print(f"📝 Detected language: {language}")
            
            # Clean up compressed file if created
            if cleanup_compressed and audio_file.exists():
                audio_file.unlink()
                print("🗑️  Cleaned up compressed file")
            
            return text
            
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            
            # Clean up compressed file if created
            if cleanup_compressed and audio_file.exists():
                audio_file.unlink()
            
            return None

def main():
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python transcribe_with_groq.py <audio_file>")
        print("Example: python transcribe_with_groq.py meeting_5.m4a")
        sys.exit(1)
    
    # Get audio file path
    audio_file = Path(sys.argv[1])
    
    # Check if file exists
    if not audio_file.exists():
        print(f"❌ File not found: {audio_file}")
        sys.exit(1)
    
    print(f"🎙️  Processing: {audio_file.name}")
    print("=" * 50)
    
    # Initialize transcriber
    transcriber = GroqTranscriber()
    
    # Transcribe audio
    transcript = transcriber.transcribe(audio_file)
    
    if transcript:
        # Save transcript
        output_file = audio_file.parent / f"{audio_file.stem}_transcript.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Transcript of: {audio_file.name}\n")
            f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            f.write(transcript)
        
        print(f"\n✅ Transcript saved to: {output_file}")
        print(f"📄 Length: {len(transcript)} characters")
    else:
        print("\n❌ Transcription failed")
        sys.exit(1)

if __name__ == "__main__":
    main()

