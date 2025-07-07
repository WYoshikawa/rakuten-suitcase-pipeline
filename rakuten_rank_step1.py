#!/usr/bin/env python3
"""
rakuten_rank_step1.py
-----------------------------------
▸ 楽天 Item Ranking API (スーツケース: genreId=301577) から上位 1000 件取得
▸ itemPrice / reviewAverage / reviewCount を含む CSV を出力
▸ 商品名キーワードで簡易機能フラグ (USB, 拡張, フロントオープン) 付与

使い方:
    1. .env に APP_ID=your_application_id を設定
    2. pip install requests pandas tqdm python-dotenv
    3. python rakuten_rank_step1.py --pages 10
"""

import os, time, argparse, re
from datetime import date
import requests, pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()
APP_ID = os.getenv("APP_ID", "").strip()
if not APP_ID:
    raise RuntimeError("APP_ID missing (.env or export APP_ID=xxxx)")

GENRE_ID  = 301577
HEADERS   = {"User-Agent": "Mozilla/5.0"}
USB_RE    = re.compile(r"USB|ポート", re.I)
EXPAND_RE = re.compile(r"拡張|エキスパンド", re.I)
FRONT_RE  = re.compile(r"フロント|前開き", re.I)

def rank_url(page):
    return (f"https://app.rakuten.co.jp/services/api/IchibaItem/Ranking/20220601"
            f"?applicationId={APP_ID}&format=json&genreId={GENRE_ID}&page={page}")

def fetch(pages):
    rows=[]
    for p in tqdm(range(1, pages+1), desc="fetch pages"):
        js=requests.get(rank_url(p), headers=HEADERS, timeout=15).json()
        for it in js.get("Items", []):
            item=it["Item"]
            name=item["itemName"]
            rows.append({
                "rank": item["rank"],
                "itemCode": item["itemCode"],
                "itemName": name,
                "itemPrice": item["itemPrice"],
                "reviewAverage": item["reviewAverage"],
                "reviewCount": item["reviewCount"],
                "has_USB": bool(USB_RE.search(name)),
                "has_expand": bool(EXPAND_RE.search(name)),
                "has_frontOP": bool(FRONT_RE.search(name)),
            })
        time.sleep(1)
    return pd.DataFrame(rows)

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=10, help="Ranking pages (max 10)")
    args=parser.parse_args()
    df=fetch(args.pages)
    out=f"rank_base_{date.today()}.csv"
    df.to_csv(out, index=False)
    print("Saved", out)
