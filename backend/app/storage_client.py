"""Google Cloud Storage client for file operations"""

from google.cloud import storage
from google.oauth2 import service_account
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class CloudStorageClient:
    """Client for Google Cloud Storage operations"""
    
    def __init__(self):
        self.client: Optional[storage.Client] = None
        self.bucket_name = settings.gcs_bucket_name
        self._initialized = False
        
    async def connect(self):
        """Initialize Cloud Storage client"""
        if self._initialized and self.client:
            return
            
        try:
            if not self.bucket_name:
                logger.warning("GCS_BUCKET_NAME not set, Cloud Storage will not be available")
                return
                
            credentials_path = settings.gcp_credentials_path
            if credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                self.client = storage.Client(
                    project=settings.gcp_project_id,
                    credentials=credentials
                )
            else:
                self.client = storage.Client(project=settings.gcp_project_id)
            
            # Verify bucket exists
            bucket = self.client.bucket(self.bucket_name)
            if not bucket.exists():
                logger.warning(f"Bucket {self.bucket_name} does not exist. Please create it in GCP Console.")
                return
            
            self._initialized = True
            logger.info(f"✅ Connected to Cloud Storage: {self.bucket_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Cloud Storage: {e}")
            self.client = None
    
    def _is_available(self) -> bool:
        """Check if Cloud Storage is available"""
        return self.client is not None and self._initialized
    
    async def upload_file(
        self, 
        file_data: bytes, 
        file_path: str, 
        content_type: str = "application/octet-stream",
        make_public: bool = False
    ) -> Optional[str]:
        """Upload file to Cloud Storage and return public URL"""
        if not self._is_available():
            logger.warning(f"GCS not available, cannot upload {file_path}")
            return None
            
        try:
            logger.info(f"Uploading to bucket '{self.bucket_name}': {file_path} ({len(file_data)} bytes)")
            bucket = self.client.bucket(self.bucket_name)
            
            # Verify bucket exists
            if not bucket.exists():
                logger.error(f"Bucket '{self.bucket_name}' does not exist!")
                return None
            
            blob = bucket.blob(file_path)
            blob.upload_from_string(file_data, content_type=content_type)
            
            logger.info(f"✅ Successfully uploaded {file_path} to GCS bucket '{self.bucket_name}'")
            
            if make_public:
                blob.make_public()
                url = blob.public_url
                logger.info(f"   Public URL: {url}")
                return url
            else:
                # Return signed URL (valid for 1 hour)
                url = blob.generate_signed_url(expiration=3600)
                logger.info(f"   Signed URL generated (expires in 1 hour)")
                return url
        except Exception as e:
            logger.error(f"❌ Error uploading file {file_path} to bucket '{self.bucket_name}': {e}")
            import traceback
            logger.error(f"Upload error traceback: {traceback.format_exc()}")
            return None
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from Cloud Storage"""
        if not self._is_available():
            return False
            
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(file_path)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    async def get_file_url(self, file_path: str, signed: bool = True) -> Optional[str]:
        """Get URL for a file"""
        if not self._is_available():
            return None
            
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(file_path)
            
            if blob.exists():
                if signed:
                    return blob.generate_signed_url(expiration=3600)
                else:
                    blob.make_public()
                    return blob.public_url
            return None
        except Exception as e:
            logger.error(f"Error getting file URL {file_path}: {e}")
            return None


# Global instance
storage_client = CloudStorageClient()
