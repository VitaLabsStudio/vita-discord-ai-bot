import os
import discord
from dotenv import load_dotenv
import aiohttp
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

BACKEND_URL = "http://localhost:8000/ingest"
ASK_URL = "http://localhost:8000/ask"

@bot.event
async def on_ready():
    """Event handler for when the bot is ready."""
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message: discord.Message) -> None:
    """Event handler for new messages. Sends message to backend for ingestion."""
    if message.author == bot.user:
        return
    payload = {
        "id": str(message.id),
        "content": message.content,
        "author_id": str(message.author.id),
        "channel_id": str(message.channel.id),
        "thread_id": str(message.thread.id) if message.thread else None,
        "timestamp": str(message.created_at),
        "attachments": [a.url for a in message.attachments],
        "roles": [role.name for role in getattr(message.author, 'roles', []) if hasattr(message.author, 'roles')]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(BACKEND_URL, json=payload) as resp:
            _ = await resp.json()
    await bot.process_commands(message)

@bot.command()
async def ask(ctx: commands.Context, *, question: str):
    """Ask a question to the knowledge assistant."""
    user_roles = [role.name for role in getattr(ctx.author, 'roles', []) if hasattr(ctx.author, 'roles')]
    channel_id = str(ctx.channel.id)
    payload = {
        "question": question,
        "user_roles": user_roles,
        "channel_id": channel_id,
        "top_k": 5
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(ASK_URL, json=payload) as resp:
            data = await resp.json()
    answer = data.get("answer", "No answer.")
    citations = data.get("citations", [])
    confidence = data.get("confidence", 0)
    await ctx.send(f"**Answer:** {answer}\n**Citations:** {citations}\n**Confidence:** {confidence:.2f}")

@bot.command()
async def delete(ctx: commands.Context, msg_id: str):
    """Delete your own message and its chunk from the knowledge base."""
    payload = {"msg_id": msg_id}
    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8000/delete", json=payload) as resp:
            data = await resp.json()
    if data.get("removed"):
        await ctx.send(f"Message {msg_id} and its chunk have been deleted.")
    else:
        await ctx.send(f"Message {msg_id} not found or not deleted.")

@bot.command()
async def feedback(ctx: commands.Context, chunk_id: str, feedback: str):
    """Provide feedback (like/dislike/flag) for a chunk."""
    payload = {"chunk_id": chunk_id, "feedback": feedback}
    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8000/feedback", json=payload) as resp:
            data = await resp.json()
    await ctx.send(f"Feedback recorded for chunk {chunk_id}.")

if __name__ == "__main__":
    bot.run(TOKEN) 