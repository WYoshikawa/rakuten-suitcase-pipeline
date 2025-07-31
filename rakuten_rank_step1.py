#!/usr/bin/env python3
"""
🦝 RASCAL TOP100 Analyzer - 高度分析機能維持版
-----------------------------------
TOP100に絞りつつ重要な分析機能を維持
- 実売価格推定分析
- 商品名品質評価
- キーワード重要度分析
- 詳細な市場分析
"""
import pandas as pd
import glob
import os
from datetime import datetime
import json
import re

class RASCALTOP100Analyzer:
    """TOP100専用高度分析器"""
    
    def __init__(self):
        self.data_dir = "data"
        self.changes_dir = os.path.join(self.data_dir, "changes")
        
        # キーワード重要度設定
        self.tier1_keywords = ["軽量", "機内持ち込み", "キャリーケース"]
        self.tier2_keywords = ["TSAロック", "静音", "USB"]
        self.tier3_keywords = ["フロントオープン", "ストッパー", "拡張"]
        
        os.makedirs(self.changes_dir, exist_ok=True)
    
    def find_latest_files(self):
        """最新2ファイルを取得"""
        csv_files = sorted(glob.glob(os.path.join(self.data_dir, "rank_base_*.csv")))
        if len(csv_files) < 2:
            raise FileNotFoundError("比較用データが不足")
        return csv_files[-1], csv_files[-2]
    
    def load_data(self, filepath):
        """データ読み込み"""
        return pd.read_csv(filepath)
    
    def analyze_price_structure(self, df):
        """価格構造分析"""
        price_stats = {
            "basic_stats": {
                "total_items": len(df),
                "avg_price": round(df['itemPrice'].mean(), 0),
                "median_price": round(df['itemPrice'].median(), 0),
                "min_price": int(df['itemPrice'].min()),
                "max_price": int(df['itemPrice'].max()),
                "price_std": round(df['itemPrice'].std(), 0)
            }
        }
        
        # 価格帯分析
        price_ranges = {
            "under_10k": len(df[df['itemPrice'] < 10000]),
            "10k_to_20k": len(df[(df['itemPrice'] >= 10000) & (df['itemPrice'] < 20000)]),
            "20k_to_50k": len(df[(df['itemPrice'] >= 20000) & (df['itemPrice'] < 50000)]),
            "over_50k": len(df[df['itemPrice'] >= 50000])
        }
        price_stats["price_ranges"] = price_ranges
        
        return price_stats
    
    def analyze_real_price_estimation(self, df):
        """実売価格推定分析"""
        if 'estimated_real_price' not in df.columns:
            return {"analysis": "実売価格データなし"}
        
        # 価格操作検出
        manipulated = df[df['itemPrice'] != df['estimated_real_price']]
        
        if len(manipulated) == 0:
            return {"price_manipulation_rate": 0, "examples": []}
        
        manipulation_rate = len(manipulated) / len(df) * 100
        avg_discount_amount = (df['itemPrice'] - df['estimated_real_price']).mean()
        avg_discount_rate = ((df['itemPrice'] - df['estimated_real_price']) / df['itemPrice'] * 100).mean()
        
        # 操作例（上位5件）
        examples = []
        for _, item in manipulated.head(5).iterrows():
            discount = item['itemPrice'] - item['estimated_real_price']
            discount_rate = (discount / item['itemPrice']) * 100
            examples.append({
                "rank": int(item['rank']),
                "display_price": int(item['itemPrice']),
                "estimated_real_price": int(item['estimated_real_price']),
                "discount_amount": int(discount),
                "discount_rate": round(discount_rate, 1)
            })
        
        return {
            "price_manipulation_rate": round(manipulation_rate, 1),
            "avg_discount_amount": round(avg_discount_amount, 0),
            "avg_discount_rate": round(avg_discount_rate, 1),
            "manipulated_count": len(manipulated),
            "examples": examples
        }
    
    def analyze_name_quality(self, df):
        """商品名品質分析"""
        if 'name_quality_score' not in df.columns:
            return {"analysis": "品質スコアデータなし"}
        
        quality_stats = {
            "avg_score": round(df['name_quality_score'].mean(), 1),
            "median_score": round(df['name_quality_score'].median(), 1),
            "min_score": int(df['name_quality_score'].min()),
            "max_score": int(df['name_quality_score'].max())
        }
        
        # 品質分布
        quality_ranges = {
            "excellent_90_plus": len(df[df['name_quality_score'] >= 90]),
            "good_80_to_89": len(df[(df['name_quality_score'] >= 80) & (df['name_quality_score'] < 90)]),
            "average_70_to_79": len(df[(df['name_quality_score'] >= 70) & (df['name_quality_score'] < 80)]),
            "poor_under_70": len(df[df['name_quality_score'] < 70])
        }
        
        # 文字数分析
        df['name_length'] = df['itemName'].str.len()
        length_stats = {
            "avg_length": round(df['name_length'].mean(), 1),
            "long_names_160_plus": len(df[df['name_length'] > 160]),
            "optimal_80_to_160": len(df[(df['name_length'] >= 80) & (df['name_length'] <= 160)]),
            "short_names_under_80": len(df[df['name_length'] < 80])
        }
        
        return {
            "quality_stats": quality_stats,
            "quality_distribution": quality_ranges,
            "length_analysis": length_stats
        }
    
    def analyze_keyword_importance(self, df):
        """キーワード重要度分析"""
        total_items = len(df)
        
        def count_keyword_occurrences(keywords, label):
            results = {}
            for keyword in keywords:
                count = df['itemName'].str.contains(keyword, case=False, na=False).sum()
                percentage = round((count / total_items) * 100, 1)
                results[keyword] = {"count": int(count), "percentage": percentage}
            return results
        
        keyword_analysis = {
            "tier1_high_importance": count_keyword_occurrences(self.tier1_keywords, "Tier1"),
            "tier2_medium_importance": count_keyword_occurrences(self.tier2_keywords, "Tier2"),
            "tier3_basic_importance": count_keyword_occurrences(self.tier3_keywords, "Tier3")
        }
        
        # 最も重要なキーワード順位
        all_keywords = []
        for tier, keywords in keyword_analysis.items():
            for keyword, data in keywords.items():
                all_keywords.append((keyword, data["percentage"], tier))
        
        all_keywords.sort(key=lambda x: x[1], reverse=True)
        top_keywords = all_keywords[:10]
        
        return {
            "keyword_tiers": keyword_analysis,
            "top_keywords": [{"keyword": k[0], "percentage": k[1], "tier": k[2]} for k in top_keywords]
        }
    
    def analyze_feature_distribution(self, df):
        """機能分布分析"""
        feature_cols = [col for col in df.columns if col.startswith(('has_', 'is_', 'for_', 'appeal_'))]
        
        feature_analysis = {}
        total_items = len(df)
        
        for col in feature_cols:
            count = df[col].sum()
            percentage = round((count / total_items) * 100, 1)
            feature_name = col.replace('has_', '').replace('is_', '').replace('for_', '').replace('appeal_', '')
            feature_analysis[feature_name] = {
                "count": int(count),
                "percentage": percentage
            }
        
        # 機能別ソート
        sorted_features = sorted(feature_analysis.items(), key=lambda x: x[1]["percentage"], reverse=True)
        
        return {
            "all_features": feature_analysis,
            "top_features": dict(sorted_features[:15]),
            "feature_summary": {
                "total_features_tracked": len(feature_cols),
                "avg_feature_adoption": round(sum(f["percentage"] for f in feature_analysis.values()) / len(feature_analysis), 1)
            }
        }
    
    def analyze_market_changes(self, today_df, yesterday_df):
        """市場変化分析"""
        yesterday_codes = set(yesterday_df['itemCode'])
        today_codes = set(today_df['itemCode'])
        
        # 基本変化統計
        new_items = today_codes - yesterday_codes
        dropped_items = yesterday_codes - today_codes
        common_items = today_codes & yesterday_codes
        
        # 価格変動分析（継続商品のみ）
        if len(common_items) > 0:
            common_df = pd.merge(
                today_df[['itemCode', 'itemPrice', 'rank']],
                yesterday_df[['itemCode', 'itemPrice']],
                on='itemCode',
                suffixes=('_today', '_yesterday')
            )
            
            price_changed = common_df[common_df['itemPrice_today'] != common_df['itemPrice_yesterday']]
            
            price_change_analysis = {
                "items_with_price_change": len(price_changed),
                "price_change_rate": round(len(price_changed) / len(common_df) * 100, 1) if len(common_df) > 0 else 0
            }
        else:
            price_change_analysis = {"items_with_price_change": 0, "price_change_rate": 0}
        
        return {
            "market_flow": {
                "new_entries": len(new_items),
                "dropped_items": len(dropped_items),
                "continuing_items": len(common_items),
                "turnover_rate": round((len(new_items) + len(dropped_items)) / len(yesterday_df) * 100, 1)
            },
            "price_dynamics": price_change_analysis
        }
    
    def display_top10_products_full(self, df):
        """TOP10商品名を完全版で表示"""
        print(f"\n🏆 TOP10商品一覧（完全版）")
        print("="*100)
        
        top10 = df.head(10)
        for _, item in top10.iterrows():
            rank = item['rank']
            name = item['itemName']
            price = item['itemPrice']
            review_avg = item['reviewAverage']
            review_count = item['reviewCount']
            
            print(f"{rank:2d}位: {name}")
            print(f"      ¥{price:,} | ⭐{review_avg:.1f} ({review_count:,}件)")
            print("")
        
        # 商品名統計も追加
        name_lengths = [len(item['itemName']) for _, item in top10.iterrows()]
        avg_length = sum(name_lengths) / len(name_lengths)
        
        print(f"📏 TOP10商品名統計:")
        print(f"  平均文字数: {avg_length:.1f}文字")
        print(f"  最長: {max(name_lengths)}文字")
        print(f"  最短: {min(name_lengths)}文字")
    
    def generate_comprehensive_analysis(self):
        """包括的分析実行"""
        print("🦝 RASCAL TOP100 包括分析開始...")
        
        try:
            # ファイル取得
            today_file, yesterday_file = self.find_latest_files()
            today_df = self.load_data(today_file)
            yesterday_df = self.load_data(yesterday_file)
            
            print(f"📊 分析対象: TOP{len(today_df)}商品")
            
            # 各種分析実行
            print("💰 価格構造分析中...")
            price_analysis = self.analyze_price_structure(today_df)
            
            print("🔍 実売価格推定分析中...")
            real_price_analysis = self.analyze_real_price_estimation(today_df)
            
            print("📝 商品名品質分析中...")
            name_quality_analysis = self.analyze_name_quality(today_df)
            
            print("🏷️ キーワード重要度分析中...")
            keyword_analysis = self.analyze_keyword_importance(today_df)
            
            print("⚙️ 機能分布分析中...")
            feature_analysis = self.analyze_feature_distribution(today_df)
            
            print("📈 市場変化分析中...")
            market_change_analysis = self.analyze_market_changes(today_df, yesterday_df)
            
            # 結果統合
            comprehensive_result = {
                "analysis_timestamp": datetime.now().isoformat(),
                "files_analyzed": {
                    "current": os.path.basename(today_file),
                    "previous": os.path.basename(yesterday_file)
                },
                "price_analysis": price_analysis,
                "real_price_estimation": real_price_analysis,
                "name_quality_analysis": name_quality_analysis,
                "keyword_importance": keyword_analysis,
                "feature_distribution": feature_analysis,
                "market_changes": market_change_analysis,
                "analysis_summary": {
                    "total_items_analyzed": len(today_df),
                    "analysis_scope": "TOP100",
                    "key_features_tracked": 30,
                    "advanced_analytics_enabled": True
                }
            }
            
            # 結果保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            output_file = os.path.join(self.changes_dir, f"top100_analysis_{timestamp}.json")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(comprehensive_result, f, ensure_ascii=False, indent=2)
            
            # レポート表示
            self.print_analysis_report(comprehensive_result)
            
            print(f"\n✅ 包括分析完了: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ 分析エラー: {e}")
            raise
    
    def print_analysis_report(self, result):
        """分析レポート表示"""
        print("\n" + "="*50)
        print("🦝 RASCAL TOP100 包括分析レポート")
        print("="*50)
        
        # 価格分析
        price = result["price_analysis"]["basic_stats"]
        print(f"💰 価格分析")
        print(f"  平均価格: ¥{price['avg_price']:,.0f}")
        print(f"  中央値: ¥{price['median_price']:,.0f}")
        print(f"  価格範囲: ¥{price['min_price']:,} - ¥{price['max_price']:,}")
        
        # 実売価格推定
        real_price = result["real_price_estimation"]
        if "price_manipulation_rate" in real_price:
            print(f"\n🔍 実売価格推定")
            print(f"  価格操作検出率: {real_price['price_manipulation_rate']}%")
            print(f"  平均割引額: ¥{real_price['avg_discount_amount']:,.0f}")
            print(f"  平均割引率: {real_price['avg_discount_rate']}%")
        
        # 商品名品質
        quality = result["name_quality_analysis"]
        if "quality_stats" in quality:
            stats = quality["quality_stats"]
            print(f"\n📝 商品名品質")
            print(f"  平均品質スコア: {stats['avg_score']}点")
            print(f"  高品質商品(90点以上): {quality['quality_distribution']['excellent_90_plus']}件")
        
        # キーワード重要度
        keywords = result["keyword_importance"]["top_keywords"]
        print(f"\n🏷️ 重要キーワード TOP5")
        for i, kw in enumerate(keywords[:5], 1):
            print(f"  {i}. {kw['keyword']}: {kw['percentage']}% ({kw['tier']})")
        
        # 機能分布
        features = result["feature_distribution"]["top_features"]
        print(f"\n⚙️ 主要機能 TOP5")
        for i, (feature, data) in enumerate(list(features.items())[:5], 1):
            print(f"  {i}. {feature}: {data['count']}件 ({data['percentage']}%)")
        
        # 市場変化
        changes = result["market_changes"]["market_flow"]
        print(f"\n📈 市場変化")
        print(f"  新規参入: {changes['new_entries']}件")
        print(f"  ランキングアウト: {changes['dropped_items']}件")
        print(f"  継続商品: {changes['continuing_items']}件")
        print(f"  市場流動性: {changes['turnover_rate']}%")

if __name__ == "__main__":
    analyzer = RASCALTOP100Analyzer()
    analyzer.generate_comprehensive_analysis()
