# Changelog

## 0.0.12

- Add `build.yaml` with explicit `BUILD_FROM` base images (fixes build failure on recent Supervisor/buildx)

## 0.0.11

- Add "Native format (no transcode)" option to download video without ffmpeg re-encode

## 0.0.10

- Fix ffmpeg encoding hang caused by stderr pipe buffer deadlock

## 0.0.9

- Show separate progress for video and audio streams (e.g. "Downloading video... 60%", "Downloading audio... 30%")

## 0.0.8

- Show encoding progress percentage during ffmpeg re-encode (video)
- Show "Converting to MP3..." status during audio post-processing
- Unified throttled message editing for all progress phases

## 0.0.7

- Clean up previous pending link when user sends a new YouTube URL

## 0.0.6

- Show download progress percentage (updates every 10%)
- Run downloads in background thread to avoid blocking the event loop

## 0.0.5

- Add username whitelist to restrict bot access (`allowed_usernames` option)
- Reply with a helpful message when users send non-YouTube text
- Add HA translations with config option descriptions
- Fix stream URL fallback for non-pre-merged formats

## 0.0.2

- Add stream-only option to get direct playback URL

## 0.0.1

- Initial release with YouTube video/audio download support
- Local Bot API server for files up to 2 GB
- Quality selection via inline keyboard
