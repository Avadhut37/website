#!/usr/bin/env python3
"""Test all OpenRouter models including DeepSeek."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.ai.providers.openrouter import OpenRouterProvider
from app.core.config import settings


# All available free models on OpenRouter
FREE_MODELS = [
    "meta-llama/llama-3.2-3b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "qwen/qwen-2-7b-instruct:free",
    "huggingfaceh4/zephyr-7b-beta:free",
]

# DeepSeek models available via OpenRouter
DEEPSEEK_MODELS = [
    "deepseek/deepseek-chat",
    "deepseek/deepseek-coder",
    "deepseek/deepseek-r1",
    "deepseek/deepseek-r1-distill-llama-70b",
]


async def test_model(model_name: str) -> dict:
    """Test a specific model."""
    provider = OpenRouterProvider(model=model_name)
    
    if not provider.is_available():
        return {
            "model": model_name,
            "status": "❌ NO API KEY",
            "response": None,
            "error": "OpenRouter API key not configured"
        }
    
    test_prompt = "Reply with: 'Hello from {model_name}!'"
    
    try:
        response = await provider.generate(
            prompt=test_prompt,
            max_tokens=100,
            temperature=0.7
        )
        
        if response and len(response) > 0:
            return {
                "model": model_name,
                "status": "✅ SUCCESS",
                "response": response[:200],
                "chars": len(response)
            }
        else:
            return {
                "model": model_name,
                "status": "❌ EMPTY RESPONSE",
                "response": None,
                "error": "No response returned"
            }
            
    except Exception as e:
        return {
            "model": model_name,
            "status": "❌ ERROR",
            "response": None,
            "error": str(e)
        }


async def main():
    """Test all models."""
    print("=" * 80)
    print("OPENROUTER MODEL TEST")
    print("=" * 80)
    print()
    
    # Check API key
    if not settings.OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY not found in environment!")
        print("   Set it in backend/.env file")
        return
    
    print(f"✅ API Key configured: {settings.OPENROUTER_API_KEY[:20]}...")
    print()
    
    # Test FREE models
    print("=" * 80)
    print("TESTING FREE MODELS")
    print("=" * 80)
    print()
    
    for model in FREE_MODELS:
        print(f"Testing: {model}")
        result = await test_model(model)
        print(f"  Status: {result['status']}")
        if result['response']:
            print(f"  Response ({result['chars']} chars): {result['response'][:100]}...")
        elif result.get('error'):
            print(f"  Error: {result['error']}")
        print()
        await asyncio.sleep(1)  # Rate limiting
    
    # Test DEEPSEEK models via OpenRouter
    print("=" * 80)
    print("TESTING DEEPSEEK MODELS (via OpenRouter)")
    print("=" * 80)
    print()
    
    for model in DEEPSEEK_MODELS:
        print(f"Testing: {model}")
        result = await test_model(model)
        print(f"  Status: {result['status']}")
        if result['response']:
            print(f"  Response ({result['chars']} chars): {result['response'][:100]}...")
        elif result.get('error'):
            print(f"  Error: {result['error']}")
        print()
        await asyncio.sleep(1)  # Rate limiting
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
