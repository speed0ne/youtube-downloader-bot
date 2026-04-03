import os
import subprocess
import tempfile
from dataclasses import dataclass

import yt_dlp


@dataclass
class DownloadResult:
    filepath: str
    duration: int | None
    width: int | None
    height: int | None
    title: str | None


@dataclass
class VideoFormat:
    height: int
    resolution: str
    filesize_approx: int | None


def get_formats(url: str) -> list[VideoFormat]:
    """Fetch available resolutions for a YouTube URL without downloading."""
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    seen_heights: set[int] = set()
    formats: list[VideoFormat] = []

    for f in info.get("formats", []):
        if f.get("vcodec", "none") == "none":
            continue

        height = f.get("height")
        if not height or height in seen_heights:
            continue
        seen_heights.add(height)

        filesize = f.get("filesize") or f.get("filesize_approx")

        formats.append(
            VideoFormat(
                height=height,
                resolution=f"{height}p",
                filesize_approx=filesize,
            )
        )

    formats.sort(key=lambda x: x.height)
    return formats


def format_size(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "~"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f}KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.0f}MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"


def get_stream_url(url: str) -> str:
    """Get a direct streamable URL (best pre-merged format)."""
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "format": "b/bv*+ba/b*"}) as ydl:
        info = ydl.extract_info(url, download=False)
        # Pre-merged formats have a direct url
        if info.get("url"):
            return info["url"]
        # If merged, return the video stream url
        for f in info.get("requested_formats", []):
            if f.get("vcodec", "none") != "none":
                return f["url"]
        raise ValueError("No streamable URL found")


def download_audio(url: str) -> DownloadResult:
    """Download audio only and return the path to an MP3 file."""
    download_dir = tempfile.mkdtemp(prefix="ytbot_")

    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(download_dir, "%(title).80s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
        ],
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

        # Find the mp3 file in the download dir
        for f in os.listdir(download_dir):
            if f.endswith(".mp3"):
                return DownloadResult(
                    filepath=os.path.join(download_dir, f),
                    duration=info.get("duration"),
                    width=None,
                    height=None,
                    title=info.get("title"),
                )

    raise FileNotFoundError("Audio extraction failed: no output file found")


def download(url: str, height: int | None = None) -> str:
    """Download a video and return the path to the downloaded file.

    Uses bestvideo+bestaudio merge strategy, optionally capped at a resolution.
    """
    download_dir = tempfile.mkdtemp(prefix="ytbot_")

    # Prefer H.264 (vcodec=avc1) + AAC for Telegram inline playback
    if height:
        fmt = (
            f"bestvideo[height<={height}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]/best"
        )
    else:
        fmt = (
            "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
            "bestvideo+bestaudio/best"
        )

    opts = {
        "format": fmt,
        "outtmpl": os.path.join(download_dir, "%(title).80s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        raw_path = base + ".mp4"
        if not os.path.exists(raw_path):
            for f in os.listdir(download_dir):
                raw_path = os.path.join(download_dir, f)
                break
            else:
                raise FileNotFoundError("Download failed: no output file found")

        # Re-encode to H.264/AAC with Telegram-compatible settings
        output_path = os.path.join(download_dir, "telegram_ready.mp4")
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", raw_path,
                "-c:v", "libx264",
                "-profile:v", "high",
                "-level", "4.0",
                "-pix_fmt", "yuv420p",
                "-preset", "medium",
                "-crf", "23",
                "-g", "30",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                output_path,
            ],
            check=True,
            capture_output=True,
        )

        # Remove the raw file, keep only the re-encoded one
        if raw_path != output_path:
            os.remove(raw_path)

        return DownloadResult(
            filepath=output_path,
            duration=info.get("duration"),
            width=info.get("width"),
            height=info.get("height"),
            title=info.get("title"),
        )
