import requests
from bs4 import BeautifulSoup
import config

print("config.proxy_host:", config.PROXY_HOST)
print("config.proxy_port:", config.PROXY_PORT)

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

url = "https://www.spitogatos.gr/search/results/residential/sale/r100/m2007m/propertyType_apartment/onlyImage"

response = requests.get(url, headers=headers, proxies=proxies)
print("response.status_code:", response.status_code)

soup = BeautifulSoup(response.content, "html.parser")

print("The End")
