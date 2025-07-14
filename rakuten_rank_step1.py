#!/usr/bin/env python3
"""
rakuten_rank_step1.py (Enhanced Version)
-----------------------------------
▸ 楽天 Item Ranking API (スーツケース: genreId=301577) から上位 1000 件取得
▸ itemPrice / reviewAverage / reviewCount を含む CSV を出力
▸ 商品名キーワードで詳細機能フラグ付与（15種類の機能検出）
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

# ========== 機能検出用正規表現パターン ==========

# 既存機能
USB_RE    = re.compile(r"USB|ポート", re.I)
EXPAND_RE = re.compile(r"拡張|エキスパンド", re.I)
FRONT_RE  = re.compile(r"フロント|前開き", re.I)

# 🔒 セキュリティ系
TSA_RE = re.compile(r"TSA|TSAロック", re.I)
LOCK_RE = re.compile(r"ロック(?!TSA)|鍵", re.I)  # TSAロック以外のロック

# ⚖️ 重量・素材系
LIGHTWEIGHT_RE = re.compile(r"軽量|超軽|軽い", re.I)
HARDCASE_RE = re.compile(r"ハード|ハードケース", re.I)
SOFTCASE_RE = re.compile(r"ソフト|ソフトケース", re.I)

# 🛞 キャスター・移動系
SILENT_RE = re.compile(r"静音|サイレント", re.I)
WHEEL360_RE = re.compile(r"360度|360°", re.I)
FOUR_WHEEL_RE = re.compile(r"4輪|四輪", re.I)
STOPPER_RE = re.compile(r"ストッパー", re.I)

# 📏 サイズ・容量系
CARRY_ON_RE = re.compile(r"機内持ち込み|機内持込", re.I)
LARGE_CAPACITY_RE = re.compile(r"大容量", re.I)

# 🔧 その他機能
SHOCK_RESISTANT_RE = re.compile(r"耐衝撃|衝撃に強い", re.I)
CUP_HOLDER_RE = re.compile(r"カップホルダー|ドリンクホルダー", re.I)

# 🏷️ ブランド系
SAMSONITE_RE = re.compile(r"サムソナイト|SAMSONITE", re.I)
INNOVATOR_RE = re.compile(r"イノベーター|innovator", re.I)

# 🛡️ 補償・保証系
WARRANTY_RE = re.compile(r"保証|補償|warranty|guarantee", re.I)
WARRANTY_1YEAR_RE = re.compile(r"1年保証", re.I)
WARRANTY_2YEAR_RE = re.compile(r"2年保証", re.I)
WARRANTY_3YEAR_RE = re.compile(r"3年保証|品質保証獲得", re.I)

# 🏨 宿泊日数系
STAY_1NIGHT_RE = re.compile(r"1泊", re.I)
STAY_2NIGHT_RE = re.compile(r"2泊", re.I)
STAY_3NIGHT_RE = re.compile(r"3泊", re.I)
STAY_4NIGHT_RE = re.compile(r"4泊", re.I)
STAY_5NIGHT_RE = re.compile(r"5泊", re.I)
STAY_SHORT_RE = re.compile(r"1泊2日|2泊3日|短期", re.I)
STAY_LONG_RE = re.compile(r"4泊5日|5泊|長期", re.I)

# 📢 マーケティング訴求パターン
# 💰 価格訴求
PRICE_APPEAL_RE = re.compile(r"OFF|クーポン|割|最安|激安|格安|衝撃価格|セール", re.I)
# 📺 権威・メディア訴求
AUTHORITY_APPEAL_RE = re.compile(r"TV|テレビ|メディア|紹介|正規品|ランキング|1位|受賞|CA監修|楽天1位", re.I)
# ⚡ 機能・性能訴求
FUNCTION_APPEAL_RE = re.compile(r"超軽量|多機能|高機能|最新|特許|独自|革新|進化", re.I)
# 🏃 緊急・限定訴求
URGENCY_APPEAL_RE = re.compile(r"限定|先着|24H限定|今だけ|再入荷|在庫限り|期間限定", re.I)

def rank_url(page):
    return (f"https://app.rakuten.co.jp/services/api/IchibaItem/Ranking/20220601"
            f"?applicationId={APP_ID}&format=json&genreId={GENRE_ID}&page={page}")

def analyze_features(name):
    """商品名から各種機能フラグを検出"""
    return {
        # 既存機能
        "has_USB": bool(USB_RE.search(name)),
        "has_expand": bool(EXPAND_RE.search(name)),
        "has_frontOP": bool(FRONT_RE.search(name)),
        
        # セキュリティ
        "has_TSA": bool(TSA_RE.search(name)),
        "has_lock": bool(LOCK_RE.search(name)),
        
        # 重量・素材
        "has_lightweight": bool(LIGHTWEIGHT_RE.search(name)),
        "has_hardcase": bool(HARDCASE_RE.search(name)),
        "has_softcase": bool(SOFTCASE_RE.search(name)),
        
        # キャスター・移動
        "has_silent": bool(SILENT_RE.search(name)),
        "has_360wheel": bool(WHEEL360_RE.search(name)),
        "has_4wheel": bool(FOUR_WHEEL_RE.search(name)),
        "has_stopper": bool(STOPPER_RE.search(name)),
        
        # サイズ・容量
        "has_carry_on": bool(CARRY_ON_RE.search(name)),
        "has_large_capacity": bool(LARGE_CAPACITY_RE.search(name)),
        
        # その他機能
        "has_shock_resistant": bool(SHOCK_RESISTANT_RE.search(name)),
        "has_cup_holder": bool(CUP_HOLDER_RE.search(name)),
        
        # ブランド
        "is_samsonite": bool(SAMSONITE_RE.search(name)),
        "is_innovator": bool(INNOVATOR_RE.search(name)),
        
        # 補償・保証
        "has_warranty": bool(WARRANTY_RE.search(name)),
        "has_1year_warranty": bool(WARRANTY_1YEAR_RE.search(name)),
        "has_2year_warranty": bool(WARRANTY_2YEAR_RE.search(name)),
        "has_3year_warranty": bool(WARRANTY_3YEAR_RE.search(name)),
        
        # 宿泊日数
        "for_1night": bool(STAY_1NIGHT_RE.search(name)),
        "for_2night": bool(STAY_2NIGHT_RE.search(name)),
        "for_3night": bool(STAY_3NIGHT_RE.search(name)),
        "for_4night": bool(STAY_4NIGHT_RE.search(name)),
        "for_5night": bool(STAY_5NIGHT_RE.search(name)),
        "for_short_stay": bool(STAY_SHORT_RE.search(name)),
        "for_long_stay": bool(STAY_LONG_RE.search(name)),
        
        # マーケティング訴求パターン
        "appeal_price": bool(PRICE_APPEAL_RE.search(name)),
        "appeal_authority": bool(AUTHORITY_APPEAL_RE.search(name)),
        "appeal_function": bool(FUNCTION_APPEAL_RE.search(name)),
        "appeal_urgency": bool(URGENCY_APPEAL_RE.search(name)),
    }

def fetch(pages):
    rows = []
    for p in tqdm(range(1, pages+1), desc="fetch pages"):
        js = requests.get(rank_url(p), headers=HEADERS, timeout=15).json()
        for it in js.get("Items", []):
            item = it["Item"]
            name = item["itemName"]
            
            # 基本データ
            row_data = {
                "rank": item["rank"],
                "itemCode": item["itemCode"],
                "itemName": name,
                "itemPrice": item["itemPrice"],
                "reviewAverage": item["reviewAverage"],
                "reviewCount": item["reviewCount"],
                "itemUrl": item["itemUrl"],  # URL も追加
            }
            
            # 機能フラグを追加
            row_data.update(analyze_features(name))
            rows.append(row_data)
            
        time.sleep(1)
    return pd.DataFrame(rows)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=10, help="Ranking pages (max 10)")
    args = parser.parse_args()
    
    print(f"🚀 楽天スーツケースランキング取得開始 (上位{args.pages * 100}件)")
    df = fetch(args.pages)
    
    # 機能統計を表示
    print(f"\n📊 機能別統計 (全{len(df)}件)")
    print("=" * 50)
    
    feature_cols = [col for col in df.columns if col.startswith(('has_', 'is_'))]
    for col in feature_cols:
        count = df[col].sum()
        percentage = (count / len(df)) * 100
        feature_name = col.replace('has_', '').replace('is_', '')
        print(f"{feature_name:15}: {count:3d}件 ({percentage:5.1f}%)")
    
    # CSV保存
    out = f"rank_base_{date.today()}.csv"
    df.to_csv(out, index=False)
    print(f"\n✅ 保存完了: {out}")
    print(f"📈 取得件数: {len(df)}件")
    print(f"🏷️  機能フラグ: {len(feature_cols)}種類")
