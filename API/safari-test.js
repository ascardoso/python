
const { webkit } = require('playwright');

async function main() {

    // Launch WebKit browser visibly
    const browser = await webkit.launch({
        headless: false
    });

    // Create a browser tab
    const page = await browser.newPage();

    // Navigate to a website
    console.log('Opening website...');

    await page.goto('https://www.wikipedia.org');

    // Get the page title
    const title = await page.title();

    console.log('Page title:', title);

    // Find the search box and enter text
    await page.locator('input[name="search"]').fill('Playwright');

    // Click the search button
    await page.locator('button[type="submit"]').click();

    // Wait for the search results page to load
    await page.waitForLoadState('domcontentloaded');

    console.log('Current URL:', page.url());

    // Take a screenshot
    await page.screenshot({
        path: 'safari-test.png'
    });

    console.log('Automation completed!');

    // Close browser
    await browser.close();
}

main().catch(console.error);

