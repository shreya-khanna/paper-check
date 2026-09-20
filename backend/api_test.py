from google import genai

API_KEY = "PASTE_YOUR_AQ_KEY_HERE"

client = genai.Client(api_key=API_KEY)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Reply with exactly: HELLO"
)

print(response.text)