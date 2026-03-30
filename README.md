# YouTube Downloader Telegram Bot

Bot Telegram che scarica video da YouTube e li invia direttamente in chat, con supporto per file fino a 2GB grazie al Telegram Bot API server locale.

## Prerequisiti

- Docker e Docker Compose
- Un account Telegram

## 1. Creare il bot Telegram

### 1.1 Ottenere il BOT_TOKEN

1. Apri Telegram e cerca **@BotFather**
2. Invia il comando `/newbot`
3. Scegli un **nome** per il bot (es. "YouTube Downloader")
4. Scegli uno **username** che finisca con `bot` (es. `mio_ytdl_bot`)
5. BotFather risponde con il token:
   ```
   Use this token to access the HTTP API:
   7123456789:AAH1234abcd5678efgh-xyz
   ```
6. Copia il token, ti servira' nel file `.env`

### 1.2 Ottenere TELEGRAM_API_ID e TELEGRAM_API_HASH

Questi servono al Telegram Bot API server locale per inviare file superiori a 50MB (fino a 2GB).

1. Vai su [https://my.telegram.org](https://my.telegram.org)
2. Accedi con il tuo **numero di telefono** (con prefisso internazionale, es. `+39...`)
3. Inserisci il **codice di verifica** ricevuto su Telegram
4. Clicca su **"API development tools"**
5. Compila il form (solo la prima volta):
   - **App title**: un nome qualsiasi (es. "YT Downloader Bot")
   - **Short name**: un nome breve (es. "ytdlbot")
   - **Platform**: Other
6. Clicca **Create application**
7. Nella pagina che appare trovi:
   - **App api_id** (un numero) &rarr; questo e' il tuo `TELEGRAM_API_ID`
   - **App api_hash** (una stringa esadecimale) &rarr; questo e' il tuo `TELEGRAM_API_HASH`

## 2. Avvio in locale (sviluppo/test)

```bash
# Clona il repository
git clone <repo-url>
cd yt-downloader

# Crea il file .env dalle variabili di esempio
cp .env.example .env
```

Modifica `.env` con i tuoi valori:

```
BOT_TOKEN=7123456789:AAH1234abcd5678efgh-xyz
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
```

Avvia i container:

```bash
docker-compose up --build
```

Apri Telegram, cerca il tuo bot e invia un link YouTube per testarlo.

## 3. Installazione su Home Assistant

### 3.1 Aggiungere il repository come add-on locale

1. Copia la cartella del progetto nella directory degli add-on di Home Assistant:
   ```
   /addons/yt-downloader-bot/
   ```
   oppure aggiungi questo repository Git come **repository di add-on**:
   - Vai in **Impostazioni > Add-ons > Negozio Add-on**
   - Clicca sui tre puntini in alto a destra > **Repository**
   - Incolla l'URL del repository Git e clicca **Aggiungi**

2. Aggiorna la lista degli add-on (clicca sui tre puntini > **Controlla aggiornamenti**)

3. Cerca **"YouTube Downloader Bot"** nella lista e clicca **Installa**

### 3.2 Configurare l'add-on

1. Vai nella tab **Configurazione** dell'add-on
2. Compila i campi:
   - `bot_token`: il token ottenuto da BotFather
   - `telegram_api_id`: l'API ID da my.telegram.org
   - `telegram_api_hash`: l'API Hash da my.telegram.org
3. Clicca **Salva**

### 3.3 Avviare l'add-on

1. Vai nella tab **Informazioni** e clicca **Avvia**
2. Controlla i **Log** per verificare che il bot sia partito correttamente
3. Dovresti vedere:
   ```
   Bot started
   Using local Bot API server at http://127.0.0.1:8081
   ```

## 4. Come funziona

### Flusso utente

1. Invii un link YouTube al bot
2. Il bot recupera le qualita' disponibili (senza scaricare il video)
3. Appare una tastiera inline con le risoluzioni (es. 360p, 720p, 1080p, Best)
4. Scegli la qualita' desiderata
5. Il bot scarica il video, lo converte e lo invia in chat
6. I file temporanei vengono eliminati automaticamente

### Download del video da YouTube

Il bot usa [yt-dlp](https://github.com/yt-dlp/yt-dlp) per interagire con YouTube:

1. **Recupero qualita'**: `yt-dlp` interroga YouTube con `extract_info(url, download=False)` per ottenere la lista di tutti gli stream disponibili (risoluzioni, codec, dimensioni stimate) senza scaricare nulla.

2. **Download**: YouTube separa video e audio in stream distinti. yt-dlp scarica separatamente il miglior stream video e il miglior stream audio per la risoluzione scelta, poi li unisce (merge) in un unico file MP4.

   La strategia di selezione formato preferisce H.264 + AAC se disponibili:
   ```
   bestvideo[height<=720][vcodec^=avc1]+bestaudio[acodec^=mp4a]
   ```
   Se non disponibili in H.264, scarica il best disponibile (tipicamente VP9 o AV1).

### Conversione per Telegram

Telegram riproduce i video inline (direttamente nel player della chat) **solo** se il file rispetta questi requisiti:

| Parametro | Valore richiesto |
|-----------|-----------------|
| Codec video | H.264 (libx264) |
| Profilo | High |
| Pixel format | yuv420p |
| Codec audio | AAC |
| Container | MP4 |
| Moov atom | All'inizio del file (faststart) |

YouTube serve spesso i video in **VP9** o **AV1**, codec piu' moderni che Telegram non riproduce inline (lo schermo resta nero, ma il video funziona se scaricato sul dispositivo).

Per questo motivo, dopo il download, il bot **ri-codifica sempre** il video con ffmpeg:

```bash
ffmpeg -i input.mp4 \
  -c:v libx264 -profile:v high -level 4.0 -pix_fmt yuv420p \
  -preset medium -crf 23 -g 30 \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  output.mp4
```

Questo garantisce che il video sia sempre riproducibile direttamente nel player di Telegram.

### Telegram Bot API server locale

L'API standard dei bot Telegram ha un limite di **50MB** per l'invio di file. Per superarlo (fino a **2GB**), il bot utilizza un'istanza locale del [Telegram Bot API server](https://github.com/tdlib/telegram-bot-api).

Il bot API server locale si interpone tra il bot e i server Telegram, gestendo l'upload diretto dei file senza il limite di 50MB:

```
Bot Python  --->  Bot API locale (porta 8081)  --->  Server Telegram
```

## Architettura

```
docker-compose.yml
  |
  +-- telegram-bot-api (container)
  |     Telegram Bot API server locale
  |     Gestisce l'upload di file fino a 2GB
  |
  +-- yt-bot (container)
        Python bot + yt-dlp + ffmpeg
        Riceve messaggi, scarica video, converte, invia
```

In Home Assistant, entrambi i processi girano nello stesso container gestiti da supervisord.
