import os
import asyncio
import discord
from discord.ext import commands
import aiohttp
import json
import tempfile
import logging
from typing import Optional, Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('suno-bot')

# Bot configuration
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_API_URL = "https://api.suno.ai/v1"

# Check if environment variables are set
if not BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN environment variable is not set")
if not SUNO_API_KEY:
    raise ValueError("SUNO_API_KEY environment variable is not set")

# Define intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot
bot = commands.Bot(command_prefix='!', intents=intents)

class SunoClient:
    """Client for interacting with the Suno API"""
    
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_music(self, prompt: str, style: Optional[str] = None) -> Dict[str, Any]:
        """Generate music using Suno API"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "prompt": prompt,
            }
            
            if style:
                payload["style"] = style
            
            async with session.post(
                f"{self.api_url}/generations", 
                headers=self.headers, 
                json=payload
            ) as response:
                if response.status != 202:
                    error_text = await response.text()
                    logger.error(f"Failed to generate music: {error_text}")
                    raise Exception(f"Failed to generate music: {error_text}")
                
                response_data = await response.json()
                generation_id = response_data.get("id")
                
                if not generation_id:
                    raise Exception("No generation ID in response")
                
                return await self._poll_generation(session, generation_id)
    
    async def _poll_generation(self, session: aiohttp.ClientSession, generation_id: str) -> Dict[str, Any]:
        """Poll for generation completion"""
        max_attempts = 60
        for attempt in range(max_attempts):
            async with session.get(
                f"{self.api_url}/generations/{generation_id}", 
                headers=self.headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to get generation status: {error_text}")
                    raise Exception(f"Failed to get generation status: {error_text}")
                
                data = await response.json()
                status = data.get("status")
                
                if status == "completed":
                    return data
                elif status == "failed":
                    raise Exception(f"Generation failed: {data.get('error')}")
                
                # Wait before trying again
                await asyncio.sleep(5)
        
        raise Exception("Generation timed out")
    
    async def get_generation(self, generation_id: str) -> Dict[str, Any]:
        """Get information about an existing generation"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_url}/generations/{generation_id}", 
                headers=self.headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to get generation: {error_text}")
                    raise Exception(f"Failed to get generation: {error_text}")
                
                return await response.json()
    
    async def get_audio_url(self, generation_id: str) -> str:
        """Get the audio URL for a completed generation"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_url}/generations/{generation_id}/audio", 
                headers=self.headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to get audio URL: {error_text}")
                    raise Exception(f"Failed to get audio URL: {error_text}")
                
                data = await response.json()
                return data.get("url")
    
    async def download_audio(self, url: str) -> str:
        """Download the audio file and return the local path"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to download audio: {error_text}")
                    raise Exception(f"Failed to download audio: {error_text}")
                
                # Create temporary file
                fd, path = tempfile.mkstemp(suffix=".mp3")
                with os.fdopen(fd, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
                
                return path
    
    async def search_generations(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for public generations on Suno"""
        async with aiohttp.ClientSession() as session:
            params = {
                "query": query,
                "limit": limit
            }
            async with session.get(
                f"{self.api_url}/search/generations",
                headers=self.headers,
                params=params
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to search generations: {error_text}")
                    raise Exception(f"Failed to search generations: {error_text}")
                
                data = await response.json()
                return data.get("results", [])

class MusicPlayer:
    """Handles music playback in voice channels"""
    
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}  # guild_id -> voice_client
        self.queues = {}  # guild_id -> list of songs
        self.current_songs = {}  # guild_id -> current song info
    
    def get_queue(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get the queue for a guild"""
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]
    
    def add_to_queue(self, guild_id: int, song_info: Dict[str, Any]):
        """Add a song to the queue"""
        queue = self.get_queue(guild_id)
        queue.append(song_info)
    
    async def join_voice_channel(self, voice_channel: discord.VoiceChannel) -> discord.VoiceClient:
        """Join a voice channel"""
        guild_id = voice_channel.guild.id
        
        # Check if already connected
        if guild_id in self.voice_clients and self.voice_clients[guild_id].is_connected():
            return self.voice_clients[guild_id]
        
        # Connect to voice channel
        voice_client = await voice_channel.connect()
        self.voice_clients[guild_id] = voice_client
        return voice_client
    
    async def leave_voice_channel(self, guild_id: int):
        """Leave the voice channel in a guild"""
        if guild_id in self.voice_clients:
            voice_client = self.voice_clients[guild_id]
            if voice_client.is_connected():
                await voice_client.disconnect()
            del self.voice_clients[guild_id]
        
        # Clear queue
        if guild_id in self.queues:
            del self.queues[guild_id]
        
        if guild_id in self.current_songs:
            del self.current_songs[guild_id]
    
    async def play(self, guild_id: int):
        """Play songs from the queue"""
        if guild_id not in self.voice_clients:
            return
        
        voice_client = self.voice_clients[guild_id]
        
        if voice_client.is_playing():
            return
        
        queue = self.get_queue(guild_id)
        
        if not queue:
            # Queue is empty
            await self.leave_voice_channel(guild_id)
            return
        
        # Get the next song
        song_info = queue.pop(0)
        self.current_songs[guild_id] = song_info
        
        # Play the song
        voice_client.play(
            discord.FFmpegPCMAudio(song_info["file_path"]),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self._song_finished(guild_id, e), self.bot.loop
            )
        )
    
    async def _song_finished(self, guild_id: int, error):
        """Called when a song finishes playing"""
        if error:
            logger.error(f"Error playing song: {error}")
        
        # Clean up temp file
        if guild_id in self.current_songs:
            try:
                os.remove(self.current_songs[guild_id]["file_path"])
            except Exception as e:
                logger.error(f"Error removing temp file: {e}")
        
        # Play next song
        await self.play(guild_id)
    
    async def skip(self, guild_id: int) -> bool:
        """Skip the current song"""
        if guild_id not in self.voice_clients:
            return False
        
        voice_client = self.voice_clients[guild_id]
        
        if not voice_client.is_playing():
            return False
        
        voice_client.stop()
        return True

# Initialize Suno client and music player
suno_client = SunoClient(SUNO_API_KEY, SUNO_API_URL)
music_player = MusicPlayer(bot)

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    logger.info(f'Logged in as {bot.user.name} ({bot.user.id})')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!suno help"))

@bot.command(name="suno")
async def suno(ctx, *args):
    """Main command for Suno bot"""
    if not args:
        await ctx.send("Usage: `!suno <command>`. Try `!suno help` for a list of commands.")
        return
    
    command = args[0].lower()
    
    if command == "help":
        await suno_help(ctx)
    elif command == "generate":
        if len(args) < 2:
            await ctx.send("Please provide a prompt for music generation. Example: `!suno generate a happy birthday song`")
            return
        
        prompt = " ".join(args[1:])
        await generate_music(ctx, prompt)
    elif command == "play":
        if len(args) < 2:
            await ctx.send("Please provide a generation ID to play. Example: `!suno play abc123`")
            return
        
        generation_id = args[1]
        await play_existing(ctx, generation_id)
    elif command == "search":
        if len(args) < 2:
            await ctx.send("Please provide a search query. Example: `!suno search electronic`")
            return
        
        query = " ".join(args[1:])
        await search_tracks(ctx, query)
    elif command == "join":
        await join(ctx)
    elif command == "leave":
        await leave(ctx)
    elif command == "queue":
        await show_queue(ctx)
    elif command == "skip":
        await skip(ctx)
    else:
        await ctx.send(f"Unknown command: {command}. Try `!suno help` for a list of commands.")

async def suno_help(ctx):
    """Show help information"""
    help_text = """
**Suno Discord Bot Commands**

`!suno help` - Show this help message
`!suno generate <prompt>` - Generate music based on your prompt
`!suno play <generation_id>` - Play an existing Suno track by its ID
`!suno search <query>` - Search for existing Suno tracks
`!suno join` - Make the bot join your voice channel
`!suno leave` - Make the bot leave the voice channel
`!suno queue` - Show the current queue
`!suno skip` - Skip the currently playing song

Examples:
`!suno generate an upbeat electronic song with a catchy melody`
`!suno play abc123def456`
`!suno search jazz piano`
"""
    await ctx.send(help_text)

async def join(ctx):
    """Join the user's voice channel"""
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel to use this command.")
        return
    
    voice_channel = ctx.author.voice.channel
    await music_player.join_voice_channel(voice_channel)
    await ctx.send(f"Joined {voice_channel.name}")

async def leave(ctx):
    """Leave the voice channel"""
    guild_id = ctx.guild.id
    await music_player.leave_voice_channel(guild_id)
    await ctx.send("Left the voice channel")

async def generate_music(ctx, prompt):
    """Generate music using Suno API and play it"""
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel to use this command.")
        return
    
    # Join voice channel if not already connected
    voice_channel = ctx.author.voice.channel
    await music_player.join_voice_channel(voice_channel)
    
    message = await ctx.send(f"🎵 Generating music based on: '{prompt}'... This might take a minute.")
    
    try:
        # Generate music
        generation = await suno_client.generate_music(prompt)
        generation_id = generation.get("id")
        
        # Update message
        await message.edit(content=f"✅ Music generated! Processing audio...")
        
        # Get audio URL
        audio_url = await suno_client.get_audio_url(generation_id)
        
        # Download audio
        file_path = await suno_client.download_audio(audio_url)
        
        # Add to queue
        song_info = {
            "title": prompt,
            "generation_id": generation_id,
            "file_path": file_path
        }
        
        guild_id = ctx.guild.id
        music_player.add_to_queue(guild_id, song_info)
        
        # Update message
        await message.edit(content=f"🎶 Added to queue: '{prompt}' (ID: {generation_id})")
        
        # Start playing if not already playing
        await music_player.play(guild_id)
        
    except Exception as e:
        logger.error(f"Error generating music: {e}")
        await message.edit(content=f"❌ Error generating music: {str(e)}")

async def play_existing(ctx, generation_id):
    """Play an existing generated track by its ID"""
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel to use this command.")
        return
    
    # Join voice channel if not already connected
    voice_channel = ctx.author.voice.channel
    await music_player.join_voice_channel(voice_channel)
    
    message = await ctx.send(f"🔍 Looking up track with ID: '{generation_id}'...")
    
    try:
        # Get generation info
        generation = await suno_client.get_generation(generation_id)
        prompt = generation.get("prompt", "Unknown track")
        
        # Update message
        await message.edit(content=f"✅ Track found: '{prompt}'. Processing audio...")
        
        # Get audio URL
        audio_url = await suno_client.get_audio_url(generation_id)
        
        # Download audio
        file_path = await suno_client.download_audio(audio_url)
        
        # Add to queue
        song_info = {
            "title": prompt,
            "generation_id": generation_id,
            "file_path": file_path
        }
        
        guild_id = ctx.guild.id
        music_player.add_to_queue(guild_id, song_info)
        
        # Update message
        await message.edit(content=f"🎶 Added to queue: '{prompt}' (ID: {generation_id})")
        
        # Start playing if not already playing
        await music_player.play(guild_id)
        
    except Exception as e:
        logger.error(f"Error playing track: {e}")
        await message.edit(content=f"❌ Error playing track: {str(e)}")

async def search_tracks(ctx, query):
    """Search for existing tracks on Suno"""
    message = await ctx.send(f"🔍 Searching for tracks matching: '{query}'...")
    
    try:
        # Search for tracks
        results = await suno_client.search_generations(query)
        
        if not results:
            await message.edit(content=f"No tracks found for '{query}'.")
            return
        
        # Create embed with results
        embed = discord.Embed(
            title=f"Search Results for '{query}'",
            color=discord.Color.blue()
        )
        
        for i, result in enumerate(results, 1):
            generation_id = result.get("id")
            prompt = result.get("prompt", "Unknown track")
            
            embed.add_field(
                name=f"{i}. {prompt[:50] + '...' if len(prompt) > 50 else prompt}",
                value=f"ID: `{generation_id}`\nUse `!suno play {generation_id}` to play this track",
                inline=False
            )
        
        await message.edit(content=None, embed=embed)
        
    except Exception as e:
        logger.error(f"Error searching tracks: {e}")
        await message.edit(content=f"❌ Error searching tracks: {str(e)}")

async def show_queue(ctx):
    """Show the current queue"""
    guild_id = ctx.guild.id
    queue = music_player.get_queue(guild_id)
    
    if not queue and guild_id not in music_player.current_songs:
        await ctx.send("The queue is empty.")
        return
    
    queue_text = "**Current Queue**\n\n"
    
    if guild_id in music_player.current_songs:
        current_song = music_player.current_songs[guild_id]
        queue_text += f"**Now Playing:** {current_song['title']} (ID: {current_song['generation_id']})\n\n"
    
    if queue:
        queue_text += "**Up Next:**\n"
        for i, song in enumerate(queue, 1):
            queue_text += f"{i}. {song['title']} (ID: {song['generation_id']})\n"
    else:
        queue_text += "**Up Next:** Nothing in queue"
    
    await ctx.send(queue_text)

async def skip(ctx):
    """Skip the current song"""
    guild_id = ctx.guild.id
    
    if await music_player.skip(guild_id):
        await ctx.send("Skipped to the next song.")
    else:
        await ctx.send("Nothing is playing right now.")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
