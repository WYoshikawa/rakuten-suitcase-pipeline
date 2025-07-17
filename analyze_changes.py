#!/usr/bin/env python3
"""
🦝 RASCAL Optimized Changes Analyzer
楽天スーツケースランキング変化分析（軽量化版）

重要度スコアリングによる効率的な変化検出システム
- ファイルサイズ制限対応
- 品質を保持した情報圧縮
- 階層化された重要度分類
"""

import pandas as pd
import json
import glob
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class RASCALChangesAnalyzer:
    """RASCAL推奨の重要度ベース変化分析器"""
    
    def __init__(self):
        self.data_dir = "data"
        self.changes_dir = os.path.join(self.data_dir, "changes")
        
        # 重要度判定のキーワード
        self.special_keywords = [
            'TV', 'ZIP', 'テレビ', 'ヒルナンデス', 'サタプラ',
            '楽天1位', 'ランキング1位', '1位獲得',
            'RIMOWA', 'サムソナイト', 'プロテカ'
        ]
        
        # ディレクトリ作成
        os.makedirs(self.changes_dir, exist_ok=True)
    
    def find_latest_files(self) -> tuple[str, str]:
        """最新と前日のCSVファイルを取得"""
        csv_files = glob.glob(os.path.join(self.data_dir, "rank_base_*.csv"))
        
        if len(csv_files) < 2:
            raise FileNotFoundError("比較に必要な2つのCSVファイルが見つかりません")
        
        # ファイル名でソート（日付順）
        csv_files.sort()
        
        return csv_files[-1], csv_files[-2]  # 最新, 前日
    
    def load_data(self, filepath: str) -> pd.DataFrame:
        """CSVデータを読み込み"""
        df = pd.read_csv(filepath)
        
        # データ型変換
        df['rank'] = df['rank'].astype(int)
        df['itemPrice'] = df['itemPrice'].astype(int)
        df['reviewAverage'] = pd.to_numeric(df['reviewAverage'], errors='coerce').fillna(0)
        df['reviewCount'] = df['reviewCount'].astype(int)
        
        return df
    
    def calculate_importance_score(self, item: Dict[str, Any]) -> int:
        """🎯 RASCAL重要度スコアリング"""
        score = 0
        
        # 順位による重要度
        rank = item.get('rank', 999)
        if rank <= 30:
            score += 3
        elif rank <= 100:
            score += 2
        elif rank <= 200:
            score += 1
        
        # 変動幅による重要度
        rank_change = abs(item.get('rank_change', 0))
        if rank_change >= 50:
            score += 3
        elif rank_change >= 20:
            score += 2
        elif rank_change >= 10:
            score += 1
        
        # 価格による重要度
        price = item.get('price', 0)
        if price >= 50000:
            score += 3
        elif price >= 30000:
            score += 2
        elif price >= 15000:
            score += 1
        
        # 価格変動による重要度
        price_change = abs(item.get('price_change_percent', 0))
        if price_change >= 20:
            score += 3
        elif price_change >= 10:
            score += 2
        elif price_change >= 5:
            score += 1
        
        # 特別要因（メディア、ブランド）
        title = item.get('title', '')
        if any(keyword in title for keyword in self.special_keywords):
            score += 2
        
        return score
    
    def filter_important_changes(self, changes: List[Dict]) -> Dict[str, List]:
        """重要度に基づく変化フィルタリング"""
        critical = []    # スコア5以上
        important = []   # スコア3-4
        notable = []     # スコア2
        
        for change in changes:
            score = self.calculate_importance_score(change)
            change['importance_score'] = score
            
            if score >= 5:
                critical.append(change)
            elif score >= 3:
                important.append(change)
            elif score >= 2:
                notable.append(change)
        
        # 各カテゴリで件数制限
        return {
            'critical': critical[:20],      # 最重要20件
            'important': important[:30],    # 重要30件
            'notable': notable[:20]         # 注目20件
        }
    
    def analyze_new_entries(self, today_df: pd.DataFrame, yesterday_df: pd.DataFrame) -> List[Dict]:
        """新規ランクイン商品の分析"""
        yesterday_codes = set(yesterday_df['itemCode'])
        new_items = today_df[~today_df['itemCode'].isin(yesterday_codes)]
        
        new_entries = []
        for _, item in new_items.iterrows():
            entry = {
                'type': '🆕 新規ランクイン',
                'rank': int(item['rank']),
                'title': str(item['itemName']),
                'price': int(item['itemPrice']),
                'url': str(item['itemUrl'])
            }
            new_entries.append(entry)
        
        return new_entries
    
    def analyze_dropped_entries(self, today_df: pd.DataFrame, yesterday_df: pd.DataFrame) -> List[Dict]:
        """ランキングアウト商品の分析"""
        today_codes = set(today_df['itemCode'])
        dropped_items = yesterday_df[~yesterday_df['itemCode'].isin(today_codes)]
        
        dropped_entries = []
        for _, item in dropped_items.iterrows():
            entry = {
                'type': '📉 ランキングアウト',
                'previous_rank': int(item['rank']),
                'title': str(item['itemName']),
                'price': int(item['itemPrice'])
            }
            dropped_entries.append(entry)
        
        return dropped_entries
    
    def analyze_rank_movements(self, today_df: pd.DataFrame, yesterday_df: pd.DataFrame) -> List[Dict]:
        """順位変動の分析"""
        # 共通商品の特定
        common_items = pd.merge(
            today_df, yesterday_df, 
            on='itemCode', 
            suffixes=('_today', '_yesterday')
        )
        
        movements = []
        for _, item in common_items.iterrows():
            rank_change = item['rank_yesterday'] - item['rank_today']  # 正数=上昇
            
            if abs(rank_change) >= 3:  # 3位以上の変動のみ
                movement = {
                    'type': '📈 急上昇' if rank_change > 0 else '📉 急下降',
                    'rank_change': int(rank_change),
                    'rank_now': int(item['rank_today']),
                    'rank_prev': int(item['rank_yesterday']),
                    'title': str(item['itemName_today']),
                    'price': int(item['itemPrice_today']),
                    'url': str(item['itemUrl_today'])
                }
                movements.append(movement)
        
        return movements
    
    def analyze_price_changes(self, today_df: pd.DataFrame, yesterday_df: pd.DataFrame) -> List[Dict]:
        """価格変動の分析"""
        common_items = pd.merge(
            today_df, yesterday_df, 
            on='itemCode', 
            suffixes=('_today', '_yesterday')
        )
        
        price_changes = []
        for _, item in common_items.iterrows():
            old_price = item['itemPrice_yesterday']
            new_price = item['itemPrice_today']
            
            if old_price != new_price and old_price > 0:
                change_percent = ((new_price - old_price) / old_price) * 100
                
                if abs(change_percent) >= 5:  # 5%以上の価格変動
                    change = {
                        'type': '💰 値上がり' if change_percent > 0 else '💸 値下がり',
                        'price_change_percent': round(change_percent, 1),
                        'price_now': int(new_price),
                        'price_prev': int(old_price),
                        'rank': int(item['rank_today']),
                        'title': str(item['itemName_today']),
                        'url': str(item['itemUrl_today'])
                    }
                    price_changes.append(change)
        
        return price_changes
    
    def calculate_summary_stats(self, today_df: pd.DataFrame, yesterday_df: pd.DataFrame, 
                              all_changes: List[Dict]) -> Dict[str, Any]:
        """サマリー統計の計算"""
        # 基本統計
        today_avg_price = today_df['itemPrice'].mean()
        yesterday_avg_price = yesterday_df['itemPrice'].mean()
        price_change_percent = ((today_avg_price - yesterday_avg_price) / yesterday_avg_price) * 100
        
        # 変化統計
        new_count = len([c for c in all_changes if c['type'] == '🆕 新規ランクイン'])
        dropped_count = len([c for c in all_changes if c['type'] == '📉 ランキングアウト'])
        price_change_count = len([c for c in all_changes if '値上がり' in c['type'] or '値下がり' in c['type']])
        
        return {
            'analysis_date': datetime.now().isoformat(),
            'total_items_today': len(today_df),
            'total_items_yesterday': len(yesterday_df),
            'avg_price_today': round(today_avg_price, 0),
            'avg_price_yesterday': round(yesterday_avg_price, 0),
            'avg_price_change_percent': round(price_change_percent, 1),
            'new_entries_count': new_count,
            'dropped_entries_count': dropped_count,
            'price_changes_count': price_change_count,
            'total_changes_detected': len(all_changes)
        }
    
    def analyze_keyword_trends(self, today_df: pd.DataFrame) -> Dict[str, float]:
        """キーワードトレンド分析"""
        total_items = len(today_df)
        
        keywords = {
            'lightweight': ['軽量', '超軽量'],
            'carry_on': ['機内持ち込み', '機内持込'],
            'front_open': ['フロントオープン', '前開き'],
            'usb': ['USB', '充電'],
            'silent': ['静音', '静か'],
            'coupon': ['クーポン', 'OFF'],
            'ranking_1st': ['楽天1位', 'ランキング1位', '1位']
        }
        
        trends = {}
        for category, terms in keywords.items():
            count = 0
            for _, item in today_df.iterrows():
                title = str(item['itemName'])
                if any(term in title for term in terms):
                    count += 1
            trends[category] = round((count / total_items) * 100, 1)
        
        return trends
    
    def run_analysis(self) -> str:
        """🦝 RASCAL メイン分析実行"""
        print("🦝 RASCAL Changes Analyzer 開始...")
        
        try:
            # ファイル取得
            today_file, yesterday_file = self.find_latest_files()
            print(f"📊 比較対象: {os.path.basename(yesterday_file)} → {os.path.basename(today_file)}")
            
            # データ読み込み
            today_df = self.load_data(today_file)
            yesterday_df = self.load_data(yesterday_file)
            
            # 各種分析実行
            print("🔍 変化分析中...")
            new_entries = self.analyze_new_entries(today_df, yesterday_df)
            dropped_entries = self.analyze_dropped_entries(today_df, yesterday_df)
            rank_movements = self.analyze_rank_movements(today_df, yesterday_df)
            price_changes = self.analyze_price_changes(today_df, yesterday_df)
            
            # 全変化を統合
            all_changes = new_entries + dropped_entries + rank_movements + price_changes
            
            # 重要度フィルタリング
            print("⚡ 重要度フィルタリング中...")
            filtered_changes = self.filter_important_changes(all_changes)
            
            # サマリー統計
            summary = self.calculate_summary_stats(today_df, yesterday_df, all_changes)
            
            # キーワードトレンド
            keyword_trends = self.analyze_keyword_trends(today_df)
            
            # 結果構築
            result = {
                'timestamp': datetime.now().isoformat(),
                'previous_file': os.path.basename(yesterday_file),
                'current_file': os.path.basename(today_file),
                'summary': summary,
                'keyword_trends': keyword_trends,
                'changes': {
                    'critical': filtered_changes['critical'],
                    'important': filtered_changes['important'], 
                    'notable': filtered_changes['notable']
                },
                'statistics': {
                    'total_changes_analyzed': len(all_changes),
                    'critical_changes': len(filtered_changes['critical']),
                    'important_changes': len(filtered_changes['important']),
                    'notable_changes': len(filtered_changes['notable']),
                    'compression_ratio': f"{(1 - (len(filtered_changes['critical']) + len(filtered_changes['important']) + len(filtered_changes['notable'])) / max(len(all_changes), 1)) * 100:.1f}%"
                }
            }
            
            # ファイル出力
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            output_file = os.path.join(self.changes_dir, f"changes_optimized_{timestamp}.json")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 分析完了: {output_file}")
            print(f"📊 検出変化: {len(all_changes)}件 → {len(filtered_changes['critical']) + len(filtered_changes['important']) + len(filtered_changes['notable'])}件に圧縮")
            print(f"🎯 圧縮率: {result['statistics']['compression_ratio']}")
            
            return output_file
            
        except Exception as e:
            print(f"❌ エラー発生: {e}")
            raise

if __name__ == "__main__":
    analyzer = RASCALChangesAnalyzer()
    output_file = analyzer.run_analysis()
    print(f"\n🦝 RASCAL分析完了: {output_file}")
