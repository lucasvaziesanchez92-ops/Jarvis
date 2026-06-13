import os
import base64
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

client = ChatOpenAI(
    model="gemini-2.5-pro",
    api_key=os.environ.get("GEMINI_API_KEY", ""),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# create a simple white pixel base64 image
b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/w8AAwAB/2+Bq74AAAAASUVORK5CYII="

msg = HumanMessage(
    content=[
        {"type": "text", "text": "What color is this image?"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
    ]
)

try:
    print(client.invoke([msg]).content)
except Exception as e:
    print("Error:", e)
