import requests
import json
import os
import time

# --- Configuration ---
# IMPORTANT: Replace "YOUR_API_KEY" with your actual Google AI Studio API key.
# It's highly recommended to use an environment variable for security:
# os.environ["GOOGLE_API_KEY"] = "YOUR_API_KEY"
API_KEY = "AIzaSyBwckwrS6ay0x-7FbaZKmEnujGtCdXIX-U" 

# Choose a model that is typically free tier friendly
MODEL_NAME = 'gemini-1.5-flash' 
API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# Free tier limits (approximate, always check official documentation)
RPM_LIMIT = 15  # Requests per Minute
RPD_LIMIT = 1500 # Requests per Day
TPM_LIMIT = 1_000_000 # Tokens per Minute (input + output)

# --- Initialize ---
# Conversation history will be maintained manually
conversation_history = []

# Variables to track usage for free tier monitoring
request_count_minute = 0
request_count_day = 0
token_count_minute = 0 

start_time_minute = time.time()
start_time_day = time.time()

print(f"Welcome to the Gemini Chatbot (Model: {MODEL_NAME}) using requests!")
print("Type 'exit' to end the conversation.")
print("Type 'stats' to see your current usage for this session.")
print("\n--- Starting Conversation ---")

def send_gemini_request(messages, generation_config=None):
    """Sends a request to the Gemini API using requests library."""
    payload = {
        "contents": messages
    }
    if generation_config:
        payload["generationConfig"] = generation_config

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(API_ENDPOINT, headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        if response.status_code == 429:
            raise Exception("RESOURCE_EXHAUSTED: Rate limit exceeded.")
        raise Exception(f"API Error: {response.status_code} - {response.text}")

def count_tokens_request(text_to_count):
    """Estimates tokens using the countTokens API."""
    count_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:countTokens?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": text_to_count}]}]
    }
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(count_endpoint, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json().get("totalTokens", 0)
    except requests.exceptions.RequestException as e:
        print(f"Token count request failed: {e}")
        return 0 # Return 0 tokens on error for this utility function

while True:
    user_input = input("You: ")

    # Reset minute counters if a minute has passed
    if time.time() - start_time_minute >= 60:
        request_count_minute = 0
        token_count_minute = 0
        start_time_minute = time.time()

    if user_input.lower() == 'exit':
        break
    elif user_input.lower() == 'stats':
        elapsed_day_hours = (time.time() - start_time_day) / 3600
        print(f"\n--- Session Stats ---")
        print(f"Requests this minute: {request_count_minute}/{RPM_LIMIT}")
        print(f"Tokens this minute: {token_count_minute}/{TPM_LIMIT}")
        print(f"Requests today (session): {request_count_day}/{RPD_LIMIT} (elapsed: {elapsed_day_hours:.2f} hours)")
        print(f"---------------------\n")
        continue

    # Prepare message for the API call
    # The Gemini API expects messages in a specific format for chat history
    # Role 'user' for user input, 'model' for bot output
    new_user_message = {"role": "user", "parts": [{"text": user_input}]}
    
    # Add new user message to the history for the current request
    current_request_messages = conversation_history + [new_user_message]

    try:
        # Estimate input tokens
        # Note: This is an estimation. The actual token count is done by the API.
        # For full chat history, you'd ideally count the combined text of all messages
        # in `current_request_messages`. For simplicity here, we'll estimate from user input.
        # A more accurate way would be to send a `countTokens` request for the full `current_request_messages`.
        input_tokens = count_tokens_request(user_input) 

        if token_count_minute + input_tokens >= TPM_LIMIT:
             print(f"Bot: Warning: Approaching TPM limit ({TPM_LIMIT}). Input tokens ({input_tokens}) might exceed limit this minute. Please wait.")
             time.sleep(5) 
             continue 

        if request_count_minute >= RPM_LIMIT:
            print(f"Bot: Warning: Approaching RPM limit ({RPM_LIMIT}). Please wait a moment.")
            time.sleep(5) 
            continue
        
        if request_count_day >= RPD_LIMIT:
            print(f"Bot: Warning: Approaching RPD limit ({RPD_LIMIT}). You might hit daily limit soon.")
            
        # Send the full conversation history to the API
        api_response_json = send_gemini_request(current_request_messages)

        # Extract the text from the response
        model_response_text = ""
        if "candidates" in api_response_json and len(api_response_json["candidates"]) > 0:
            candidate = api_response_json["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                model_response_text = candidate["content"]["parts"][0].get("text", "")
        
        if not model_response_text:
            print("Bot: (No text response from model, or response was empty.)")
            # Check for safety ratings if no text content
            if "promptFeedback" in api_response_json and "safetyRatings" in api_response_json["promptFeedback"]:
                for rating in api_response_json["promptFeedback"]["safetyRatings"]:
                    if rating["blocked"] == True:
                        print(f"Bot: Note: Response was blocked due to safety settings for category: {rating['category']}")
            continue # Don't add empty response to history

        # Add user and model message to conversation history
        conversation_history.append(new_user_message)
        conversation_history.append({"role": "model", "parts": [{"text": model_response_text}]})

        # Count actual output tokens (after getting response)
        output_tokens = count_tokens_request(model_response_text)

        request_count_minute += 1
        request_count_day += 1
        token_count_minute += input_tokens + output_tokens # Sum of estimated input and actual output

        print(f"Bot: {model_response_text}")

    except Exception as e:
        print(f"An error occurred: {e}")
        if "RESOURCE_EXHAUSTED" in str(e):
            print("You likely hit a rate limit. Please wait a bit before trying again.")
            time.sleep(10) # Longer wait for rate limit errors
        else:
            print("Please try again.")

print("\nConversation ended. Goodbye!")
print(f"Total requests in this session: {request_count_day}")