import os
import json
import glob
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_to_google_drive():
    # 環境変数から認証情報を取得
    service_account_info = json.loads(os.environ['GDRIVE_JSON'])
    folder_id = os.environ['GDRIVE_FOLDER']
    
    # 認証
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    
    # Google Drive API クライアント作成
    service = build('drive', 'v3', credentials=credentials)
    
    # アップロードするファイルを探す
    csv_files = glob.glob('rank_base_*.csv')
    if not csv_files:
        print("CSV ファイルが見つかりません")
        return
    
    file_path = csv_files[0]  # 最初に見つかったファイル
    target_name = 'rank_base_daily.csv'
    
    # 既存ファイルがあるかチェック（上書き用）
    existing_files = service.files().list(
        q=f"name='{target_name}' and parents in '{folder_id}'",
        fields="files(id, name)"
    ).execute()
    
    # ファイルメタデータ
    file_metadata = {
        'name': target_name,
        'parents': [folder_id]
    }
    
    # メディアアップロード
    media = MediaFileUpload(file_path, mimetype='text/csv')
    
    if existing_files['files']:
        # 既存ファイルがある場合は更新
        file_id = existing_files['files'][0]['id']
        file = service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
        print(f"ファイルを更新しました: {file.get('name')} (ID: {file.get('id')})")
    else:
        # 新規作成
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name'
        ).execute()
        print(f"ファイルを作成しました: {file.get('name')} (ID: {file.get('id')})")

if __name__ == "__main__":
    upload_to_google_drive()
