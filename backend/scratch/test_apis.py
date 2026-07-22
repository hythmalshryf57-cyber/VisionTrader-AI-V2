# -*- coding: utf-8 -*-
import httpx, asyncio, os, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv('.env')

gemini_key = os.getenv('GEMINI_API_KEY', '')
or_key = os.getenv('OPENROUTER_API_KEY', '')

async def test_gemini():
    print("=== Testing Gemini ===")
    for version in ['v1beta']:
        for model in ['gemini-2.5-flash-lite-preview-06-17', 'gemini-2.5-flash', 'gemini-2.0-flash-lite', 'gemini-2.0-flash']:
            try:
                url = f'https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={gemini_key}'
                payload = {
                    'contents': [{'role': 'user', 'parts': [{'text': 'Say hello (2 words only)'}]}],
                    'generationConfig': {'maxOutputTokens': 10}
                }
                async with httpx.AsyncClient(timeout=12) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                        print(f"  OK ({version}): {model} -> {text.strip()[:40]}")
                        return model  # Return working model
                    else:
                        err_data = resp.json().get('error', {})
                        code = err_data.get('code')
                        msg = err_data.get('message', '')[:80]
                        print(f"  FAIL ({version}): {model} -> {code}: {msg}")
            except Exception as e:
                print(f"  ERROR ({version}): {model} -> {e}")
    return None

async def test_openrouter():
    print("\n=== Testing OpenRouter ===")
    for model in ['anthropic/claude-3-haiku', 'openai/gpt-4o-mini', 'meta-llama/llama-3.3-70b-instruct', 'google/gemini-2.0-flash-001']:
        try:
            url = 'https://openrouter.ai/api/v1/chat/completions'
            headers = {
                'Authorization': f'Bearer {or_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://visiontrader.ai',
                'X-Title': 'VisionTrader AI'
            }
            payload = {
                'model': model,
                'messages': [{'role': 'user', 'content': 'Say hello (2 words)'}],
                'max_tokens': 20
            }
            async with httpx.AsyncClient(timeout=12) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    content = resp.json()['choices'][0]['message']['content']
                    print(f"  OK: {model} -> {content.strip()[:40]}")
                    return model
                else:
                    err = resp.json().get('error', {})
                    print(f"  FAIL: {model} -> {resp.status_code}: {err.get('message', '')[:80]}")
        except Exception as e:
            print(f"  ERROR: {model} -> {e}")
    return None

async def main():
    g = await test_gemini()
    o = await test_openrouter()
    print(f"\n=== Results ===")
    print(f"Best Gemini model: {g}")
    print(f"Best OpenRouter model: {o}")

asyncio.run(main())
