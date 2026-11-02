import openai
# If you set the key in code, uncomment the next line:
openai.api_key = "sk-…"

model_id = "gpt-4o"          # Replace with any model name you want
model_info = openai.Model.retrieve(model_id)

# The property that holds the context window is called `context_length`
print(f"Model: {model_id}")
print(f"Max context length (tokens): {model_info.context_length}")

