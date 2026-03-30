# YouTube Downloader Telegram Bot

Telegram bot that downloads YouTube videos and sends them directly to chat, with support for files up to 2GB thanks to the local Telegram Bot API server. Also supports audio-only extraction in MP3 format.

## Prerequisites

- Docker and Docker Compose
- A Telegram account

## 1. Create the Telegram bot

### 1.1 Get the BOT_TOKEN

1. Open Telegram and search for **@BotFather**
2. Send the command `/newbot`
3. Choose a **name** for the bot (e.g. "YouTube Downloader")
4. Choose a **username** ending with `bot` (e.g. `my_ytdl_bot`)
5. BotFather replies with the token:
   ```
   Use this token to access the HTTP API:
   7123456789:AAH1234abcd5678efgh-xyz
   ```
6. Copy the token, you'll need it in the `.env` file

### 1.2 Get TELEGRAM_API_ID and TELEGRAM_API_HASH

These are required by the local Telegram Bot API server to send files larger than 50MB (up to 2GB).

1. Go to [https://my.telegram.org](https://my.telegram.org)
2. Log in with your **phone number** (with international prefix, e.g. `+1...`)
3. Enter the **verification code** received on Telegram
4. Click on **"API development tools"**
5. Fill in the form (first time only):
   - **App title**: any name (e.g. "YT Downloader Bot")
   - **Short name**: a short name (e.g. "ytdlbot")
   - **Platform**: Other
6. Click **Create application**
7. On the page that appears you'll find:
   - **App api_id** (a number) &rarr; this is your `TELEGRAM_API_ID`
   - **App api_hash** (a hexadecimal string) &rarr; this is your `TELEGRAM_API_HASH`

## 2. Local setup (development/testing)

```bash
# Clone the repository
git clone <repo-url>
cd yt-downloader

# Create the .env file from the example
cp .env.example .env
```

Edit `.env` with your values:

```
BOT_TOKEN=7123456789:AAH1234abcd5678efgh-xyz
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
```

Start the containers:

```bash
docker-compose up --build
```

Open Telegram, find your bot and send a YouTube link to test it.

## 3. Installation on Home Assistant

### 3.1 Add the repository as a local add-on

1. Copy the project folder into the Home Assistant add-ons directory:
   ```
   /addons/yt-downloader-bot/
   ```
   or add this Git repository as an **add-on repository**:
   - Go to **Settings > Add-ons > Add-on Store**
   - Click the three dots in the top right > **Repositories**
   - Paste the Git repository URL and click **Add**

2. Refresh the add-on list (click the three dots > **Check for updates**)

3. Search for **"YouTube Downloader Bot"** in the list and click **Install**

### 3.2 Configure the add-on

1. Go to the **Configuration** tab of the add-on
2. Fill in the fields:
   - `bot_token`: the token obtained from BotFather
   - `telegram_api_id`: the API ID from my.telegram.org
   - `telegram_api_hash`: the API Hash from my.telegram.org
3. Click **Save**

### 3.3 Start the add-on

1. Go to the **Info** tab and click **Start**
2. Check the **Logs** to verify the bot started correctly
3. You should see:
   ```
   Bot started
   Using local Bot API server at http://127.0.0.1:8081
   ```

## 4. How it works

### User flow

1. Send a YouTube link to the bot
2. The bot fetches available qualities (without downloading the video)
3. An inline keyboard appears with resolutions (e.g. 360p, 720p, 1080p, Best) and an "Audio only (MP3)" option
4. Choose the desired quality or audio extraction
5. The bot downloads the video/audio, converts it and sends it to chat
6. Temporary files are automatically deleted

### Downloading from YouTube

The bot uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) to interact with YouTube:

1. **Quality retrieval**: `yt-dlp` queries YouTube with `extract_info(url, download=False)` to get the list of all available streams (resolutions, codecs, estimated sizes) without downloading anything.

2. **Video download**: YouTube separates video and audio into distinct streams. yt-dlp downloads the best video stream and the best audio stream for the chosen resolution separately, then merges them into a single MP4 file.

   The format selection strategy prefers H.264 + AAC when available:
   ```
   bestvideo[height<=720][vcodec^=avc1]+bestaudio[acodec^=mp4a]
   ```
   If not available in H.264, it downloads the best available (typically VP9 or AV1).

3. **Audio download**: When "Audio only" is selected, yt-dlp downloads the best audio stream and converts it to MP3 at 192kbps using ffmpeg. Telegram supports MP3 and M4A formats for audio playback.

### Video conversion for Telegram

Telegram plays videos inline (directly in the chat player) **only** if the file meets these requirements:

| Parameter | Required value |
|-----------|---------------|
| Video codec | H.264 (libx264) |
| Profile | High |
| Pixel format | yuv420p |
| Audio codec | AAC |
| Container | MP4 |
| Moov atom | At the beginning of the file (faststart) |

YouTube often serves videos in **VP9** or **AV1**, more modern codecs that Telegram cannot play inline (the screen stays black, but the video works if downloaded to the device).

For this reason, after downloading, the bot **always re-encodes** the video with ffmpeg:

```bash
ffmpeg -i input.mp4 \
  -c:v libx264 -profile:v high -level 4.0 -pix_fmt yuv420p \
  -preset medium -crf 23 -g 30 \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  output.mp4
```

This ensures that the video is always playable directly in the Telegram player.

### Local Telegram Bot API server

The standard Telegram Bot API has a **50MB** limit for sending files. To exceed this (up to **2GB**), the bot uses a local instance of the [Telegram Bot API server](https://github.com/tdlib/telegram-bot-api).

The local Bot API server sits between the bot and the Telegram servers, handling direct file uploads without the 50MB limit:

```
Python Bot  --->  Local Bot API (port 8081)  --->  Telegram Servers
```

## Architecture

```
docker-compose.yml
  |
  +-- telegram-bot-api (container)
  |     Local Telegram Bot API server
  |     Handles file uploads up to 2GB
  |
  +-- yt-bot (container)
        Python bot + yt-dlp + ffmpeg
        Receives messages, downloads videos, converts, sends
```

On Home Assistant, both processes run in the same container managed by supervisord.
