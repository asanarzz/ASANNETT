import requests
from bs4 import BeautifulSoup

def get_prices():
    # لینک یک سایت معتبر برای استخراج قیمت
    url = "https://www.tgju.org/" 
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # این بخش قیمت دلار و طلا را از سایت استخراج می‌کند
    dollar = soup.find("td", {"data-market-param": "price_dollar_rl"}).text
    gold = soup.find("td", {"data-market-param": "geram18"}).text
    
    with open("prices.txt", "w", encoding="utf-8") as f:
        f.write(f"قیمت دلار: {dollar}\nقیمت طلا ۱۸ عیار: {gold}")

if __name__ == "__main__":
    get_prices()
