# Use a lightweight Python version
FROM python:3.10-slim

# Install FFmpeg (Required for video merging) and Git
RUN apt-get update && \
    apt-get install -y ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy all your files into the container
COPY . .

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Start the bot
CMD ["python", "main.py"]
