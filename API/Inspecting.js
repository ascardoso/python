const { webkit } = require('playwright');

(async () => {
    const browser = await webkit.launch({
        headless: false
    });

    const page = await browser.newPage();

    await page.goto('https://www.wikipedia.org');

    const links = await page.locator('a').allTextContents();

    console.log('Links found:');

    links.forEach(link => {
        if (link.trim()) {
            console.log(link.trim());
        }
    });

    await browser.close();
})();
