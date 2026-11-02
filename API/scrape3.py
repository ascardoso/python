import requests
import re

url = "https://raw.githubusercontent.com/openai/openai-quickstart/master/models.md"
text = requests.get(url).text

# The table is a Markdown block.  Grab the rows.
rows = re.findall(r"\|\s*([^\|]+)\s*\|\s*([^\|]+)\s*\|\s*([^\|]+)\s*\|", text)

for name, max_tokens, _ in rows:
    print(f"{name.strip():25} → {max_tokens.strip()}")

