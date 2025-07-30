#!/usr/bin/env python3
"""
🦝 RASCAL 3.0 Image Analysis System
楽天スーツケース画像分析システム - GitHub Actions対応版

▸ 色彩分析（支配色、彩度、明度）
▸ デザイン分類（ハード/ソフト、ブランド推定）
▸ 高級感評価（質感、仕上げ品質）
▸ 整合性チェック（商品名と画像の一致度）
▸ 軽量・高速化によるCI/CD対応
"""

import os
import json
import glob
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

try:
    from PIL import Image, ImageStat
    import cv2
    from sklearn.cluster import KMeans
    from colorthief import ColorThief
    import webcolors
    from io import BytesIO
    import matplotlib.pyplot as plt
    import seaborn as sns
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    DEPENDENCIES_OK = True
except ImportError as e:
    print(f"❌ 画像分析ライブラリが不足: {e}")
    print("pip install pillow opencv-python scikit-learn colorthief webcolors matplotlib seaborn")
    DEPENDENCIES_OK = False

class RASCALImageAnalyzer:
    """🦝 RASCAL 3.0 画像分析エンジン"""
    
    def __init__(self, max_workers=4, timeout=10):
        if not DEPENDENCIES_OK:
            raise ImportError("必要なライブラリがインストールされていません")
        
        self.max_workers = max_workers
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 色名マッピング（日本語対応）
        self.color_names = {
            'black': '黒', 'white': '白', 'gray': 'グレー', 'grey': 'グレー',
            'red': '赤', 'blue': '青', 'green': '緑', 'yellow': '黄',
            'orange': 'オレンジ', 'purple': '紫', 'pink': 'ピンク',
            'brown': '茶', 'silver': 'シルバー', 'gold': 'ゴールド',
            'navy': 'ネイビー', 'beige': 'ベージュ'
        }
    
    def download_image(self, url: str, max_size=(400, 400)) -> Optional[Image.Image]:
        """画像ダウンロード（サイズ制限・高速化）"""
        try:
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # コンテンツサイズチェック（5MB制限）
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 5 * 1024 * 1024:
                return None
            
            # 画像読み込み
            image = Image.open(BytesIO(response.content))
            
            # サイズ調整（高速化）
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # RGB変換
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            return image
            
        except Exception as e:
            print(f"画像ダウンロードエラー {url}: {e}")
            return None
    
    def analyze_dominant_colors(self, image: Image.Image, num_colors=5) -> List[Dict]:
        """支配色分析（高速化版）"""
        try:
            # 画像をさらに縮小（高速化）
            temp_image = image.copy()
            temp_image.thumbnail((150, 150), Image.Resampling.LANCZOS)
            
            # numpy配列に変換
            img_array = np.array(temp_image)
            pixels = img_array.reshape(-1, 3)
            
            # K-means クラスタリング
            kmeans = KMeans(n_clusters=min(num_colors, len(np.unique(pixels, axis=0))), 
                          random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            colors = []
            total_pixels = len(pixels)
            
            for i, color in enumerate(kmeans.cluster_centers_):
                color_rgb = tuple(map(int, color))
                percentage = np.sum(kmeans.labels_ == i) / total_pixels * 100
                
                # 色名推定
                color_name = self.get_color_name(color_rgb)
                
                colors.append({
                    'rgb': color_rgb,
                    'hex': '#{:02x}{:02x}{:02x}'.format(*color_rgb),
                    'percentage': round(percentage, 1),
                    'name': color_name
                })
            
            # 割合順にソート
            colors.sort(key=lambda x: x['percentage'], reverse=True)
            return colors
            
        except Exception as e:
            print(f"色彩分析エラー: {e}")
            return []
    
    def get_color_name(self, rgb: Tuple[int, int, int]) -> str:
        """RGB値から色名を推定"""
        try:
            # webcolorsで最近似色を検索
            closest_name = webcolors.rgb_to_name(rgb)
            return self.color_names.get(closest_name, closest_name)
        except ValueError:
            # 最近似色を手動計算
            min_distance = float('inf')
            closest_name = '不明'
            
            for hex_color, name in webcolors.CSS3_HEX_TO_NAMES.items():
                hex_rgb = webcolors.hex_to_rgb(hex_color)
                distance = sum((c1 - c2) ** 2 for c1, c2 in zip(rgb, hex_rgb))
                if distance < min_distance:
                    min_distance = distance
                    closest_name = self.color_names.get(name, name)
            
            return closest_name
    
    def analyze_image_quality(self, image: Image.Image) -> Dict[str, float]:
        """画像品質・高級感分析"""
        try:
            # 基本統計
            stat = ImageStat.Stat(image)
            
            # 彩度計算
            hsv_image = image.convert('HSV')
            hsv_stat = ImageStat.Stat(hsv_image)
            saturation = hsv_stat.mean[1] / 255.0
            
            # 明度
            brightness = sum(stat.mean) / (255.0 * 3)
            
            # コントラスト（標準偏差ベース）
            contrast = sum(stat.stddev) / (255.0 * 3)
            
            # 鮮明度（エッジ検出ベース）
            gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            sharpness = laplacian.var() / 10000.0  # 正規化
            
            # 高級感スコア（複合指標）
            luxury_score = (
                saturation * 0.3 +           # 適度な彩度
                contrast * 0.4 +             # 高コントラスト  
                min(sharpness, 1.0) * 0.3    # 鮮明度（上限1.0）
            ) * 100
            
            return {
                'brightness': round(brightness, 3),
                'saturation': round(saturation, 3),
                'contrast': round(contrast, 3),
                'sharpness': round(min(sharpness, 1.0), 3),
                'luxury_score': round(min(luxury_score, 100), 1)
            }
            
        except Exception as e:
            print(f"品質分析エラー: {e}")
            return {
                'brightness': 0.5, 'saturation': 0.5, 'contrast': 0.5,
                'sharpness': 0.5, 'luxury_score': 50.0
            }
    
    def classify_suitcase_type(self, image: Image.Image, item_name: str) -> Dict[str, Any]:
        """スーツケース分類（ハード/ソフト、ブランド推定）"""
        try:
            # 色彩による分類
            colors = self.analyze_dominant_colors(image, 3)
            dominant_color = colors[0] if colors else {'name': '不明', 'percentage': 0}
            
            # 材質推定（色・質感ベース）
            material_hints = []
            if any(color['name'] in ['黒', 'グレー', 'シルバー'] for color in colors):
                material_hints.append('ハードケース')
            if any(color['name'] in ['茶', 'ベージュ', '黒'] for color in colors):
                material_hints.append('レザー調')
            
            # 商品名との整合性チェック
            name_lower = item_name.lower()
            consistency_score = 0
            
            # ハード/ソフト判定
            if 'ハード' in item_name and dominant_color['name'] in ['黒', 'グレー', 'シルバー']:
                consistency_score += 30
            elif 'ソフト' in item_name and dominant_color['name'] in ['黒', '茶', 'ネイビー']:
                consistency_score += 30
            
            # 色名整合性
            if dominant_color['name'] in item_name:
                consistency_score += 20
            
            # サイズ推定（アスペクト比ベース）
            width, height = image.size
            aspect_ratio = width / height
            size_estimate = '中型' if 0.7 <= aspect_ratio <= 1.3 else ('横長' if aspect_ratio > 1.3 else '縦長')
            
            return {
                'dominant_color': dominant_color['name'],
                'material_hints': material_hints,
                'size_estimate': size_estimate,
                'consistency_score': min(consistency_score, 100),
                'aspect_ratio': round(aspect_ratio, 2)
            }
            
        except Exception as e:
            print(f"分類エラー: {e}")
            return {
                'dominant_color': '不明', 'material_hints': [], 'size_estimate': '不明',
                'consistency_score': 0, 'aspect_ratio': 1.0
            }
    
    def analyze_single_image(self, row: pd.Series) -> Dict[str, Any]:
        """単一商品の画像分析"""
        try:
            image_url = row.get('imageUrl', '')
            if not image_url:
                return self.create_empty_result(row, "画像URLなし")
            
            # 画像ダウンロード
            image = self.download_image(image_url)
            if image is None:
                return self.create_empty_result(row, "画像取得失敗")
            
            # 各種分析実行
            colors = self.analyze_dominant_colors(image)
            quality = self.analyze_image_quality(image)
            classification = self.classify_suitcase_type(image, row.get('itemName', ''))
            
            return {
                'rank': int(row.get('rank', 0)),
                'itemCode': str(row.get('itemCode', '')),
                'itemName': str(row.get('itemName', ''))[:100],  # 長すぎる名前は切り捨て
                'price': int(row.get('itemPrice', 0)),
                'imageUrl': image_url,
                'analysis_status': 'success',
                'colors': colors[:3],  # 上位3色のみ
                'quality': quality,
                'classification': classification,
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return self.create_empty_result(row, f"分析エラー: {str(e)}")
    
    def create_empty_result(self, row: pd.Series, reason: str) -> Dict[str, Any]:
        """空の分析結果を生成"""
        return {
            'rank': int(row.get('rank', 0)),
            'itemCode': str(row.get('itemCode', '')),
            'itemName': str(row.get('itemName', ''))[:100],
            'price': int(row.get('itemPrice', 0)),
            'imageUrl': row.get('imageUrl', ''),
            'analysis_status': 'failed',
            'error_reason': reason,
            'colors': [],
            'quality': {'brightness': 0, 'saturation': 0, 'contrast': 0, 'sharpness': 0, 'luxury_score': 0},
            'classification': {'dominant_color': '不明', 'material_hints': [], 'size_estimate': '不明', 'consistency_score': 0},
            'analyzed_at': datetime.now().isoformat()
        }
    
    def run_batch_analysis(self, csv_file: str, max_items: int = 100) -> str:
        """🦝 バッチ画像分析（GitHub Actions最適化）"""
        print(f"🎨 RASCAL 3.0 画像分析開始: {csv_file}")
        
        # CSV読み込み
        try:
            df = pd.read_csv(csv_file)
            print(f"📊 データ読み込み: {len(df)}件")
        except Exception as e:
            print(f"❌ CSVファイル読み込みエラー: {e}")
            return ""
        
        # 画像URLがある行のみ抽出
        df_with_images = df[df['imageUrl'].notna() & (df['imageUrl'] != '')].copy()
        total_images = len(df_with_images)
        
        if total_images == 0:
            print("❌ 分析可能な画像URLが見つかりません")
            return ""
        
        # GitHub Actions環境では処理数を制限
        if total_images > max_items:
            print(f"⚡ 処理数を{max_items}件に制限（GitHub Actions最適化）")
            df_with_images = df_with_images.head(max_items)
        
        print(f"🎨 画像分析対象: {len(df_with_images)}件")
        
        # 並列分析実行
        results = []
        successful_analyses = 0
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 分析タスク投入
            future_to_row = {
                executor.submit(self.analyze_single_image, row): idx 
                for idx, row in df_with_images.iterrows()
            }
            
            # 結果回収
            for future in as_completed(future_to_row):
                result = future.result()
                results.append(result)
                
                if result['analysis_status'] == 'success':
                    successful_analyses += 1
                
                # 進捗表示
                if len(results) % 10 == 0:
                    print(f"🔄 分析進捗: {len(results)}/{len(df_with_images)}件")
        
        analysis_time = time.time() - start_time
        
        # 統計計算
        stats = self.calculate_analysis_statistics(results)
        
        # 結果構築
        final_result = {
            'metadata': {
                'analyzed_at': datetime.now().isoformat(),
                'source_file': os.path.basename(csv_file),
                'total_items': len(df),
                'analyzed_items': len(results),
                'successful_analyses': successful_analyses,
                'success_rate': round((successful_analyses / len(results)) * 100, 1),
                'analysis_time_seconds': round(analysis_time, 1),
                'items_per_second': round(len(results) / analysis_time, 2)
            },
            'statistics': stats,
            'detailed_results': results
        }
        
        # 結果保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_file = f"image_analysis_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 画像分析完了: {output_file}")
        print(f"📊 成功率: {final_result['metadata']['success_rate']}%")
        print(f"⚡ 処理速度: {final_result['metadata']['items_per_second']}件/秒")
        
        return output_file
    
    def calculate_analysis_statistics(self, results: List[Dict]) -> Dict[str, Any]:
        """分析統計計算"""
        successful_results = [r for r in results if r['analysis_status'] == 'success']
        
        if not successful_results:
            return {'error': '分析成功データなし'}
        
        # 色彩統計
        all_colors = []
        for result in successful_results:
            for color in result['colors']:
                all_colors.append(color['name'])
        
        color_counts = {}
        for color in all_colors:
            color_counts[color] = color_counts.get(color, 0) + 1
        
        top_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # 品質統計
        luxury_scores = [r['quality']['luxury_score'] for r in successful_results]
        avg_luxury_score = sum(luxury_scores) / len(luxury_scores) if luxury_scores else 0
        
        # 価格帯別分析
        price_ranges = {'~20000': 0, '20000-40000': 0, '40000-60000': 0, '60000+': 0}
        for result in successful_results:
            price = result['price']
            if price < 20000:
                price_ranges['~20000'] += 1
            elif price < 40000:
                price_ranges['20000-40000'] += 1
            elif price < 60000:
                price_ranges['40000-60000'] += 1
            else:
                price_ranges['60000+'] += 1
        
        return {
            'color_analysis': {
                'top_colors': [{'color': color, 'count': count} for color, count in top_colors],
                'unique_colors': len(color_counts)
            },
            'quality_analysis': {
                'average_luxury_score': round(avg_luxury_score, 1),
                'high_quality_items': len([s for s in luxury_scores if s >= 70]),
                'luxury_score_distribution': {
                    'high': len([s for s in luxury_scores if s >= 70]),
                    'medium': len([s for s in luxury_scores if 40 <= s < 70]),
                    'low': len([s for s in luxury_scores if s < 40])
                }
            },
            'price_range_analysis': price_ranges
        }

def main():
    """メイン実行"""
    if not DEPENDENCIES_OK:
        print("❌ 必要なライブラリがインストールされていません")
        return
    
    # 画像付きCSVファイルを検索
    image_csv_files = glob.glob("rank_base_*_with_images.csv")
    
    if not image_csv_files:
        print("❌ 画像付きCSVファイルが見つかりません")
        print("💡 python rakuten_rank_step1.py --with-images で画像付きデータを取得してください")
        return
    
    # 最新ファイルを使用
    latest_file = max(image_csv_files, key=os.path.getctime)
    print(f"🎯 分析対象ファイル: {latest_file}")
    
    # 分析実行
    analyzer = RASCALImageAnalyzer(max_workers=3, timeout=8)  # GitHub Actions用に軽量化
    result_file = analyzer.run_batch_analysis(latest_file, max_items=50)  # 50件制限
    
    if result_file:
        print(f"🦝 RASCAL 3.0 画像分析完了！")
        print(f"📁 結果ファイル: {result_file}")
        print(f"🎨 スーツケース市場の視覚的洞察を獲得しました！")

if __name__ == "__main__":
    main()
