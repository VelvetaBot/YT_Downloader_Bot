# YouTube Downloader Bot for Telegram

A powerful Telegram bot to download YouTube videos in multiple qualities.

## Features
- 🎬 Multiple quality options (Best, 720p, 480p, Audio)
- 📥 Download videos up to 2GB
- 🎵 Extract audio as MP3
- ⚡ Fast and reliable

## Deployment on Render

1. Fork this repository
2. Sign up on [Render.com](https://render.com)
3. Create a new Web Service
4. Connect your GitHub repository
5. Add environment variable: `BOT_TOKEN=your_bot_token_here`
6. Deploy!

## Local Development
```bash
pip install -r requirements.txt
export BOT_TOKEN="your_bot_token"
python bot.py
```

## Support
Join our channel: [@Velvetabots](https://t.me/Velvetabots)
```

**.gitignore:**
```
downloads/
*.pyc
__pycache__/
.env
*.log
```

## 2️⃣ Render.com Deployment

1. **GitHub లో Repository సృష్టించండి:**
   - GitHub.com కి వెళ్ళండి
   - New Repository క్లిక్ చేయండి
   - పేరు: `youtube-downloader-bot`
   - Public గా ఉంచండి
   - పైన ఉన్న అన్ని ఫైళ్ళు అప్‌లోడ్ చేయండి

2. **Render.com Setup:**
   - [Render.com](https://render.com) లో Sign Up చేయండి (GitHub తో)
   - "New +" → "Web Service" క్లిక్ చేయండి
   - మీ repository select చేయండి
   
3. **Configuration:**
```
   Name: youtube-downloader-bot
   Region: Oregon (US West) - ఉచితం
   Branch: main
   Runtime: Docker
   Instance Type: Free
