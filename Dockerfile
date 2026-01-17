FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY bot.py .
RUN mkdir -p downloads

CMD ["python", "bot.py"]
```

---

## 🎯 ఈ Version Features:

1. **Multiple extraction methods** - iOS, mweb, Android clients try చేస్తుంది
2. **Fallback system** - ఒకటి fail అయితే మరొకటి try చేస్తుంది
3. **Mobile user agents** - YouTube mobile versions ఉపయోగిస్తుంది (తక్కువ restrictions)
4. **Auto yt-dlp update** - Startup లో latest version download చేస్తుంది

---

## ✅ ఏ Videos పని చేస్తాయి:

1. **Music videos** from official channels (Vevo, T-Series, etc.)
2. **Popular videos** (million+ views)
3. **Tutorial/educational** videos
4. **Gaming** videos
5. **Older uploads** (24+ hours old)

---

## ❌ పని చేయని Videos:

1. **Age-restricted** (18+, requires login)
2. **Members-only** content
3. **Recently uploaded** (< 1 hour)
4. **Live streams** currently broadcasting
5. **Premium** content

---

## 🧪 Test Videos (Usually Work):

Try these links తో test చేయండి:
```
https://www.youtube.com/watch?v=dQw4w9WgXcQ
(Rick Astley - Never Gonna Give You Up)

https://www.youtube.com/watch?v=kJQP7kiw5Fk
(Luis Fonsi - Despacito)

https://www.youtube.com/watch?v=JGwWNGJdvx8
(Ed Sheeran - Shape of You)
