#!/usr/bin/env python3
"""
🦝 RASCAL 3.0 Image Analysis System (GitHub Actions Headless Version)
GitHub Actions環境で動作する画像分析システム

主な変更点:
- opencv-python-headless使用（GUI依存性なし）
- matplotlib非インタラクティブモード
- 軽量化・高速化対応
- エラー耐性向上
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

# matplotlib非インタラクティブモード設定
import matplotlib
matplotlib.use('Agg')  # GUI不要のバックエンド

try:
    from PIL import Image, ImageStat
    import cv2
    from sklearn.cluster import KMeans
    from colorthief import ColorThief
    import webcolors
    from io import BytesIO
    import matplotlib.pyplot as plt
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    DEPENDENCIES_OK = True
    print("✅ 画像分析ライブラリ読み込み成功")
except ImportError as e:
    print(f"❌ 画像分析ライブラリ不足: {e}")
    DEPENDENCIES_OK = False

class RASCALImageAnalyzerHeadless:
    """🦝 RASCAL 3.0 GitHub Actions対応画像分析エンジン"""
    
    def __init__(self, max_workers=2, timeout=8):
        if not DEPENDENCIES_OK:
            raise ImportError("必要なライブラリがインストールされていません")
        
        self.max_workers = max_workers  # GitHub Actions用に削減
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 色名マッピング
        self.color_names = {
            'black': '黒', 'white': '白', 'gray': 'グレー', 'grey': 'グレー',
            'red': '赤', 'blue': '青', 'green': '緑', 'yellow': '黄',
            'orange': 'オレンジ', 'purple': '紫', 'pink': 'ピンク',
            'brown': '茶', 'silver': 'シルバー', 'gold': 'ゴールド',
            'navy': 'ネイビー', 'beige': 'ベージュ'
        }
    
    def download_image(self, url: str, max_size=(300, 300)) -> Optional[Image.Image]:
        """画像ダウンロード（GitHub Actions最適化）"""
        try:
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # サイズ制限（3MB）
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 3 * 1024 * 1024:
                return None
            
            # 画像読み込み
            image_data = response.content
            if len(image_data) > 3 * 1024 * 1024:  # 念のため再チェック
                return None
            
            image = Image.open(BytesIO(image_data))
            
            # さらに小さくリサイズ（高速化）
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # RGB変換
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            return image
            
        except Exception as e:
            # エラーを詳細に出力しない（ログ圧縮）
            return None
    
    def analyze_dominant_colors_fast(self, image: Image.Image, num_colors=3) -> List[Dict]:
        """高速色彩分析（GitHub Actions最適化）"""
        try:
            # さらに縮小（高速化優先）
            temp_image = image.copy()
            temp_image.thumbnail((100, 100), Image.Resampling.LANCZOS)
            
            # numpy配列変換
            img_array = np.array(temp_image)
            pixels = img_array.reshape(-1, 3)
            
            # サンプリング（大幅高速化）
            if len(pixels) > 1000:
                indices = np.random.choice(len(pixels), 1000, replace=False)
                pixels = pixels[indices]
            
            # K-means（高速設定）
            unique_pixels = np.unique(pixels, axis=0)
            n_clusters = min(num_colors, len(unique_pixels), 3)  # 最大3色
            
            if n_clusters < 2:
                # 色が少なすぎる場合の処理
                dominant_color = tuple(map(int, pixels[0])) if len(pixels) > 0 else (128, 128, 128)
                return [{
                    'rgb': dominant_color,
                    'hex': '#{:02x}{:02x}{:02x}'.format(*dominant_color),
                    'percentage': 100.0,
                    'name': self.get_color_name_fast(dominant_color)
                }]
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=3, max_iter=50)
            kmeans.fit(pixels)
            
            colors = []
            total_pixels = len(pixels)
            
            for i, color in enumerate(kmeans.cluster_centers_):
                color_rgb = tuple(map(int, color))
                percentage = np.sum(kmeans.labels_ == i) / total_pixels * 100
                
                colors.append({
                    'rgb': color_rgb,
                    'hex': '#{:02x}{:02x}{:02x}'.format(*color_rgb),
                    'percentage': round(percentage, 1),
                    'name': self.get_color_name_fast(color_rgb)
                })
            
            # 割合順にソート
            colors.sort(key=lambda x: x['percentage'], reverse=True)
            return colors[:3]  # 上位3色のみ
            
        except Exception as e:
            # デフォルト色を返す
            return [{
                'rgb': (128, 128, 128),
                'hex': '#808080',
                'percentage': 100.0,
                'name': 'グレー'
            }]
    
    def get_color_name_fast(self, rgb: Tuple[int, int, int]) -> str:
        """高速色名推定"""
        try:
            # 基本色との距離計算（簡易版）
            basic_colors = {
                (0, 0, 0): '黒',
                (255, 255, 255): '白',
                (128, 128, 128): 'グレー',
                (255, 0, 0): '赤',
                (0, 0, 255): '青',
                (0, 255, 0): '緑',
                (255, 255, 0): '黄',
                (255, 165, 0): 'オレンジ',
                (128, 0, 128): '紫',
                (165, 42, 42): '茶',
                (192, 192, 192): 'シルバー'
            }
            
            min_distance = float('inf')
            closest_name = '不明'
            
            for basic_rgb, name in basic_colors.items():
                distance = sum((c1 - c2) ** 2 for c1, c2 in zip(rgb, basic_rgb))
                if distance < min_distance:
                    min_distance = distance
                    closest_name = name
            
            return closest_name
            
        except Exception:
            return '不明'
    
    def analyze_image_quality_fast(self, image: Image.Image) -> Dict[str, float]:
        """高速画像品質分析"""
        try:
            # 基本統計
            stat = ImageStat.Stat(image)
            
            # 明度（簡易計算）
            brightness = sum(stat.mean) / (255.0 * 3)
            
            # コントラスト（標準偏差ベース）
            contrast = sum(stat.stddev) / (255.0 * 3)
            
            # 彩度（簡易計算）
            r, g, b = stat.mean
            max_rgb = max(r, g, b)
            min_rgb = min(r, g, b)
            saturation = (max_rgb - min_rgb) / max_rgb if max_rgb > 0 else 0
            saturation = saturation / 255.0
            
            # 高級感スコア（簡易計算）
            luxury_score = (
                saturation * 30 +        # 適度な彩度
                contrast * 50 +          # 高コントラスト
                (1 - abs(brightness - 0.5)) * 20  # 適度な明度
            )
            
            return {
                'brightness': round(brightness, 3),
                'saturation': round(saturation, 3),
                'contrast': round(contrast, 3),
                'sharpness': round(contrast, 3),  # コントラストで代用
                'luxury_score': round(min(luxury_score, 100), 1)
            }
            
        except Exception:
            return {
                'brightness': 0.5, 'saturation': 0.5, 'contrast': 0.5,
                'sharpness': 0.5, 'luxury_score': 50.0
            }
    
    def classify_suitcase_fast(self, image: Image.Image, item_name: str) -> Dict[str, Any]:
        """高速スーツケース分類"""
        try:
            # 色彩による分類
            colors = self.analyze_dominant_colors_fast(image, 2)
            dominant_color = colors[0] if colors else {'name': '不明', 'percentage': 0}
            
            # 材質推定（簡易版）
            material_hints = []
            dominant_name = dominant_color['name']
            
            if dominant_name in ['黒', 'グレー', 'シルバー']:
                material_hints.append('ハードケース')
            elif dominant_name in ['茶', 'ベージュ']:
                material_hints.append('ソフトケース')
            
            # 整合性チェック（簡易版）
            consistency_score = 0
            item_name_lower = item_name.lower()
            
            # 基本的な整合性チェック
            if 'ハード' in item_name and dominant_name in ['黒', 'グレー', 'シルバー']:
                consistency_score += 40
            elif 'ソフト' in item_name and dominant_name in ['黒', '茶']:
                consistency_score += 40
            
            # 色名チェック
            if any(color in item_name for color in ['黒', '白', 'グレー', '赤', '青', '緑']):
                consistency_score += 30
            
            # サイズ推定
            width, height = image.size
            aspect_ratio = width / height
            size_estimate = '標準' if 0.8 <= aspect_ratio <= 1.2 else '特殊'
            
            return {
                'dominant_color': dominant_name,
                'material_hints': material_hints,
                'size_estimate': size_estimate,
                'consistency_score': min(consistency_score, 100),
                'aspect_ratio': round(aspect_ratio, 2)
            }
            
        except Exception:
            return {
                'dominant_color': '不明', 'material_hints': [], 'size_estimate': '不明',
                'consistency_score': 0, 'aspect_ratio': 1.0
            }
    
    def analyze_single_image_fast(self, row: pd.Series) -> Dict[str, Any]:
        """高速単一画像分析"""
        try:
            image_url = row.get('imageUrl', '')
            if not image_url:
                return self.create_empty_result(row, "画像URLなし")
            
            # 画像ダウンロード
            image = self.download_image(image_url)
            if image is None:
                return self.create_empty_result(row, "画像取得失敗")
            
            # 高速分析実行
            colors = self.analyze_dominant_colors_fast(image)
            quality = self.analyze_image_quality_fast(image)
            classification = self.classify_suitcase_fast(image, row.get('itemName', ''))
            
            return {
                'rank': int(row.get('rank', 0)),
                'itemCode': str(row.get('itemCode', '')),
                'itemName': str(row.get('itemName', ''))[:80],  # さらに短縮
                'price': int(row.get('itemPrice', 0)),
                'imageUrl': image_url,
                'analysis_status': 'success',
                'colors': colors[:2],  # 上位2色のみ
                'quality': quality,
                'classification': classification,
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return self.create_empty_result(row, f"分析エラー")
    
    def create_empty_result(self, row: pd.Series, reason: str) -> Dict[str, Any]:
        """空の分析結果を生成"""
        return {
            'rank': int(row.get('rank', 0)),
            'itemCode': str(row.get('itemCode', '')),
            'itemName': str(row.get('itemName', ''))[:80],
            'price': int(row.get('itemPrice', 0)),
            'imageUrl': row.get('imageUrl', ''),
            'analysis_status': 'failed',
            'error_reason': reason,
            'colors': [],
            'quality': {'brightness': 0, 'saturation': 0, 'contrast': 0, 'sharpness': 0, 'luxury_score': 0},
            'classification': {'dominant_color': '不明', 'material_hints': [], 'size_estimate': '不明', 'consistency_score': 0},
            'analyzed_at': datetime.now().isoformat()
        }
    
    def run_batch_analysis_headless(self, csv_file: str, max_items: int = 30) -> str:
        """🦝 GitHub Actions対応バッチ画像分析"""
        print(f"🎨 RASCAL 3.0 Headless 画像分析開始: {csv_file}")
        
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
        
        # GitHub Actions用に処理数を制限
        if total_images > max_items:
            print(f"⚡ 処理数を{max_items}件に制限（GitHub Actions最適化）")
            df_with_images = df_with_images.head(max_items)
        
        print(f"🎨 画像分析対象: {len(df_with_images)}件")
        
        # 並列分析実行（軽量版）
        results = []
        successful_analyses = 0
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_row = {
                executor.submit(self.analyze_single_image_fast, row): idx 
                for idx, row in df_with_images.iterrows()
            }
            
            for future in as_completed(future_to_row):
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['analysis_status'] == 'success':
                        successful_analyses += 1
                        
                except Exception:
                    # エラーは無視して継続
                    pass
        
        analysis_time = time.time() - start_time
        
        # 統計計算（簡易版）
        stats = self.calculate_basic_statistics(results)
        
        # 結果構築（軽量版）
        final_result = {
            'metadata': {
                'analyzed_at': datetime.now().isoformat(),
                'source_file': os.path.basename(csv_file),
                'total_items': len(df),
                'analyzed_items': len(results),
                'successful_analyses': successful_analyses,
                'success_rate': round((successful_analyses / len(results)) * 100, 1) if results else 0,
                'analysis_time_seconds': round(analysis_time, 1),
                'github_actions_optimized': True
            },
            'statistics': stats,
            'detailed_results': results[:20]  # 上位20件のみ保存
        }
        
        # 結果保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_file = f"image_analysis_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, ensure_ascii=False, indent=1)  # インデント削減
        
        print(f"✅ 画像分析完了: {output_file}")
        print(f"📊 成功率: {final_result['metadata']['success_rate']}%")
        print(f"⚡ 処理時間: {analysis_time:.1f}秒")
        
        return output_file
    
    def calculate_basic_statistics(self, results: List[Dict]) -> Dict[str, Any]:
        """基本統計計算（軽量版）"""
        successful_results = [r for r in results if r['analysis_status'] == 'success']
        
        if not successful_results:
            return {'error': '分析成功データなし'}
        
        # 色彩統計（簡易版）
        color_counts = {}
        for result in successful_results:
            for color in result['colors']:
                color_name = color['name']
                color_counts[color_name] = color_counts.get(color_name, 0) + 1
        
        top_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # 品質統計（簡易版）
        luxury_scores = [r['quality']['luxury_score'] for r in successful_results]
        avg_luxury = sum(luxury_scores) / len(luxury_scores) if luxury_scores else 0
        
        return {
            'top_colors': [{'color': color, 'count': count} for color, count in top_colors],
            'average_luxury_score': round(avg_luxury, 1),
            'analyzed_count': len(successful_results)
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
        return
    
    # 最新ファイルを使用
    latest_file = max(image_csv_files, key=os.path.getctime)
    print(f"🎯 分析対象ファイル: {latest_file}")
    
    # 分析実行
    analyzer = RASCALImageAnalyzerHeadless(max_workers=2, timeout=6)
    result_file = analyzer.run_batch_analysis_headless(latest_file, max_items=30)
    
    if result_file:
        print(f"🦝 RASCAL 3.0 Headless 画像分析完了！")

if __name__ == "__main__":
    main()
