#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""دریافت خودکار قیمت روز خودرو از چند سایت خبری و ساخت data/scraped.json (فقط کتابخانه‌های استاندارد پایتون)."""
import json, re, os, sys, datetime as dt, urllib.request, urllib.parse
from html.parser import HTMLParser
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime

OUT = 'data/scraped.json'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
      'Accept-Language': 'fa,en;q=0.8'}
QUERIES = ['قیمت خودرو امروز', 'قیمت خودروهای ایران خودرو امروز', 'قیمت خودروهای سایپا امروز', 'قیمت خودرو مونتاژی و وارداتی امروز']
MAX_PAGES, MAX_AGE_DAYS, MIN_ITEMS_PAGE, MIN_ITEMS_TOTAL = 18, 3, 5, 10
MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
CATS = [('وارداتی', r'تویوتا|هیوندای|کیا |بنز|بی‌ام‌و|BMW|لکسوس|اوشان|Oshan|نیسان|هوندا|مزدا|فولکس|فرانتلندر|کرولا'),
        ('کرمان موتور', r'جک|کی‌ام‌سی|KMC|بک '),
        ('ایران‌خودرو', r'پژو|دنا|سورن|رانا|تارا|آریسان|ری[ \u200c]?را|هایما|فوتون|سمند'),
        ('سایپا', r'سهند|ساینا|کوییک|اطلس|شاهین|سایپا|زامیاد|کارون|چانگان|سیتروئن|پراید|تیبا'),
        ('مدیران خودرو', r'X22|X33|X55|تیگو|آریزو|فونیکس'),
        ('بهمن موتور', r'فیدلیتی|دیگنیتی|رسپکت|کارا|کاپرا')]
STOP = {'و', 'با', 'ای', 'مدل', 'تیپ'}


def digits(s):
    s = str(s).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
    return s.replace('ي', 'ی').replace('ك', 'ک').replace('\xa0', ' ')


def cat(n):
    return next((c for c, rx in CATS if re.search(rx, n)), 'سایر')


def j2g(jy, jm, jd):  # تبدیل شمسی به میلادی
    jy += 1595
    days = -355668 + 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4 + jd + ((jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186)
    gy = 400 * (days // 146097); days %= 146097
    if days > 36524:
        days -= 1; gy += 100 * (days // 36524); days %= 36524
        if days >= 365: days += 1
    gy += 4 * (days // 1461); days %= 1461
    if days > 365: gy += (days - 1) // 365; days = (days - 1) % 365
    gd = days + 1
    ml = [0, 31, 29 if (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while gm < 13 and gd > ml[gm]:
        gd -= ml[gm]; gm += 1
    return dt.date(gy, gm, gd)


def find_date(text):
    m = re.search(r'(\d{1,2})\s*(%s)\s*(\d{4})' % '|'.join(MONTHS), digits(text))
    if not m: return None
    try: return j2g(int(m.group(3)), MONTHS.index(m.group(2)) + 1, int(m.group(1)))
    except Exception: return None


PR = re.compile(r'(\d+(?:\.\d+)?)\s*میلیارد(?:\s*و\s*(\d+(?:\.\d+)?)\s*میلیون)?|(\d+(?:\.\d+)?)\s*میلیون|(?<![\d.])(\d{9,11})(?![\d.])')


def price(cell):
    m = PR.search(re.sub(r'[,٬،]', '', digits(cell)))
    if not m: return None
    if m.group(1): v = float(m.group(1)) * 1e9 + float(m.group(2) or 0) * 1e6
    elif m.group(3): v = float(m.group(3)) * 1e6
    else: v = float(m.group(4))
    v = round(v)
    return v if 2e8 <= v <= 1e11 else None


class TP(HTMLParser):
    def __init__(s):
        super().__init__(); s.rows = []; s.row = None; s.cell = None
    def handle_starttag(s, t, a):
        if t == 'tr': s.row = []
        elif t in ('td', 'th') and s.row is not None: s.cell = []
        elif t == 'br' and s.cell is not None: s.cell.append(' ')
    def handle_endtag(s, t):
        if t in ('td', 'th') and s.cell is not None and s.row is not None:
            s.row.append(' '.join(''.join(s.cell).split())); s.cell = None
        elif t == 'tr' and s.row is not None:
            if s.row: s.rows.append(s.row)
            s.row = None
    def handle_data(s, d):
        if s.cell is not None: s.cell.append(d)


def clean_name(n):
    n = digits(n)
    n = re.sub(r'\s*[,،]?\s*\b(1[34]\d\d|20\d\d)\b\s*$', '', n.strip())
    return re.sub(r'\s+', ' ', n).strip(' -–:|')


def parse_rows(rows):
    out, mk, ag = [], None, None
    for r in rows:
        if not any(price(c) for c in r) and any(k in ' '.join(r) for k in ('بازار', 'کارخانه', 'نمایندگی', 'قیمت')):
            mk = ag = None
            for i, c in enumerate(r):
                if 'کارخانه' in c or 'نمایندگی' in c: ag = i
                elif any(k in c for k in ('بازار', 'قیمت', 'روز')) and mk is None: mk = i
            continue
        name, prices = None, []
        for i, c in enumerate(r):
            p = price(c)
            if p: prices.append((i, p))
            elif name is None and re.search(r'[آ-ی]|[A-Za-z]', c) and not re.search(r'تغییر|بازار|کارخانه|نمایندگی', c): name = c
        name = clean_name(name) if name else None
        if not name or len(name) < 3 or not prices: continue
        market, agency = None, 0
        if mk is not None:
            market = next((p for i, p in prices if i == mk), None)
            agency = next((p for i, p in prices if i == ag), 0) if ag is not None else 0
            if market is None: continue  # «ناموجود» یا بدون قیمت بازار
        else:
            market = prices[0][1]
            if len(prices) > 1 and 0.3 <= prices[1][1] / market <= 2: agency = prices[1][1]
        out.append({'name': name, 'price': market, 'agency': agency, 'cat': cat(name)})
    return out


def tokens(n):
    return {t for t in re.findall(r'[آ-یA-Za-z0-9]+', n.replace('\u200c', ' ').lower()) if t not in STOP}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode('utf-8', 'replace')


def candidates():
    seen, res = set(), []
    for q in QUERIES:
        try:
            xml = get('https://www.bing.com/news/search?q=%s&format=rss&setlang=fa&cc=IR' % urllib.parse.quote(q))
            for it in ET.fromstring(xml).iter('item'):
                title, link = it.findtext('title') or '', it.findtext('link') or ''
                url = urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get('url', [link])[0]
                d = find_date(title)
                if d is None and it.findtext('pubDate'):
                    try: d = parsedate_to_datetime(it.findtext('pubDate')).date()
                    except Exception: pass
                if url not in seen and 'خودرو' in title: seen.add(url); res.append((title, url, d))
        except Exception as e:
            print('خطا در جست‌وجوی خبر:', q, e, file=sys.stderr)
    return res


def collect(today):
    pages, log = [], []
    for title, url, d in candidates():
        if len(pages) + len(log) >= MAX_PAGES: break
        if d is None or not (today - dt.timedelta(days=MAX_AGE_DAYS) <= d <= today + dt.timedelta(days=1)): continue
        host = urllib.parse.urlparse(url).netloc.replace('www.', '')
        try:
            p = TP(); p.feed(get(url)); items = parse_rows(p.rows)
            ok = len(items) >= MIN_ITEMS_PAGE
            log.append({'source': host, 'url': url, 'status': 'ok' if ok else 'error', 'count': len(items), 'date': str(d), **({} if ok else {'error': 'جدول قیمت کافی پیدا نشد'})})
            if ok: pages.append({'host': host, 'url': url, 'date': d, 'items': items})
        except Exception as e:
            log.append({'source': host, 'url': url, 'status': 'error', 'count': 0, 'date': str(d), 'error': str(e)[:120]})
    return pages, log


def merge(pages):
    if not pages: return []
    newest = max(p['date'] for p in pages)
    use = [p for p in pages if p['date'] >= newest - dt.timedelta(days=1)]
    use.sort(key=lambda p: (p['date'] != newest, -sum(1 for i in p['items'] if i['agency']), -len(p['items'])))  # صفحه اصلی: تازه‌ترین و کامل‌ترین
    res, toks = [], []
    for k, p in enumerate(use):
        for i in p['items']:
            t = tokens(i['name'])
            if not t or any(len(t & o) / len(t | o) >= 0.85 for o in toks): continue
            # از صفحه‌های بعدی فقط برای گروه‌هایی که صفحه اصلی کم‌پوشش دارد (مثلاً وارداتی) خودرو اضافه می‌شود
            if k and sum(1 for x in res if x['cat'] == i['cat']) >= 3: continue
            toks.append(t)
            res.append({**i, 'source': p['host'], 'url': p['url'], 'reportDate': str(p['date']), 'kind': 'scraped'})
    return res


def main():
    today = dt.datetime.now(dt.timezone.utc).date()
    pages, log = collect(today)
    items = merge(pages)
    old = {}
    if os.path.exists(OUT):
        try: old = json.load(open(OUT, encoding='utf-8'))
        except Exception: pass
    if len(items) < MIN_ITEMS_TOTAL:
        print('قیمت کافی پیدا نشد؛ داده قبلی نگه داشته شد.', file=sys.stderr)
        items = old.get('items', [])
        updated = old.get('updated')
        log.append({'source': 'کل اجرا', 'status': 'error', 'count': 0, 'error': 'داده جدید کافی نبود، داده قبلی مانده است'})
    else:
        updated = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    os.makedirs('data', exist_ok=True)
    json.dump({'updated': updated, 'items': items, 'log': log}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('تعداد خودرو:', len(items), '| صفحه موفق:', len(pages), '| کل لاگ:', len(log))


if __name__ == '__main__':
    main()
