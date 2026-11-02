import requests
from bs4 import BeautifulSoup

url = "https://platform.openai.com/docs/models"
resp = requests.get(url)
soup = BeautifulSoup(resp.text, "html.parser")

# Find the table that lists models
table = soup.find("table")          # first <table> element in the page
rows = table.find_all("tr")[1:]      # skip header row

for r in rows:
    cells = r.find_all("td")
    name, context = cells[0].text.strip(), cells[1].text.strip()
    print(f"{name:25} → {context}")

