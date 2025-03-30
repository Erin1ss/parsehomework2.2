import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import os
import re
import datetime
import pytz

COOKIES_FILE = "/root/parsehomework2.0/cookies.json"
OUTPUT_DIR = "/root/parsehomework2.0/"  # Path for saving .txt files
FAKE_FILE = "/root/parsehomework2.0/cookies_status.txt"  # File to store cookie status

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def update_cookie_status(status):
    """Update the cookie status in the fake file."""
    with open(FAKE_FILE, "w", encoding="utf-8") as file:
        file.write(str(status))

async def save_cookies_to_file(cookies, filename):
    """Save cookies to a JSON file."""
    with open(filename, "w") as file:
        json.dump(cookies, file)
    print(f"Cookies saved to {filename}.")

async def load_cookies_from_file(context, filename):
    """Load cookies into a Playwright browser context."""
    if os.path.exists(filename):
        with open(filename, "r") as file:
            cookies = json.load(file)
            await context.add_cookies(cookies)
    else:
        print("No cookies file found.")

async def login_via_browser(playwright, url, cookies_file):
    """Open a browser for manual login and save cookies."""
    update_cookie_status(False)  # Assume failure until success
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(url)

    print("Please log in manually. The browser will close automatically after login.")
    input("Press Enter after logging in to save cookies...")

    cookies = await context.cookies()
    await save_cookies_to_file(cookies, cookies_file)

    update_cookie_status(True)  # Mark success
    await browser.close()


async def fetch_homework_section(playwright, url, cookies_file):
    """Fetch the specific section of the homework page using Playwright."""
    browser = await playwright.chromium.launch()
    context = await browser.new_context()

    # Load cookies and navigate to the page
    await load_cookies_from_file(context, cookies_file)
    page = await context.new_page()
    await page.goto(url)
    await asyncio.sleep(20)

    if "login" in page.url:  # If redirected to login, cookies are invalid
        update_cookie_status(False)
        await browser.close()
        return None

    update_cookie_status(True)
    html_content = await page.content()
    await browser.close()
    return html_content


async def save_homeworks_by_day(html_content):
    """Identify the day in Russian and save corresponding homework into .txt files."""
    if html_content is None:
        return

    soup = BeautifulSoup(html_content, "html.parser")
    day_mapping = {
        "Понедельник": "Понедельник.txt",
        "Вторник": "Вторник.txt",
        "Среда": "Среда.txt",
        "Четверг": "Четверг.txt",
        "Пятница": "Пятница.txt",
        "Суббота": "Суббота.txt",
        "Воскресенье": "Воскресенье.txt",
    }

    moscow_tz = pytz.timezone("Europe/Moscow")
    now = datetime.datetime.now(moscow_tz)
    update_time = f"\nОбновлено: {now.strftime('%H:%M %d.%m.%Y')}\n"

    for file_name in day_mapping.values():
        with open(os.path.join(OUTPUT_DIR, file_name), "w", encoding="utf-8") as file:
            file.write("В эл. дневнике пока что ничего нет\n")
            file.write(update_time)

    day_wrappers = soup.find_all("div", class_="diary-emotion-cache-mqvnnf-homeworksForDayWrapper")
    if not day_wrappers:
        print("No homework sections found.")
        return

    for day_wrapper in day_wrappers:
        day_text = day_wrapper.get_text(separator="\n", strip=True)
        for russian_day, file_name in day_mapping.items():
            if russian_day in day_text:
                homework_cards = day_wrapper.find_all("div", class_="diary-emotion-cache-nl8na2-homeworkCard")
                homework_items = []
                for card in homework_cards:
                    card_text = card.get_text(separator=":\n", strip=True)
                    filtered_items = [
                        item.strip()
                        for item in card_text.split("\n")
                        if item.strip() and not re.search(r'\d{1,2}:\d{2}', item)
                    ]
                    homework_items.extend(filtered_items)
                    homework_items.append("-" * 30)

                output_path = os.path.join(OUTPUT_DIR, file_name)
                with open(output_path, "w", encoding="utf-8") as file:
                    if homework_items:
                        file.write(f"{russian_day}: \n\n")
                        file.writelines(f"{item}\n" for item in homework_items)
                    file.write(update_time)

                print(f"Saved homework for {russian_day} to {output_path}.")
                break

async def debug_html(html_content):
    """Save the HTML content for debugging."""
    if html_content is None:
        return
    debug_path = os.path.join(OUTPUT_DIR, "debug.html")
    with open(debug_path, "w", encoding="utf-8") as file:
        file.write(html_content)
    print(f"HTML content saved to {debug_path}.")

async def main():
    login_url = "https://ms-edu.tatar.ru/16/"
    homework_url = "https://ms-edu.tatar.ru/diary/homeworks/homeworks/"

    async with async_playwright() as playwright:
        if not os.path.exists(COOKIES_FILE):
            print("No saved cookies found. Opening browser for manual login.")
            update_cookie_status(False)  # Mark cookies as missing
            await login_via_browser(playwright, login_url, COOKIES_FILE)

        while True:
            html_content = await fetch_homework_section(playwright, homework_url, COOKIES_FILE)
            await debug_html(html_content)
            await save_homeworks_by_day(html_content)
            print("Data parsed and saved. Waiting 30 minutes for the next fetch...")
            await asyncio.sleep(1800)


if __name__ == "__main__":
    asyncio.run(main())