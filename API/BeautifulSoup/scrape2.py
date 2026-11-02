# pip install playwright beautifulsoup4
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://platform.openai.com/docs/models")

        # Wait until the table is rendered
        await page.wait_for_selector("table")   # adjust if needed

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")

        rows = table.find_all("tr")[1:]  # skip header
        for r in rows:
            cells = r.find_all("td")
            name, context = cells[0].text.strip(), cells[1].text.strip()
            print(f"{name:25} → {context}")

        await browser.close()

asyncio.run(scrape())

