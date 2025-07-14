import pandas as pd
import json
from datetime import datetime
import glob
import os

def analyze_ranking_changes():
    """前回との変化を分析"""
    
    # 最新の2つのCSVファイルを取得
    csv_files = sorted(glob.glob('data/rank_base_*.csv'))
    if len(csv_files) < 2:
        print("比較するデータが不足しています")
        return
    
    # 前回と今回のデータを読み込み
    previous_file = csv_files[-2]  # 前回
    current_file = csv_files[-1]   # 今回
    
    print(f"比較: {previous_file} → {current_file}")
    
    try:
        df_prev = pd.read_csv(previous_file)
        df_curr = pd.read_csv(current_file)
    except Exception as e:
        print(f"CSVファイル読み込みエラー: {e}")
        return
    
    # 商品IDで結合して変化を分析
    comparison = df_curr.merge(df_prev, on='itemCode', how='outer', suffixes=('_now', '_prev'))
    
    changes = {
        'timestamp': datetime.now().isoformat(),
        'previous_file': os.path.basename(previous_file),
        'current_file': os.path.basename(current_file),
        'changes': []
    }
    
    # 新規ランクイン
    new_items = comparison[comparison['rank_prev'].isna()]
    for _, item in new_items.iterrows():
        if pd.notna(item['rank_now']):
            changes['changes'].append({
                'type': '🆕 新規ランクイン',
                'rank': int(item['rank_now']),
                'title': item['itemName_now'],
                'price': item['itemPrice_now'],
                'url': item['itemUrl_now']
            })
    
    # ランキングアウト
    dropped_items = comparison[comparison['rank_now'].isna()]
    for _, item in dropped_items.iterrows():
        if pd.notna(item['rank_prev']):
            changes['changes'].append({
                'type': '📉 ランキングアウト',
                'previous_rank': int(item['rank_prev']),
                'title': item['itemName_prev'],
                'price': item['itemPrice_prev']
            })
    
    # 順位変動
    stable_items = comparison.dropna(subset=['rank_now', 'rank_prev'])
    for _, item in stable_items.iterrows():
        rank_change = int(item['rank_prev']) - int(item['rank_now'])  # 正数=上昇
        if abs(rank_change) >= 5:  # 5位以上の変動のみ
            change_type = "📈 急上昇" if rank_change > 0 else "📉 急下降"
            changes['changes'].append({
                'type': change_type,
                'rank_change': rank_change,
                'rank_now': int(item['rank_now']),
                'rank_prev': int(item['rank_prev']),
                'title': item['itemName_now'],
                'price': item['itemPrice_now'],
                'url': item['itemUrl_now']
            })
    
    # 価格変動（10%以上）
    for _, item in stable_items.iterrows():
        if pd.notna(item['itemPrice_now']) and pd.notna(item['itemPrice_prev']):
            price_change = (item['itemPrice_now'] - item['itemPrice_prev']) / item['itemPrice_prev'] * 100
            if abs(price_change) >= 10:
                change_type = "💰 値上がり" if price_change > 0 else "💸 値下がり"
                changes['changes'].append({
                    'type': change_type,
                    'price_change_percent': round(price_change, 1),
                    'price_now': item['itemPrice_now'],
                    'price_prev': item['itemPrice_prev'],
                    'rank': int(item['rank_now']),
                    'title': item['itemName_now'],
                    'url': item['itemUrl_now']
                })
    
    # 結果を保存
    os.makedirs('data/changes', exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    change_file = f'data/changes/changes_{timestamp}.json'
    
    with open(change_file, 'w', encoding='utf-8') as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)
    
    # 最新の変化も保存
    with open('data/changes/latest_changes.json', 'w', encoding='utf-8') as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)
    
    # コンソール出力
    print(f"\n🔄 ランキング変化レポート ({len(changes['changes'])}件)")
    print("=" * 50)
    
    for change in sorted(changes['changes'], key=lambda x: x.get('rank_now', x.get('rank', 999))):
        if change['type'] == '🆕 新規ランクイン':
            print(f"{change['type']} #{change['rank']} {change['title'][:50]}...")
        elif change['type'] == '📉 ランキングアウト':
            print(f"{change['type']} (#{change['previous_rank']}→圏外) {change['title'][:50]}...")
        elif '急' in change['type']:
            print(f"{change['type']} #{change['rank_prev']}→#{change['rank_now']} ({change['rank_change']:+d}) {change['title'][:50]}...")
        elif '値' in change['type']:
            print(f"{change['type']} ¥{change['price_prev']}→¥{change['price_now']} ({change['price_change_percent']:+.1f}%) {change['title'][:50]}...")
    
    print(f"\n📝 詳細は {change_file} に保存しました")

if __name__ == "__main__":
    analyze_ranking_changes()
