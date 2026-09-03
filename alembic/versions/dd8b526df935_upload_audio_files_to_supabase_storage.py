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
    from supabase import create_client, Client
    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Skipping audio upload: SUPABASE_URL and SUPABASE_KEY not found in environment.")
        return

    supabase: Client = create_client(url, key)
    BUCKET_NAME = "sounds"

    # Attempt to create bucket
    try:
        supabase.storage.get_bucket(BUCKET_NAME)
    except Exception:
        print(f"Bucket '{BUCKET_NAME}' does not exist. Creating it now...")
        try:
            supabase.storage.create_bucket(BUCKET_NAME, public=True)
        except Exception as e:
            print(f"Could not create bucket: {e}")

    # Files to upload mapped to destination path
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

        with open(local_path, 'rb') as f:
            content_type = "audio/mpeg" if local_path.endswith(".mp3") else "audio/wav" if local_path.endswith(".wav") else "application/octet-stream"
            try:
                res = supabase.storage.from_(BUCKET_NAME).upload(
                    path=storage_path,
                    file=f,
                    file_options={"content-type": content_type, "upsert": "true"}
                )
                print(f"✅ Successfully uploaded to Supabase Storage: {storage_path}")
            except Exception as e:
                print(f"❌ Failed to upload {storage_path}: {e}")


def downgrade() -> None:
    """Downgrade schema."""
    pass
