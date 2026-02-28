"""Supabase storage utility for file uploads and retrieval"""
import os
import uuid
from typing import Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from supabase import Client

try:
    from supabase import create_client
except ImportError:
    create_client = None


class SupabaseStorage:
    """Wrapper for Supabase storage operations"""
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.bucket_name = os.getenv("SUPABASE_BUCKET", "campus-storage")
        self.client: Optional["Client"] = None
        
        if self.url and self.key and create_client:
            self.client = create_client(self.url, self.key)

    
    def is_configured(self) -> bool:
        """Check if Supabase is properly configured"""
        return self.client is not None
    
    def upload_profile_image(
        self, 
        user_id: int, 
        file_path: str,
        file_content: bytes
    ) -> Optional[str]:
        """
        Upload a profile picture to Supabase.
        
        Folder structure: users/{user_id}/profile_picture/{filename}
        
        Args:
            user_id: The user ID
            file_path: Original file path with extension
            file_content: File content bytes
            
        Returns:
            Public URL or None if upload fails
        """
        if not self.is_configured():
            return None
            
        try:
            ext = Path(file_path).suffix.lower()
            filename = f"profile_picture{ext}"
            storage_path = f"users/{user_id}/profile_picture/{filename}"
            
            # If old file exists, delete it
            try:
                self.client.storage.from_(self.bucket_name).remove([storage_path])
            except:
                pass
            
            # Upload new file
            self.client.storage.from_(self.bucket_name).upload(
                storage_path,
                file_content,
                file_options={"content-type": self._get_content_type(ext)}
            )
            
            # Get public URL
            return self._get_public_url(storage_path)
        except Exception as e:
            print(f"Error uploading profile image: {e}")
            return None
    
    def upload_verification_document(
        self,
        user_id: int,
        file_path: str,
        file_content: bytes
    ) -> Optional[str]:
        """
        Upload a verification document (ID card) to Supabase.
        
        Folder structure: users/{user_id}/verification/{filename}
        
        Args:
            user_id: The user ID
            file_path: Original file path with extension
            file_content: File content bytes
            
        Returns:
            Public URL or None if upload fails
        """
        if not self.is_configured():
            return None
            
        try:
            ext = Path(file_path).suffix.lower()
            unique_name = f"id_card_{uuid.uuid4().hex}{ext}"
            storage_path = f"users/{user_id}/verification/{unique_name}"
            
            # Upload file
            self.client.storage.from_(self.bucket_name).upload(
                storage_path,
                file_content,
                file_options={"content-type": self._get_content_type(ext)}
            )
            
            # Get public URL
            return self._get_public_url(storage_path)
        except Exception as e:
            print(f"Error uploading verification document: {e}")
            return None
    
    def upload_marketplace_item(
        self,
        user_id: int,
        item_id: int,
        file_path: str,
        file_content: bytes
    ) -> Optional[str]:
        """
        Upload a marketplace item image to Supabase.
        
        Folder structure: marketplace/{user_id}/items/{item_id}/{filename}
        
        Args:
            user_id: The user ID (owner)
            item_id: The marketplace item ID
            file_path: Original file path with extension
            file_content: File content bytes
            
        Returns:
            Public URL or None if upload fails
        """
        if not self.is_configured():
            return None
            
        try:
            ext = Path(file_path).suffix.lower()
            filename = f"item_image{ext}"
            storage_path = f"marketplace/{user_id}/items/{item_id}/{filename}"
            
            # Upload file
            self.client.storage.from_(self.bucket_name).upload(
                storage_path,
                file_content,
                file_options={"content-type": self._get_content_type(ext)}
            )
            
            # Get public URL
            return self._get_public_url(storage_path)
        except Exception as e:
            print(f"Error uploading marketplace item: {e}")
            return None
    
    def upload_event_image(
        self,
        event_id: int,
        organizer_id: int,
        file_path: str,
        file_content: bytes
    ) -> Optional[str]:
        """
        Upload an event image to Supabase.
        
        Folder structure: events/{event_id}/image_{timestamp}
        
        Args:
            event_id: The event ID
            organizer_id: The user ID (organizer)
            file_path: Original file path with extension
            file_content: File content bytes
            
        Returns:
            Public URL or None if upload fails
        """
        if not self.is_configured():
            return None
            
        try:
            ext = Path(file_path).suffix.lower()
            filename = f"event_image{ext}"
            storage_path = f"events/{event_id}/{filename}"
            
            # Upload file
            self.client.storage.from_(self.bucket_name).upload(
                storage_path,
                file_content,
                file_options={"content-type": self._get_content_type(ext)}
            )
            
            # Get public URL
            return self._get_public_url(storage_path)
        except Exception as e:
            print(f"Error uploading event image: {e}")
            return None
    
    def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            storage_path: Full storage path (e.g., users/1/profile_picture/image.png)
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.is_configured():
            return False
            
        try:
            self.client.storage.from_(self.bucket_name).remove([storage_path])
            return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
    
    def _get_public_url(self, storage_path: str) -> str:
        """Construct public URL for a file"""
        return f"{self.url}/storage/v1/object/public/{self.bucket_name}/{storage_path}"
    
    def _get_content_type(self, extension: str) -> str:
        """Get MIME type based on file extension"""
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".pdf": "application/pdf",
            ".gif": "image/gif",
        }
        return content_types.get(extension.lower(), "application/octet-stream")


# Create a singleton instance
storage = SupabaseStorage()
