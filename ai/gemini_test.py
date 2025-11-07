import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv(".env")

# Configure API KEY
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Select a valid model
model = genai.GenerativeModel("models/gemini-2.5-pro")

# Make a request
response = model.generate_content("Explain CPU scheduling in simple terms.")

print(response.text)
