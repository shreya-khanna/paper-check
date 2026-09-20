from google import genai
from google.genai import types
import os, time

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

paper_text = """
This is a short placeholder paper excerpt.
We test whether context-cached prompts reduce repeated upload cost.
"""

# 1) create cache
# NOTE: exact method names vary by SDK version.
# If this raises NotImplemented/InvalidArgument, caching is not enabled
# in the current SDK/model combination.
cache = client.caches.create(
    model="gemini-3.6-flash",
    config=types.CreateCachedContentConfig(
        contents=[types.Content(
            role="user",
            parts=[types.Part.from_text(paper_text)]
        )],
        ttl="3600s",
    )
)

print("CACHE NAME:", cache.name)

# 2) use cached content for a prompt
start = time.time()
resp = client.models.generate_content(
    model=cache.name,
    contents="What is the main idea of this paper?"
)
print("RESPONSE:", resp.text)
print("ELAPSED:", time.time() - start)