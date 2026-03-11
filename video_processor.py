import os
import subprocess
import tempfile
import asyncio
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class VideoProcessor:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def extract_audio(self, video_path: str) -> str:
        """Extract audio from video using ffmpeg"""
        audio_path = video_path.replace(".mp4", ".mp3")
        
        try:
            cmd = [
                "ffmpeg", "-i", video_path,
                "-vn",           # No video
                "-acodec", "libmp3lame",
                "-ar", "16000",  # 16kHz sample rate
                "-ac", "1",      # Mono
                "-ab", "64k",    # Bitrate
                "-y",            # Overwrite
                audio_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"ffmpeg error: {stderr.decode()}")
                raise Exception(f"Audio extraction failed: {stderr.decode()}")
            
            return audio_path
            
        except FileNotFoundError:
            raise Exception(
                "ffmpeg topilmadi. Iltimos, ffmpeg o'rnating: sudo apt install ffmpeg"
            )
    
    async def transcribe_video(self, video_path: str) -> str:
        """Transcribe video using OpenAI Whisper"""
        audio_path = None
        
        try:
            # Extract audio
            logger.info("Audio ajratilmoqda...")
            audio_path = await self.extract_audio(video_path)
            
            # Check audio file size (OpenAI limit: 25MB)
            audio_size = os.path.getsize(audio_path)
            
            if audio_size > 25 * 1024 * 1024:
                # Split and transcribe in chunks
                return await self._transcribe_large_audio(audio_path)
            
            # Transcribe with Whisper API
            logger.info("Matn ajratilmoqda (Whisper)...")
            
            with open(audio_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                    response_format="text"
                )
            
            transcript = response if isinstance(response, str) else response.text
            logger.info(f"Transkriptsiya tugadi: {len(transcript)} belgi")
            
            return transcript
            
        finally:
            # Cleanup audio file
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)
    
    async def _transcribe_large_audio(self, audio_path: str) -> str:
        """Handle large audio files by splitting into chunks"""
        logger.info("Katta audio faylni bo'laklarga bo'lish...")
        
        # Get audio duration
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries",
            "format=duration", "-of", "csv=p=0", audio_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        duration = float(stdout.decode().strip())
        
        # Split into 10-minute chunks
        chunk_duration = 600  # seconds
        chunks = []
        transcripts = []
        
        start = 0
        chunk_idx = 0
        
        while start < duration:
            chunk_path = audio_path.replace(".mp3", f"_chunk{chunk_idx}.mp3")
            chunks.append(chunk_path)
            
            cmd = [
                "ffmpeg", "-i", audio_path,
                "-ss", str(start),
                "-t", str(chunk_duration),
                "-y", chunk_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            # Transcribe chunk
            with open(chunk_path, "rb") as f:
                response = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="en",
                    response_format="text"
                )
            
            text = response if isinstance(response, str) else response.text
            transcripts.append(text)
            
            start += chunk_duration
            chunk_idx += 1
        
        # Cleanup chunks
        for chunk in chunks:
            if os.path.exists(chunk):
                os.unlink(chunk)
        
        return " ".join(transcripts)
