# list_gemini_models.py

import os
import google.generativeai as genai

# Load API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("Please set the GEMINI_API_KEY environment variable.")

# Configure the API client
genai.configure(api_key=GEMINI_API_KEY)

# Fetch and print all available models
try:
    models = genai.list_models()
    print("Available Gemini Models:\n")
    for model in models:
        print(f"Name: {model.name}")
        print(f"  Description: {getattr(model, 'description', 'No description')}")
        print(f"  Input Token Limit: {getattr(model, 'input_token_limit', 'Unknown')}")
        print(f"  Output Token Limit: {getattr(model, 'output_token_limit', 'Unknown')}")
        print(f"  Supported Modalities: {getattr(model, 'supported_generation_methods', 'Unknown')}")
        print("-" * 50)
except Exception as e:
    print(f"Error fetching models: {e}")
