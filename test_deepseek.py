#!/usr/bin/env python3
"""Test script to verify Deepseek API connection and available models."""

import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_deepseek():
    """Test Deepseek API connection."""
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY not set")
        return
    
    print(f"Testing with API key: {api_key[:10]}...")
    
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1"
    )
    
    try:
        # Test models endpoint
        print("Testing models endpoint...")
        models = await client.models.list()
        print(f"Available models: {[m.id for m in models.data]}")
        
        # Test embedding
        print("\nTesting embedding...")
        response = await client.embeddings.create(
            input=["test message"],
            model="deepseek-embedding"
        )
        print(f"Embedding successful: {len(response.data[0].embedding)} dimensions")
        
        # Test chat completion
        print("\nTesting chat completion...")
        completion = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print(f"Chat completion successful: {completion.choices[0].message.content}")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_deepseek()) 