#!/usr/bin/env python3
"""Google Drive upload module using service account"""

import os
import io
import logging
import asyncio
from typing import Callable, Tuple, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

LOGGER = logging.getLogger(__name__)

# Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']


class GoogleDrive:
    """Google Drive API wrapper for uploading files"""
    
    def __init__(self, credentials_file: str = None):
        """
        Initialize Google Drive client
        
        Args:
            credentials_file: Path to service account JSON file
        """
        self.credentials_file = credentials_file or os.environ.get('GDRIVE_CREDENTIALS', 'credentials.json')
        self.service = None
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the Drive service"""
        try:
            credentials = None
            
            # First, try file-based credentials
            if os.path.exists(self.credentials_file):
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        self.credentials_file,
                        scopes=SCOPES
                    )
                    LOGGER.info("Using credentials from file")
                except Exception as e:
                    LOGGER.warning(f"Local credentials file failed: {e}. Trying database...")
            
            if not credentials:
                # Try to load from MongoDB
                try:
                    from bot.utils.db_handler import get_db
                    import json
                    
                    db = get_db()
                    if db:
                        creds_data = await db.get_gdrive_credentials()
                        
                        if creds_data:
                            creds_json = json.loads(creds_data)
                            credentials = service_account.Credentials.from_service_account_info(
                                creds_json,
                                scopes=SCOPES
                            )
                            LOGGER.info("Using credentials from MongoDB")
                except Exception as e:
                    LOGGER.warning(f"Could not load credentials from MongoDB: {e}")
            
            if not credentials:
                LOGGER.warning(f"No GDrive credentials found")
                return False
            
            self.service = build('drive', 'v3', credentials=credentials)
            self._initialized = True
            LOGGER.info("Google Drive service initialized")
            return True
        except Exception as e:
            LOGGER.error(f"Failed to initialize Google Drive: {e}")
            return False
    
    @property
    def is_ready(self) -> bool:
        """Check if Drive service is ready"""
        return self._initialized and self.service is not None
    
    async def upload_file(
        self,
        file_path: str,
        folder_id: str = None,
        custom_name: str = None,
        progress_callback: Callable = None
    ) -> Tuple[bool, str]:
        """
        Upload file to Google Drive
        
        Args:
            file_path: Path to the file to upload
            folder_id: Google Drive folder ID (optional)
            custom_name: Custom name for the file (optional)
            progress_callback: Callback for progress updates
            
        Returns:
            Tuple of (success, file_id or error message)
        """
        if not self.is_ready:
            if not await self.initialize():
                return False, "Google Drive not configured"
        
        try:
            file_name = custom_name or os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # File metadata
            file_metadata = {'name': file_name}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Determine MIME type
            mime_type = self._get_mime_type(file_path)
            
            # Create media upload
            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True,
                chunksize=50 * 1024 * 1024  # 50MB chunks
            )
            
            # Create request
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink'
            )
            
            # Execute with progress
            response = None
            while response is None:
                status, response = await asyncio.to_thread(request.next_chunk)
                if status and progress_callback:
                    progress = status.progress() * 100
                    await progress_callback(progress, file_size * status.progress(), file_size)
            
            file_id = response.get('id')
            web_link = response.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")
            
            # Make file publicly accessible (optional)
            await self._set_public_permission(file_id)
            
            LOGGER.info(f"Uploaded file: {file_name} -> {file_id}")
            return True, {
                'id': file_id,
                'name': file_name,
                'link': web_link,
                'size': file_size
            }
            
        except HttpError as e:
            error = str(e)
            LOGGER.error(f"Upload error: {error}")
            return False, error
        except Exception as e:
            error = str(e)
            LOGGER.error(f"Upload error: {error}")
            return False, error
    
    async def _set_public_permission(self, file_id: str) -> bool:
        """Make file publicly accessible"""
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            await asyncio.to_thread(
                self.service.permissions().create(
                    fileId=file_id,
                    body=permission
                ).execute
            )
            return True
        except Exception as e:
            LOGGER.warning(f"Could not set public permission: {e}")
            return False
    
    async def create_folder(self, folder_name: str, parent_id: str = None) -> Tuple[bool, str]:
        """Create a folder in Google Drive"""
        if not self.is_ready:
            if not self.initialize():
                return False, "Google Drive not configured"
        
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = await asyncio.to_thread(
                self.service.files().create(
                    body=file_metadata,
                    fields='id'
                ).execute
            )
            
            return True, folder.get('id')
        except Exception as e:
            return False, str(e)
    
    async def get_file_info(self, file_id: str) -> Optional[dict]:
        """Get file information"""
        if not self.is_ready:
            return None
        
        try:
            file = await asyncio.to_thread(
                self.service.files().get(
                    fileId=file_id,
                    fields='id, name, size, mimeType, webViewLink'
                ).execute
            )
            return file
        except Exception:
            return None
    
    @staticmethod
    def _get_mime_type(file_path: str) -> str:
        """Get MIME type based on file extension"""
        extension = os.path.splitext(file_path)[1].lower()
        
        mime_types = {
            # Video
            '.mp4': 'video/mp4',
            '.mkv': 'video/x-matroska',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.webm': 'video/webm',
            '.flv': 'video/x-flv',
            # Audio
            '.mp3': 'audio/mpeg',
            '.aac': 'audio/aac',
            '.flac': 'audio/flac',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            # Others
            '.srt': 'text/plain',
            '.ass': 'text/plain',
            '.jpg': 'image/jpeg',
            '.png': 'image/png',
        }
        
        return mime_types.get(extension, 'application/octet-stream')


# Global instance
gdrive: GoogleDrive = None


def init_gdrive(credentials_file: str = None) -> GoogleDrive:
    """Initialize the global Google Drive instance"""
    global gdrive
    gdrive = GoogleDrive(credentials_file)
    # Initialization is now async and must be called by the user
    return gdrive


def get_gdrive() -> GoogleDrive:
    """Get the global Google Drive instance"""
    global gdrive
    if gdrive is None:
        gdrive = GoogleDrive()
    return gdrive
