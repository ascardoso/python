import openai

model = "gpt-4o"
info = openai.Model.retrieve(model)
print(info.context_length)   # → 128000

