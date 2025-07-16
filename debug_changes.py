import pandas as pd
import json
from datetime import datetime
import glob
import os

def debug_ranking_changes():
    """変化検出のデバッグ"""
    
    # 最新の2つのCSVファイルを取得
    csv_files = sorted(glob.glob('data/rank_base_*.csv'))
    print(f"発見されたCSVファイル: {csv_files}")
    
    if len(csv_files) < 2:
        print("⚠️ 比較するデータが不足しています")
        return
    
    # 前回と今回のデータを読み込み
    previous_file = csv_files[-2]  # 前回
    current_file = csv_files[-1]   # 今回
    
    print(f"比較対象: {previous_file} → {current_file}")
    
    try:
        df_prev = pd.read_csv(previous_file)
        df_curr = pd.read_csv(current_file)
        
        print(f"前回データ: {len(df_prev)}件")
        print(f"今回データ: {len(df_curr)}件")
        
        # データの中身をチェック
        print(f"前回の列: {list(df_prev.columns)}")
        print(f"今回の列: {list(df_curr.columns)}")
        
        # itemCodeの存在確認
        if 'itemCode' not in df_prev.columns or 'itemCode' not in df_curr.columns:
            print("❌ itemCode列が見つかりません")
            return
            
        print(f"前回のitemCode例: {df_prev['itemCode'].head().tolist()}")
        print(f"今回のitemCode例: {df_curr['itemCode'].head().tolist()}")
        
        # 重複確認
        prev_codes = set(df_prev['itemCode'])
        curr_codes = set(df_curr['itemCode'])
        
        common_codes = prev_codes & curr_codes
        new_codes = curr_codes - prev_codes
        dropped_codes = prev_codes - curr_codes
        
        print(f"\n📊 変化の概要:")
        print(f"共通商品: {len(common_codes)}件")
        print(f"新規商品: {len(new_codes)}件")
        print(f"削除商品: {len(dropped_codes)}件")
        
        if len(new_codes) > 0:
            print(f"\n🆕 新規商品の例:")
            new_items = df_curr[df_curr['itemCode'].isin(list(new_codes))].head(3)
            for _, item in new_items.iterrows():
                print(f"  {item['rank']}位: {item['itemName'][:60]}...")
        
        if len(dropped_codes) > 0:
            print(f"\n📉 削除商品の例:")
            dropped_items = df_prev[df_prev['itemCode'].isin(list(dropped_codes))].head(3)
            for _, item in dropped_items.iterrows():
                print(f"  元{item['rank']}位: {item['itemName'][:60]}...")
        
        # 共通商品の順位変動チェック
        if len(common_codes) > 0:
            print(f"\n📈 順位変動チェック (しきい値: 5位)")
            
            for code in list(common_codes)[:10]:  # 最初の10件だけチェック
                prev_item = df_prev[df_prev['itemCode'] == code].iloc[0]
                curr_item = df_curr[df_curr['itemCode'] == code].iloc[0]
                
                rank_change = prev_item['rank'] - curr_item['rank']  # 正数=上昇
                
                if abs(rank_change) >= 5:
                    change_type = "📈 急上昇" if rank_change > 0 else "📉 急下降"
                    print(f"  {change_type}: {prev_item['rank']}位→{curr_item['rank']}位 ({rank_change:+d})")
                    print(f"    {curr_item['itemName'][:50]}...")
                    
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ranking_changes()
