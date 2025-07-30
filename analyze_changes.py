#!/usr/bin/env python3
"""
🎨 RASCAL 3.0 Enhanced Changes Analyzer with Image Analysis
画像分析データを含む楽天スーツケースランキング変化分析

画像分析結果を活用した新しい洞察:
- 色彩トレンドの変化
- 高級感スコアの推移  
- デザイン傾向の分析
- ビジュアル戦略の効果測定
"""

import pandas as pd
import json
import glob
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class RASCALImageChangesAnalyzer:
    """🎨 RASCAL 3.0 画像分析対応変化分析器"""
    
    def __init__(self):
        self.data_dir = "data"
        self.changes_dir = os.path.join(self.data_dir, "changes")
        self.images_dir = os.path.join(self.data_dir, "images")
        
        # ディレクトリ作成
        os.makedirs(self.changes_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
    
    def find_latest_files(self) -> tuple[str, str]:
        """最新と前日のCSVファイルを取得（画像対応）"""
        # 画像付きファイルを優先
        image_csv_files = glob.glob(os.path.join(self.data_dir, "rank_base_*_with_images.csv"))
        regular_csv_files = glob.glob(os.path.join(self.data_dir, "rank_base_*.csv"))
        
        all_csv_files = image_csv_files + [f for f in regular_csv_files if "_with_images" not in f]
        
        if len(all_csv_files) < 2:
            raise FileNotFoundError("比較に必要な2つのCSVファイルが見つかりません")
        
        all_csv_files.sort()
        return all_csv_files[-1], all_csv_files[-2]  # 最新, 前日
    
    def find_latest_image_analysis(self) -> Optional[str]:
        """最新の画像分析結果を取得"""
        json_files = glob.glob(os.path.join(self.images_dir, "image_analysis_*.json"))
        if not json_files:
            json_files = glob.glob("image_analysis_*.json")
        
        if json_files:
            return max(json_files, key=os.path.getctime)
        return None
    
    def load_image_analysis_data(self) -> Optional[Dict]:
        """画像分析データ読み込み"""
        image_analysis_file = self.find_latest_image_analysis()
        if not image_analysis_file:
            return None
        
        try:
            with open(image_analysis_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"画像分析データ読み込みエラー: {e}")
            return None
    
    def analyze_color_trends(self, today_df: pd.DataFrame, image_data: Dict) -> Dict[str, Any]:
        """色彩トレンド分析"""
        if not image_data or 'detailed_results' not in image_data:
            return {'error': '画像分析データなし'}
        
        try:
            # 今日の色彩データ収集
            color_distribution = {}
            luxury_by_color = {}
            price_by_color = {}
            
            for result in image_data['detailed_results']:
                if result['analysis_status'] != 'success':
                    continue
                
                for color_info in result['colors']:
                    color_name = color_info['name']
                    percentage = color_info['percentage']
                    
                    if color_name not in color_distribution:
                        color_distribution[color_name] = {'count': 0, 'total_percentage': 0, 'items': []}
                    
                    color_distribution[color_name]['count'] += 1
                    color_distribution[color_name]['total_percentage'] += percentage
                    color_distribution[color_name]['items'].append({
                        'rank': result['rank'],
                        'price': result['price'],
                        'luxury_score': result['quality']['luxury_score']
                    })
            
            # 色別統計計算
            color_stats = []
            for color, data in color_distribution.items():
                if data['count'] >= 2:  # 2件以上の色のみ
                    avg_price = sum(item['price'] for item in data['items']) / len(data['items'])
                    avg_luxury = sum(item['luxury_score'] for item in data['items']) / len(data['items'])
                    avg_rank = sum(item['rank'] for item in data['items']) / len(data['items'])
                    
                    color_stats.append({
                        'color': color,
                        'count': data['count'],
                        'market_share': round((data['count'] / len(image_data['detailed_results'])) * 100, 1),
                        'avg_price': round(avg_price, 0),
                        'avg_luxury_score': round(avg_luxury, 1),
                        'avg_rank': round(avg_rank, 1)
                    })
            
            # 人気色順にソート
            color_stats.sort(key=lambda x: x['count'], reverse=True)
            
            return {
                'top_colors': color_stats[:5],
                'total_colors_analyzed': len(color_distribution),
                'high_luxury_colors': [c for c in color_stats if c['avg_luxury_score'] >= 70],
                'premium_price_colors': [c for c in color_stats if c['avg_price'] >= 40000]
            }
            
        except Exception as e:
            return {'error': f'色彩トレンド分析エラー: {e}'}
    
    def analyze_visual_quality_trends(self, image_data: Dict) -> Dict[str, Any]:
        """ビジュアル品質トレンド分析"""
        if not image_data or 'detailed_results' not in image_data:
            return {'error': '画像分析データなし'}
        
        try:
            successful_results = [r for r in image_data['detailed_results'] if r['analysis_status'] == 'success']
            
            if not successful_results:
                return {'error': '分析成功データなし'}
            
            # 品質指標集計
            quality_metrics = {
                'luxury_scores': [r['quality']['luxury_score'] for r in successful_results],
                'brightness': [r['quality']['brightness'] for r in successful_results],
                'saturation': [r['quality']['saturation'] for r in successful_results],
                'contrast': [r['quality']['contrast'] for r in successful_results]
            }
            
            # 統計計算
            stats = {}
            for metric, values in quality_metrics.items():
                stats[metric] = {
                    'average': round(sum(values) / len(values), 2),
                    'max': round(max(values), 2),
                    'min': round(min(values), 2)
                }
            
            # ランク別品質分析
            rank_quality = {'top30': [], 'middle': [], 'lower': []}
            for result in successful_results:
                rank = result['rank']
                luxury_score = result['quality']['luxury_score']
                
                if rank <= 30:
                    rank_quality['top30'].append(luxury_score)
                elif rank <= 70:
                    rank_quality['middle'].append(luxury_score)
                else:
                    rank_quality['lower'].append(luxury_score)
            
            rank_quality_stats = {}
            for category, scores in rank_quality.items():
                if scores:
                    rank_quality_stats[category] = {
                        'average_luxury': round(sum(scores) / len(scores), 1),
                        'count': len(scores)
                    }
            
            return {
                'overall_quality': stats,
                'rank_quality_correlation': rank_quality_stats,
                'high_quality_count': len([s for s in quality_metrics['luxury_scores'] if s >= 70]),
                'quality_distribution': {
                    'excellent': len([s for s in quality_metrics['luxury_scores'] if s >= 80]),
                    'good': len([s for s in quality_metrics['luxury_scores'] if 60 <= s < 80]),
                    'average': len([s for s in quality_metrics['luxury_scores'] if 40 <= s < 60]),
                    'poor': len([s for s in quality_metrics['luxury_scores'] if s < 40])
                }
            }
            
        except Exception as e:
            return {'error': f'品質トレンド分析エラー: {e}'}
    
    def analyze_design_consistency(self, image_data: Dict) -> Dict[str, Any]:
        """デザイン整合性分析"""
        if not image_data or 'detailed_results' not in image_data:
            return {'error': '画像分析データなし'}
        
        try:
            successful_results = [r for r in image_data['detailed_results'] if r['analysis_status'] == 'success']
            
            consistency_scores = [r['classification']['consistency_score'] for r in successful_results]
            
            if not consistency_scores:
                return {'error': '整合性データなし'}
            
            avg_consistency = sum(consistency_scores) / len(consistency_scores)
            
            # 整合性レベル別分類
            consistency_levels = {
                'excellent': len([s for s in consistency_scores if s >= 80]),
                'good': len([s for s in consistency_scores if 60 <= s < 80]),
                'fair': len([s for s in consistency_scores if 40 <= s < 60]),
                'poor': len([s for s in consistency_scores if s < 40])
            }
            
            # 低整合性商品の特定
            low_consistency_items = []
            for result in successful_results:
                if result['classification']['consistency_score'] < 50:
                    low_consistency_items.append({
                        'rank': result['rank'],
                        'name': result['itemName'][:50],
                        'consistency_score': result['classification']['consistency_score'],
                        'dominant_color': result['classification']['dominant_color']
                    })
            
            return {
                'average_consistency': round(avg_consistency, 1),
                'consistency_distribution': consistency_levels,
                'low_consistency_items': low_consistency_items[:5],  # 上位5件
                'total_analyzed': len(consistency_scores)
            }
            
        except Exception as e:
            return {'error': f'整合性分析エラー: {e}'}
    
    def run_enhanced_analysis(self) -> str:
        """🎨 RASCAL 3.0 拡張分析実行"""
        print("🎨 RASCAL 3.0 Enhanced Changes Analyzer 開始...")
        
        try:
            # ファイル取得
            today_file, yesterday_file = self.find_latest_files()
            print(f"📊 比較対象: {os.path.basename(yesterday_file)} → {os.path.basename(today_file)}")
            
            # データ読み込み
            today_df = pd.read_csv(today_file)
            yesterday_df = pd.read_csv(yesterday_file)
            
            # 画像分析データ読み込み
            image_data = self.load_image_analysis_data()
            has_image_analysis = image_data is not None
            
            print(f"🎨 画像分析データ: {'有効' if has_image_analysis else '無効'}")
            
            # 基本変化分析（既存ロジック）
            basic_analysis = self.run_basic_analysis(today_df, yesterday_df)
            
            # 拡張分析（画像データがある場合）
            enhanced_analysis = {}
            if has_image_analysis:
                print("🎨 色彩・品質トレンド分析中...")
                enhanced_analysis = {
                    'color_trends': self.analyze_color_trends(today_df, image_data),
                    'visual_quality': self.analyze_visual_quality_trends(image_data),
                    'design_consistency': self.analyze_design_consistency(image_data),
                    'image_analysis_metadata': image_data.get('metadata', {})
                }
            
            # 結果統合
            result = {
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'enhanced_with_images' if has_image_analysis else 'basic',
                'source_files': {
                    'current': os.path.basename(today_file),
                    'previous': os.path.basename(yesterday_file)
                },
                'basic_analysis': basic_analysis,
                'enhanced_analysis': enhanced_analysis if has_image_analysis else None,
                'summary': self.generate_enhanced_summary(basic_analysis, enhanced_analysis, has_image_analysis)
            }
            
            # ファイル出力
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            output_file = os.path.join(self.changes_dir, f"enhanced_changes_{timestamp}.json")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 拡張分析完了: {output_file}")
            if has_image_analysis:
                print("🎨 画像分析による新しい洞察が含まれています！")
            
            return output_file
            
        except Exception as e:
            print(f"❌ エラー発生: {e}")
            raise
    
    def run_basic_analysis(self, today_df: pd.DataFrame, yesterday_df: pd.DataFrame) -> Dict[str, Any]:
        """基本変化分析（既存ロジック）"""
        # 価格変化
        today_avg = today_df['itemPrice'].mean()
        yesterday_avg = yesterday_df['itemPrice'].mean()
        price_change = ((today_avg - yesterday_avg) / yesterday_avg) * 100
        
        # 商品入れ替わり
        today_codes = set(today_df['itemCode'])
        yesterday_codes = set(yesterday_df['itemCode'])
        
        new_items = len(today_codes - yesterday_codes)
        dropped_items = len(yesterday_codes - today_codes)
        common_items = len(today_codes & yesterday_codes)
        
        return {
            'price_analysis': {
                'today_average': round(today_avg, 0),
                'yesterday_average': round(yesterday_avg, 0),
                'change_percent': round(price_change, 1)
            },
            'market_dynamics': {
                'new_entries': new_items,
                'dropped_items': dropped_items,
                'continuing_items': common_items,
                'turnover_rate': round((new_items + dropped_items) / len(today_df) * 100, 1)
            }
        }
    
    def generate_enhanced_summary(self, basic: Dict, enhanced: Dict, has_images: bool) -> Dict[str, str]:
        """拡張サマリー生成"""
        summary = {
            'market_trend': f"平均価格{basic['price_analysis']['change_percent']:+.1f}%変動",
            'market_fluidity': f"商品入れ替わり率{basic['market_dynamics']['turnover_rate']:.1f}%"
        }
        
        if has_images and enhanced and 'color_trends' in enhanced:
            color_data = enhanced['color_trends']
            if 'top_colors' in color_data and color_data['top_colors']:
                top_color = color_data['top_colors'][0]['color']
                summary['visual_trend'] = f"支配色: {top_color}"
            
            if 'visual_quality' in enhanced:
                quality_data = enhanced['visual_quality']
                if 'overall_quality' in quality_data:
                    avg_luxury = quality_data['overall_quality'].get('luxury_scores', {}).get('average', 0)
                    summary['quality_trend'] = f"平均高級感スコア: {avg_luxury:.1f}点"
        
        return summary

def main():
    """メイン実行"""
    analyzer = RASCALImageChangesAnalyzer()
    result_file = analyzer.run_enhanced_analysis()
    
    print(f"\n🦝 RASCAL 3.0 拡張分析完了！")
    print(f"📁 結果ファイル: {result_file}")
    print(f"🎨 画像分析による深い市場洞察を獲得しました！")

if __name__ == "__main__":
    main()
