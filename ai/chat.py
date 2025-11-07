import os
from dotenv import load_dotenv
import google.generativeai as genai

# python3 AI_Module/ai_chat.py

# Load the .env file from project root
load_dotenv("/mnt/d/Projects/FUSEfs/.env")

# Configure API
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("ERROR: GEMINI_API_KEY not found in .env")
    exit()

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.0-flash")

def chat(prompt):
    response = model.generate_content(prompt)
    return response.text

print("AI Chat Ready. Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break
    reply = chat(user_input)
    print("AI:", reply, "\n")

