import base64
import uuid
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.uploader import upload
from django.conf import settings
from django.core.files.base import ContentFile


class CloudinaryFileUpload:
    def __init__(self):
        self.cloud_name = settings.CLOUD_NAME
        self.api_key = settings.API_KEY
        self.api_secret = settings.API_SECRET
        
    def __set_up(self):
        cloudinary.config( 
            cloud_name = self.cloud_name, 
            api_key = self.api_key, 
            api_secret = self.api_secret,
            secure=True
        )
        
    def upload_file_to_cloudinary_v1(self, file, file_name)->str:
        self.__set_up()
        result = upload(file, resource_type="auto", 
                        type="upload", public_id=file_name, 
                        overwrite=True,
                        use_filename=True,
                        folder="profile_pictures",
                        unique_filename=False)
        return result["secure_url"]
    
    def upload_file_to_cloudinary(self, file, filename="upload.zip"):
        """
        Uploads a file or BytesIO stream to Cloudinary and returns the secure URL.
        """
        self.__set_up()
        try:
            result = cloudinary.uploader.upload(
                file,
                resource_type="raw",  # use 'raw' for non-image/video files like zip
                public_id=filename,
                overwrite=True,
                use_filename=True,
                unique_filename=False
            )
            return result["secure_url"]
        except Exception as e:
            raise Exception(f"Cloudinary upload failed: {e}")
