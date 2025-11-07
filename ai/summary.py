import os
from dotenv import load_dotenv
import google.generativeai as genai
from extract_text import extract_text
import sys

# Load environment variables
load_dotenv("/mnt/d/Projects/FUSEfs/.env")

# Configure API Key
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("ERROR: GEMINI_API_KEY is missing from .env")
    sys.exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def summarize_file(file_path):
    text = extract_text(file_path)
    if not text:
        return "No text extracted."
    
    prompt = f"Summarize into clear bullet points:\n\n{text}"
    response = model.generate_content(prompt)
    return response.text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ai_summary.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    summary = summarize_file(file_path)
    
    print("\n--- SUMMARY OUTPUT ---\n")
    print(summary)
    print("\n----------------------\n")
