"""Quick Gemini API verification — run once during Phase 1 setup, then delete."""

import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.config import get_settings

settings = get_settings()

if not settings.gemini_api_key or settings.gemini_api_key == "your_key_here":
    print("❌  GEMINI_API_KEY is not set in .env")
    print("    Go to https://aistudio.google.com  →  Get API Key  →  paste into .env")
    sys.exit(1)

import google.generativeai as genai

genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

print("Testing Gemini 1.5 Flash...")
response = model.generate_content("Say 'WoxBot is alive!' and nothing else.")
print(f"✅  Gemini responded: {response.text.strip()}")

# Also verify embedding model
print(f"\nTesting embedding model ({settings.embedding_model_version})...")
result = genai.embed_content(
    model=f"models/{settings.embedding_model_version}",
    content="Woxsen University test embedding",
)
vec = result["embedding"]
print(f"✅  Embedding returned vector of dimension {len(vec)}")
print("\n🎉  Gemini API is fully working. Ready for Phase 2.")
