import asyncio
from playwright.async_api import async_playwright

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})
        
        # Take screenshot of the Chat page
        print("Navigating to Chat page...")
        await page.goto("http://localhost:8501/")
        # Wait for streamlit app to load (wait for the main container)
        await page.wait_for_selector(".stApp")
        await page.wait_for_timeout(3000)  # Extra wait for React to settle
        await page.screenshot(path="assets/chat.png")
        print("Saved assets/chat.png")
        
        # Navigate to the Analytics page (Streamlit uses multi-page links)
        print("Navigating to Analytics page...")
        # The link text in the sidebar might be "3 📊 Analytics" or similar, we'll navigate via URL if possible, or click.
        # Since streamlit pages have a specific URL structure, we can just click the link.
        await page.click("text=Analytics")
        await page.wait_for_timeout(3000)
        await page.screenshot(path="assets/dashboard.png")
        print("Saved assets/dashboard.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())
