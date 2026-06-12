import os
import httpx
from dotenv import load_dotenv

load_dotenv(".env.production")
groq_key = os.getenv("GROQ_API_KEY")

res = httpx.get('https://api.groq.com/openai/v1/models', headers={'Authorization': f'Bearer {groq_key}'})
data = res.json()
print([m['id'] for m in data.get('data', []) if 'vision' in m['id']])
