# Discord bot logic will be implemented here 

import os
import discord
from discord.ext import commands
from discord import app_commands, Interaction
from dotenv import load_dotenv
import aiohttp
import asyncio
from typing import Any, Dict, List, Optional
from src.backend.utils import clean_text, redact_pii

load_dotenv()

DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8001")

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True
intents.reactions = True
intents.typing = False

class MyBot(commands.Bot):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.http_session: Optional[aiohttp.ClientSession] = None

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession()
        await self.add_cog(CommandCog(self))
        try:
            for guild in self.guilds:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            print("Slash commands synced.")
        except Exception as e:
            print(f"Error syncing commands: {e}")

    async def close(self) -> None:
        if self.http_session:
            await self.http_session.close()
        await super().close()

bot = MyBot(command_prefix="!", intents=intents)

def get_user_roles(member: discord.abc.User) -> List[str]:
    """Get a list of role names for a user if available."""
    if hasattr(member, "roles"):
        return [role.name for role in member.roles if role.name != "@everyone"]
    return []

@bot.event
async def on_ready() -> None:
    """Event handler for when the bot is ready."""
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

@bot.event
async def on_message(message: discord.Message) -> None:
    """Event handler for new messages. Sends to backend for ingestion if not from bot."""
    if message.author.bot or not bot.http_session:
        return

    ingest_payload: Dict[str, Any] = {
        "message_id": str(message.id),
        "channel_id": str(message.channel.id),
        "user_id": str(message.author.id),
        "content": message.content,
        "timestamp": message.created_at.isoformat(),
        "attachments": [a.url for a in message.attachments],
        "thread_id": str(message.thread.id) if message.thread else None,
        "roles": get_user_roles(message.author),
    }
    try:
        async with bot.http_session.post(f"{BACKEND_URL}/ingest", json=ingest_payload) as resp:
            if resp.status != 200:
                print(f"Ingestion failed: {resp.status}, {await resp.text()}")
    except Exception as e:
        print(f"Error sending to backend: {e}")

class CommandCog(commands.Cog):
    def __init__(self, bot: MyBot):
        self.bot = bot

    async def cog_check(self, interaction: Interaction) -> bool:
        # Ensure the session is available for all commands
        return self.bot.http_session is not None and not self.bot.http_session.closed

    @app_commands.command(name="ask", description="Ask the knowledge assistant a question.")
    async def ask(self, interaction: Interaction, question: str) -> None:
        """Handles the /ask command, sending the question to the backend and returning the answer."""
        await interaction.response.defer()
        user_roles = get_user_roles(interaction.user)
        payload = {
            "user_id": str(interaction.user.id),
            "channel_id": str(interaction.channel.id),
            "roles": user_roles,
            "question": question,
            "top_k": 5
        }
        
        assert self.bot.http_session is not None
        try:
            async with self.bot.http_session.post(f"{BACKEND_URL}/query", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    answer = data.get("answer", "No answer could be generated.")
                    citations = data.get("citations", [])
                    confidence = data.get("confidence", 0.0)
                    
                    citation_links = [f"https://discord.com/channels/{interaction.guild_id}/{c.get('channel_id')}/{c.get('message_id')}" for c in citations]
                    citation_text = "\n".join(f"- <{link}>" for link in citation_links) if citation_links else "No citations found."

                    embed = discord.Embed(
                        title="VITA's Answer",
                        description=answer,
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="Confidence", value=f"{confidence:.2%}", inline=True)
                    embed.add_field(name="Citations", value=citation_text, inline=False)
                    
                    await interaction.followup.send(embed=embed)
                else:
                    error_text = await resp.text()
                    await interaction.followup.send(f"Sorry, there was an error processing your question. ({resp.status}):\n`{error_text}`")
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred while contacting the backend: {e}")

    @app_commands.command(name="delete", description="Delete your own message from the knowledge base.")
    async def delete(self, interaction: Interaction, message_id: str) -> None:
        """Allows a user to delete their own message from the knowledge base."""
        await interaction.response.defer()
        payload = {"user_id": str(interaction.user.id), "message_id": message_id}
        async with self.bot.http_session.post(f"{BACKEND_URL}/delete", json=payload) as resp:
            if resp.status == 200:
                await interaction.followup.send("Message deleted from knowledge base.")
            else:
                await interaction.followup.send("Failed to delete message.")

    @app_commands.command(name="redact", description="Redact your own message in the knowledge base.")
    async def redact(self, interaction: Interaction, message_id: str) -> None:
        """Allows a user to redact their own message in the knowledge base."""
        await interaction.response.defer()
        payload = {"user_id": str(interaction.user.id), "message_id": message_id}
        async with self.bot.http_session.post(f"{BACKEND_URL}/redact", json=payload) as resp:
            if resp.status == 200:
                await interaction.followup.send("Message redacted in knowledge base.")
            else:
                await interaction.followup.send("Failed to redact message.")

    @app_commands.command(name="feedback", description="Give feedback on a bot answer.")
    async def feedback(self, interaction: Interaction, message_id: str, feedback: str, comment: str = "") -> None:
        """Allows a user to give feedback (up/down/flag) on a bot answer."""
        await interaction.response.defer()
        payload = {
            "user_id": str(interaction.user.id),
            "message_id": message_id,
            "feedback": feedback,
            "comment": comment
        }
        async with self.bot.http_session.post(f"{BACKEND_URL}/feedback", json=payload) as resp:
            if resp.status == 200:
                await interaction.followup.send("Feedback logged. Thank you!")
            else:
                await interaction.followup.send("Failed to log feedback.")

    @app_commands.command(name="ingest_history", description="Ingest the message history of this server (Admins only).")
    @app_commands.checks.has_permissions(administrator=True)
    async def ingest_history(self, interaction: Interaction) -> None:
        """Fetches and ingests all historical messages from all channels with robust feedback."""
        await interaction.response.send_message("✅ Starting historical ingestion. This may take a while...", ephemeral=True)
        
        guild = interaction.guild
        if not guild or not self.bot.http_session:
            await interaction.edit_original_response(content="❌ This command can only be used in a server or the bot is not ready.")
            return
        
        print("Starting historical ingestion process...")
        
        total_ingested = 0
        total_failed = 0
        
        text_channels = [c for c in guild.text_channels if c.permissions_for(guild.me).read_message_history]
        
        if not text_channels:
            await interaction.edit_original_response(content="❌ I don't have permission to read message history in any channels.")
            return

        status_message = await interaction.followup.send(f"Found {len(text_channels)} channels to process. Starting...", ephemeral=True)

        for i, channel in enumerate(text_channels):
            print(f"[{i+1}/{len(text_channels)}] Fetching history for #{channel.name}...")
            await status_message.edit(content=f"⚙️ Processing channel #{channel.name} ({i+1}/{len(text_channels)})...\nTotal ingested so far: {total_ingested}")
            
            try:
                message_batch = []
                async for message in channel.history(limit=None):
                    if message.author.bot or (not message.content and not message.attachments):
                        continue
                    
                    message_batch.append({
                        "message_id": str(message.id),
                        "channel_id": str(message.channel.id),
                        "user_id": str(message.author.id),
                        "content": message.content,
                        "timestamp": message.created_at.isoformat(),
                        "attachments": [a.url for a in message.attachments],
                        "thread_id": str(message.thread.id) if message.thread else None,
                        "roles": get_user_roles(message.author),
                    })

                    if len(message_batch) >= 50:
                        async with self.bot.http_session.post(f"{BACKEND_URL}/batch_ingest", json={"messages": message_batch}) as resp:
                            if resp.status == 200:
                                result = await resp.json()
                                total_ingested += result.get("processed", 0)
                                total_failed += result.get("failed", 0)
                            else:
                                total_failed += len(message_batch)
                                print(f"Batch failed for #{channel.name} with status {resp.status}")
                        message_batch = []
                
                if message_batch:
                    async with self.bot.http_session.post(f"{BACKEND_URL}/batch_ingest", json={"messages": message_batch}) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            total_ingested += result.get("processed", 0)
                            total_failed += result.get("failed", 0)
                        else:
                            total_failed += len(message_batch)
                            print(f"Final batch failed for #{channel.name} with status {resp.status}")
            except discord.Forbidden:
                print(f"Permissions error in #{channel.name}. Skipping.")
                continue
            except Exception as e:
                print(f"Unexpected error in #{channel.name}: {e}")
                continue

        await status_message.edit(content=f"✅ Historical ingestion complete!\n- Processed {total_ingested} messages successfully.\n- Failed to process {total_failed} messages.")

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN is not set in the environment.")
    
    asyncio.run(bot.start(DISCORD_BOT_TOKEN)) 