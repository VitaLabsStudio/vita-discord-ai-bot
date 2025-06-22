#!/usr/bin/env python3
"""Test script to verify ingestion pipeline works correctly."""

import asyncio
import aiohttp
import json

async def test_ingestion():
    """Test the ingestion endpoint with a simple message."""
    backend_url = "http://localhost:8001"
    
    # Test single message ingestion
    test_message = {
        "message_id": "test_123",
        "channel_id": "test_channel_123",
        "user_id": "test_user_123",
        "content": "This is a test message to verify the ingestion pipeline is working correctly.",
        "timestamp": "2024-01-01T00:00:00Z",
        "attachments": [],
        "thread_id": None,
        "roles": ["test_role"]
    }
    
    print("Testing single message ingestion...")
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{backend_url}/ingest", json=test_message) as resp:
            print(f"Status: {resp.status}")
            response_text = await resp.text()
            print(f"Response: {response_text}")
    
    # Test batch ingestion
    test_batch = {
        "messages": [
            {
                "message_id": "test_batch_1",
                "channel_id": "test_channel_123",
                "user_id": "test_user_123",
                "content": "First test message in batch.",
                "timestamp": "2024-01-01T00:00:00Z",
                "attachments": [],
                "thread_id": None,
                "roles": ["test_role"]
            },
            {
                "message_id": "test_batch_2",
                "channel_id": "test_channel_123",
                "user_id": "test_user_123",
                "content": "Second test message in batch.",
                "timestamp": "2024-01-01T00:00:01Z",
                "attachments": [],
                "thread_id": None,
                "roles": ["test_role"]
            }
        ]
    }
    
    print("\nTesting batch message ingestion...")
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{backend_url}/batch_ingest", json=test_batch) as resp:
            print(f"Status: {resp.status}")
            response_text = await resp.text()
            print(f"Response: {response_text}")

if __name__ == "__main__":
    asyncio.run(test_ingestion()) 