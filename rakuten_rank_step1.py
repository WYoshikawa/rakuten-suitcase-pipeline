#!/usr/bin/env python3
"""
🦝 RASCAL 3.0対応 rakuten_rank_step1.py【画像URL取得版】
-----------------------------------
▸ 楽天 Item Ranking API (スーツケース: genreId=301577) から上位 1000 件取得
▸ itemPrice / reviewAverage / reviewCount / 画像URL を含む CSV を出力
▸ 商品名キーワードで詳細機能フラグ付与（15種類の機能検出）
▸ 🆕 画像URL取得機能追加（RASCAL 3.0 画像分析対応）

使い方:
    1. .env に APP_ID=your_application_id を設定
    2. pip install requests pandas tqdm python-dotenv
    3. python rakuten_rank_step1.py --pages 10 --with-images
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
HEADERS   = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

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
    """楽天ランキングAPI URL生成"""
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

def extract_image_url(item, image_size="medium"):
    """🎨 商品画像URL抽出（RASCAL 3.0対応）"""
    try:
        # 画像サイズ別URL取得
        if image_size == "medium" and "mediumImageUrls" in item:
            image_urls = item["mediumImageUrls"]
            if image_urls and len(image_urls) > 0:
                return image_urls[0]["imageUrl"]
        
        elif image_size == "small" and "smallImageUrls" in item:
            image_urls = item["smallImageUrls"]
            if image_urls and len(image_urls) > 0:
                return image_urls[0]["imageUrl"]
        
        # フォールバック: mediumImageUrl（単一）
        if "mediumImageUrl" in item and item["mediumImageUrl"]:
            return item["mediumImageUrl"]
        
        # フォールバック: smallImageUrl（単一）  
        if "smallImageUrl" in item and item["smallImageUrl"]:
            return item["smallImageUrl"]
        
        # 最終フォールバック: itemUrl（商品ページ）
        return item.get("itemUrl", "")
        
    except Exception as e:
        print(f"画像URL抽出エラー: {e}")
        return ""

def fetch(pages, with_images=False):
    """楽天ランキングデータ取得"""
    rows = []
    print(f"🚀 楽天スーツケースランキング取得開始 (上位{pages * 100}件)")
    if with_images:
        print("🎨 画像URL取得機能: 有効")
    
    for p in tqdm(range(1, pages+1), desc="📡 データ取得中"):
        try:
            response = requests.get(rank_url(p), headers=HEADERS, timeout=15)
            response.raise_for_status()
            js = response.json()
            
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
                    "itemUrl": item["itemUrl"],
                }
                
                # 🎨 画像URL追加（RASCAL 3.0対応）
                if with_images:
                    row_data["imageUrl"] = extract_image_url(item, "medium")
                    # 念のため小さいサイズも取得
                    row_data["smallImageUrl"] = extract_image_url(item, "small")
                
                # 機能フラグを追加
                row_data.update(analyze_features(name))
                rows.append(row_data)
                
        except requests.exceptions.RequestException as e:
            print(f"❌ API取得エラー (page {p}): {e}")
            continue
        except Exception as e:
            print(f"❌ データ処理エラー (page {p}): {e}")
            continue
            
        # API負荷軽減
        time.sleep(1)
    
    return pd.DataFrame(rows)

def display_statistics(df, with_images=False):
    """統計情報表示"""
    print(f"\n📊 機能別統計 (全{len(df)}件)")
    print("=" * 50)
    
    # 機能統計
    feature_cols = [col for col in df.columns if col.startswith(('has_', 'is_', 'for_', 'appeal_'))]
    for col in feature_cols:
        count = df[col].sum() if df[col].dtype == bool else (df[col] == True).sum()
        percentage = (count / len(df)) * 100
        feature_name = col.replace('has_', '').replace('is_', '').replace('for_', '').replace('appeal_', '')
        print(f"{feature_name:15}: {count:3d}件 ({percentage:5.1f}%)")
    
    # 🎨 画像URL統計（RASCAL 3.0対応）
    if with_images:
        print(f"\n🎨 画像URL取得統計")
        print("=" * 30)
        if 'imageUrl' in df.columns:
            valid_images = df['imageUrl'].notna().sum()
            valid_percentage = (valid_images / len(df)) * 100
            print(f"画像URL取得成功: {valid_images}件 ({valid_percentage:.1f}%)")
            
            # 画像URL例
            sample_images = df[df['imageUrl'].notna()]['imageUrl'].head(3)
            print(f"画像URL例:")
            for i, url in enumerate(sample_images, 1):
                print(f"  {i}. {url[:80]}...")
        else:
            print("画像URL取得: 無効")

def save_data(df, with_images=False):
    """データ保存"""
    # ファイル名生成
    base_name = f"rank_base_{date.today()}"
    if with_images:
        out = f"{base_name}_with_images.csv"
    else:
        out = f"{base_name}.csv"
    
    # CSV保存
    df.to_csv(out, index=False, encoding='utf-8')
    
    print(f"\n✅ 保存完了: {out}")
    print(f"📈 取得件数: {len(df)}件")
    
    # 列数表示
    feature_cols = [col for col in df.columns if col.startswith(('has_', 'is_', 'for_', 'appeal_'))]
    print(f"🏷️  機能フラグ: {len(feature_cols)}種類")
    
    if with_images and 'imageUrl' in df.columns:
        valid_images = df['imageUrl'].notna().sum()
        print(f"🎨 画像URL: {valid_images}件取得")
        
        # RASCAL 3.0 分析準備完了メッセージ
        if valid_images > 0:
            print(f"\n🦝 RASCAL 3.0 画像分析準備完了！")
            print(f"次のコマンドで画像分析を実行:")
            print(f"python rascal_3_0_image_analysis.py {out}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="🦝 RASCAL楽天ランキング取得システム")
    parser.add_argument("--pages", type=int, default=10, help="取得ページ数 (最大10)")
    parser.add_argument("--with-images", action="store_true", help="🎨 画像URL取得（RASCAL 3.0対応）")
    args = parser.parse_args()
    
    print("🦝" + "="*50)
    print("🦝 RASCAL楽天スーツケースランキング取得システム")
    if args.with_images:
        print("🦝 RASCAL 3.0 画像分析対応版")
    print("🦝" + "="*50)
    
    # データ取得
    df = fetch(args.pages, args.with_images)
    
    if len(df) == 0:
        print("❌ データ取得に失敗しました")
        exit(1)
    
    # 統計表示
    display_statistics(df, args.with_images)
    
    # データ保存
    save_data(df, args.with_images)
    
    # RASCAL 3.0 画像分析推奨
    if args.with_images and 'imageUrl' in df.columns and df['imageUrl'].notna().sum() > 0:
        print(f"\n🦝 RASCAL 3.0 画像分析機能が利用可能です！")
        print(f"🎨 色彩分析、デザイン分類、高級感評価、整合性チェック")
        print(f"💎 市場の真実を画像データで解明しましょう！")
    
    print(f"\n🦝 データ取得完了！RASCAL分析をお楽しみください！")
