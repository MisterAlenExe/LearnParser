import asyncio
import os
import dotenv
import pickle
import aiohttp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup


async def auth_microsoft(website, barcode, password):
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/107.0.0.0 Safari/537.36")
    options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument('log-level=3')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    browser = webdriver.Chrome(options=options)

    email_field = (By.ID, "i0116")
    password_field = (By.ID, "i0118")
    next_button = (By.ID, "idSIButton9")
    browser.get(website)
    wait = WebDriverWait(browser, 10)
    try:
        wait.until(ec.element_to_be_clickable(email_field)).send_keys(f"{barcode}@astanait.edu.kz")
        wait.until(ec.element_to_be_clickable(next_button)).click()
        wait.until(ec.element_to_be_clickable(password_field)).send_keys(password)
        wait.until(ec.element_to_be_clickable(next_button)).click()
        wait.until(ec.element_to_be_clickable(next_button)).click()
    except:
        pass

    browser_cookies = browser.get_cookies()
    browser.close()
    browser.quit()

    cookies = {}
    for cookie in browser_cookies:
        cookies[cookie['name']] = cookie['value']

    pickle.dump(cookies, open(f"{barcode}_cookies", "wb"))
    return cookies


async def is_cookies_valid(cookies):
    async with aiohttp.ClientSession(cookies=cookies) as session:
        async with session.get('https://learn.astanait.edu.kz/login?next=%2F') as response:
            # print(await response.text())
            if 'Войти' not in await response.text():
                await session.close()
                return True
            else:
                await session.close()
                return False


async def find_courses(cookies):
    async with aiohttp.ClientSession(cookies=cookies) as session:
        async with session.get('https://learn.astanait.edu.kz/dashboard') as response:
            main_url = 'https://learn.astanait.edu.kz'
            soup = BeautifulSoup(await response.text(), 'lxml')
            links = soup.find_all('a', {'class': 'course-target-link'})
            courses = set()
            for course in links:
                courses.add(main_url + course.get('href'))
            await session.close()
            return courses


async def find_all_quizes(courses, cookies):
    for course in courses:
        async with aiohttp.ClientSession(cookies=cookies) as session:
            async with session.get(course) as response:
                soup = BeautifulSoup(await response.text(), 'lxml')
                lists = soup.find_all('li', {'class': 'outline-item section scored'})
                print(course)
                for section in lists:
                    for link in section.find_all('a', {'class': 'subsection-text outline-button'}):
                        if 'Quiz' in link.text and link.find('span', {'class': 'subtitle'}):
                            print(link.find('div').find('span', {'class': 'localized-datetime subtitle-name'}).get(
                                'data-datetime'))
                await session.close()


async def main():
    dotenv.load_dotenv()
    login_url = 'https://learn.astanait.edu.kz/auth/login/azuread-oauth2/?auth_entry=login&next=%2F'
    barcode = os.getenv('BARCODE')
    passwd = os.getenv('PASSWORD')

    cookies = pickle.load(open(f"{barcode}_cookies", "rb"))

    if not await is_cookies_valid(cookies):
        cookies = await auth_microsoft(login_url, barcode, passwd)

    await find_all_quizes(list(await find_courses(cookies)), cookies)


if __name__ == '__main__':
    asyncio.run(main())
