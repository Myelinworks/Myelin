"""upload_audio_files_to_supabase_storage

Revision ID: dd8b526df935
Revises: a2b3c4d5e6f7
Create Date: 2026-09-03 23:30:28.574177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd8b526df935'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema and upload audio files to Supabase Storage."""
    import os
    # Use standard library to avoid missing pip package dependencies
    import os
    import json
    import urllib.request
    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY")
    
    if not url or not key:
        print("Skipping audio upload: SUPABASE_URL and SUPABASE_SECRET_KEY not found in environment.")
        return

    BUCKET_NAME = "sounds"
    
    # Attempt to create bucket
    bucket_url = f"{url}/storage/v1/bucket"
    req = urllib.request.Request(bucket_url, data=json.dumps({"id": BUCKET_NAME, "name": BUCKET_NAME, "public": True}).encode(), headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    })
    try:
        urllib.request.urlopen(req)
        print(f"Bucket '{BUCKET_NAME}' created.")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        if e.code != 400:
            print(f"Bucket creation error: {e.code} - {err_body}")
        else:
            print("Bucket might already exist (400).")

    # Files to upload
    files_to_upload = [
        ("/c:/Users/bhask/OneDrive/Desktop/myelin-backend/MyElin-Backend/supabase/typing-sound.mp3", "typing-sound.mp3"),
        ("/c:/Users/bhask/OneDrive/Desktop/myelin-backend/MyElin-Backend/supabase/WhatsApp Audio 2026-08-28 at 10.36.27 AM.mp3", "whatsapp-audio-2026-08-28.mp3"),
        ("/c:/Users/bhask/OneDrive/Desktop/Myelin/MyElin-Frontend/public/sounds/processing.wav", "processing.wav"),
        ("/c:/Users/bhask/OneDrive/Desktop/Myelin/MyElin-Frontend/public/sounds/quarter-closed.wav", "quarter-closed.wav"),
    ]

    for local_path, storage_path in files_to_upload:
        local_path = local_path.replace("/c:/", "C:/") 
        if not os.path.exists(local_path):
            print(f"Error: File not found -> {local_path}")
            continue

        content_type = "audio/mpeg" if local_path.endswith(".mp3") else "audio/wav" if local_path.endswith(".wav") else "application/octet-stream"
        
        with open(local_path, 'rb') as f:
            file_data = f.read()
            
        # URL encode the filename part of the path if it has spaces
        safe_storage_path = urllib.parse.quote(storage_path)
        upload_url = f"{url}/storage/v1/object/{BUCKET_NAME}/{safe_storage_path}"
        
        try:
            req = urllib.request.Request(upload_url, data=file_data, headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": content_type,
                "x-upsert": "true"
            }, method="POST")
            urllib.request.urlopen(req)
            print(f"Successfully uploaded to Supabase Storage: {storage_path}")
        except urllib.error.HTTPError as e:
            print(f"Failed to upload {storage_path}: HTTP {e.code}: {e.read().decode()}")
        except Exception as e:
            print(f"Failed to upload {storage_path}: {e}")


def downgrade() -> None:
    """Downgrade schema."""
    pass
