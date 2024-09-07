import requests
from bs4 import BeautifulSoup
import config


headers = {
    "Host": "www.spitogatos.gr",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0",
    "Accept": "application/json; charset=utf-8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.spitogatos.gr/",
    "Content-Type": "text/plain; charset=utf-8",
    "Origin": "https://www.spitogatos.gr",
}

proxy = f"http://{config.PROXY_USER}:{config.PROXY_PASS}@{config.PROXY_HOST}:{config.PROXY_PORT}"

proxies = {"http": proxy, "https": proxy}

url = "https://www.spitogatos.gr/pwliseis-katoikies/marousi"

response = requests.get(url, headers=headers, proxies=proxies)
if response.status_code != 200:
    print("Failed to fetch the page. Status code:", response.status_code)
    exit(1)

soup = BeautifulSoup(response.content, "html.parser")

apartments = soup.find_all("article", class_="ordered-element")

for apt in apartments:
    price = (
        apt.find("div", class_="tile__price").text.strip()
        if apt.find("div", class_="tile__price")
        else "No price available"
    )
    print("price:", price)

print("The End")
