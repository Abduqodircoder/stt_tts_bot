# 🎬 English With Movies - Telegram Bot

Filmlar orqali ingliz tilini o'rgatuvchi Telegram bot.

## ✨ Imkoniyatlar

- 🎙️ Video nutqini matnga aylantirish (OpenAI Whisper)
- 📖 Muhim so'zlarni (vocabulary) ajratish
- 🧠 10 ta quiz savol avtomatik tuzish (4 variantli)
- 📊 Quiz natijalarini ko'rsatish

## 🛠️ O'rnatish

### 1. Talablar

```bash
# Python 3.9+
python --version

# ffmpeg o'rnatish (Ubuntu/Debian)
sudo apt update
sudo apt install ffmpeg -y

# ffmpeg o'rnatish (macOS)
brew install ffmpeg
```

### 2. Loyihani klonlash

```bash
git clone <repo_url>
cd english-with-movies-bot
```

### 3. Virtual muhit yaratish

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate     # Windows
```

### 4. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 5. Token va API kalitlarini sozlash

```bash
# .env.example faylini .env ga nusxalang
cp .env.example .env

# .env faylini tahrirlang
nano .env
```

`.env` faylida:
```
BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
```

#### Bot Token olish:
1. Telegram'da [@BotFather](https://t.me/BotFather) ga yozing
2. `/newbot` buyrug'ini yuboring
3. Bot nomi va username kiriting
4. Tokenni nusxalab `.env` ga joylashtiring

#### OpenAI API Key olish:
1. [platform.openai.com](https://platform.openai.com) ga kiring
2. API Keys bo'limiga o'ting
3. "Create new secret key" tugmasini bosing
4. Kalitni nusxalab `.env` ga joylashtiring

### 6. Botni ishga tushirish

```bash
python bot.py
```

## 📁 Fayl tuzilmasi

```
english-with-movies-bot/
├── bot.py              # Asosiy bot fayl
├── video_processor.py  # Video → Matn (Whisper)
├── quiz_generator.py   # Vocabulary va Quiz (GPT-4o-mini)
├── requirements.txt    # Python kutubxonalari
├── .env.example        # Environment o'zgaruvchilar namunasi
└── README.md           # Qo'llanma
```

## 🎯 Foydalanish

1. Botni Telegram'da toping
2. `/start` buyrug'ini yuboring
3. Ingliz tilidagi video yuboring (max 50MB)
4. Bot avtomatik:
   - ✅ Nutqni matnga aylantiradi
   - ✅ 10-15 ta muhim so'zni ajratadi
   - ✅ 10 ta quiz savol tuzadi
5. Savollarga javob bering va natijangizni ko'ring!

## ⚙️ Texnik ma'lumotlar

| Komponent | Texnologiya |
|-----------|-------------|
| Bot framework | python-telegram-bot 21.x |
| Speech-to-Text | OpenAI Whisper API |
| AI/NLP | GPT-4o-mini |
| Audio extraction | FFmpeg |

## ⚠️ Cheklovlar

- Video hajmi: max 50MB
- Audio hajmi: max 25MB (OpenAI Whisper limiti)
- Til: Ingliz tili videolari uchun mo'ljallangan

## 💰 Narxlar (taxminiy)

- Whisper API: ~$0.006/daqiqa
- GPT-4o-mini: ~$0.001/1K token
- 5 daqiqalik video uchun taxminan: ~$0.05

## 🐛 Muammolar

**"ffmpeg topilmadi" xatosi:**
```bash
sudo apt install ffmpeg
```

**"OpenAI API key" xatosi:**
- `.env` faylidagi kalitni tekshiring

**Video qayta ishlanmayapti:**
- Video ingliz tilida ekanligini tekshiring
- Fayl hajmi 50MB dan kam ekanligini tekshiring
