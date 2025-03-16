FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install FFmpeg and other dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code
COPY bot.py .

# Create a directory for temporary files
RUN mkdir -p /tmp/suno_bot

# Set environment variables
ENV TEMP_DIR=/tmp/suno_bot

# Command to run the bot
CMD ["python", "bot.py"]
