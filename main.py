import requests
from PIL import Image, ImageDraw, ImageFont
import jdatetime
from config import BOT_TOKEN, CHAT_ID

def get_prices():


    return {
        "bitcoin": bitcoin,
        "gold18": "نامشخص",
        "usd": "نامشخص",
        "tether": "1$"
    }

def make_image(data):
    img = Image.new("RGB", (1080, 1080), (15, 20, 40))
    draw = ImageDraw.Draw(img)

    date = jdatetime.date.today().strftime("%Y/%m/%d")

    draw.text((50, 50), "کافی نت آسان نت @ASANNETT", fill="white")
    draw.text((50, 120), f"تاریخ: {date}", fill="white")

    draw.text((50, 250), f"بیت کوین: {data['bitcoin']}", fill="white")
    draw.text((50, 320), f"تتر: {data['tether']}", fill="white")

    path = "/tmp/output.png"
    img.save(path)
    return path

def send_to_telegram(image_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": open(image_path, "rb")}
    data = {"chat_id": CHAT_ID}
    requests.post(url, files=files, data=data)

if __name__ == "__main__":
    data = get_prices()
    img = make_image(data)
    send_to_telegram(img)
