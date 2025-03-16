# Suno Discord Bot

A Discord bot that lets you generate and play AI-created music from Suno directly in your Discord server's voice channels.

## Features

- Generate custom AI music with text prompts
- Play existing tracks from Suno by their ID
- Search for music in the Suno library
- Queue system for multiple songs
- Simple voice channel controls

## Prerequisites

Before setting up the bot, you'll need:

- A Discord account and the ability to create a bot
- A Suno account with API access
- Docker and Docker Compose (for the containerized setup)

## Setup Guide

### Step 1: Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Navigate to the "Bot" tab and click "Add Bot"
4. Under the "Privileged Gateway Intents" section, enable:
   - Message Content Intent
   - Server Members Intent
   - Presence Intent
5. Copy your bot token by clicking "Reset Token" or "Copy" (you'll need this later)
6. Go to the "OAuth2 > URL Generator" tab
7. Select the following scopes:
   - `bot`
   - `applications.commands`
8. Select the following bot permissions:
   - Send Messages
   - Connect
   - Speak
   - Read Message History
   - Use Embedded Activities
9. Copy the generated URL and open it in your browser to invite the bot to your server

### Step 2: Get Your Suno API Key

1. Log in to your Suno account
2. Navigate to your account settings or developer section
3. Generate or copy your API key

### Step 3: Set Up the Bot Files

1. Create a new directory for your bot
2. Save the following files in that directory:
   - `bot.py` (The main bot script)
   - `Dockerfile`
   - `requirements.txt`
   - `docker-compose.yml`
   
3. Create a `.env` file with the following contents:
   ```
   # Discord Bot Token
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   
   # Suno API Key
   SUNO_API_KEY=your_suno_api_key_here
   ```

4. Replace the placeholder values with your actual Discord bot token and Suno API key

### Step 4: Build and Run the Bot

1. Open a terminal and navigate to your bot directory
2. Run the following command to build and start the bot:
   ```bash
   docker-compose up -d
   ```
3. To check if the bot is running:
   ```bash
   docker-compose logs -f
   ```

4. You should see a message saying the bot has logged in, and it should now appear online in your Discord server

## Usage

### Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!suno help` | Show help information | `!suno help` |
| `!suno generate <prompt>` | Generate music based on your prompt | `!suno generate a happy birthday song with jazz piano` |
| `!suno play <generation_id>` | Play an existing Suno track by its ID | `!suno play abc123def456` |
| `!suno search <query>` | Search for existing Suno tracks | `!suno search electronic dance` |
| `!suno join` | Make the bot join your voice channel | `!suno join` |
| `!suno leave` | Make the bot leave the voice channel | `!suno leave` |
| `!suno queue` | Show the current queue | `!suno queue` |
| `!suno skip` | Skip the currently playing song | `!suno skip` |

### Workflow Examples

#### Generating and Playing AI Music

1. Join a voice channel in your Discord server
2. Type `!suno generate an upbeat electronic song with a catchy melody`
3. Wait for the bot to generate the music (this may take a minute)
4. The bot will join your voice channel and play the generated track

#### Playing Existing Tracks

1. Search for tracks: `!suno search jazz piano`
2. The bot will return a list of matching tracks with their IDs
3. Play a specific track: `!suno play abc123def456` (replace with an actual ID)
4. The bot will join your voice channel and play the selected track

## Troubleshooting

### Bot Doesn't Respond

- Check if the bot is online in your server
- Ensure the bot has the necessary permissions
- Check the bot logs with `docker-compose logs -f`

### Bot Can't Join Voice Channel

- Make sure you're in a voice channel before using commands
- Check if the bot has permission to join and speak in voice channels
- Ensure your Discord server allows bots to connect to voice channels

### Music Generation Fails

- Verify your Suno API key is correct in the `.env` file
- Check if you have sufficient credits/access on your Suno account
- Try with a simpler prompt

## Updating the Bot

1. Pull the latest code changes
2. Rebuild the Docker container:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

## Stopping the Bot

To stop the bot, run:
```bash
docker-compose down
```

## Technical Information

- Built with Python 3.11
- Uses discord.py for Discord API interaction
- Uses FFmpeg for audio processing
- Containerized with Docker for easy deployment

## License

This project is provided as-is with no warranties. Use at your own risk.

## Acknowledgements

- Discord.py library
- Suno AI for the music generation API
