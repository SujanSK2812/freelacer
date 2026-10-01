import os
import uuid
import re
from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db.models.fields.files import ImageFieldFile
from django.db import models
from django.conf import settings
from PIL import Image

# Maximum upload size: 5 MB
MAX_UPLOAD_SIZE = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.avif'}
ALLOWED_MIME_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/avif',
}

# Dedicated FileSystemStorage relative to project BASE_DIR
# This ensures that relative path 'uploads/...' is stored in DB
# and resolved from BASE_DIR / 'uploads/...', with url starting with '/'
portal_upload_storage = FileSystemStorage(
    location=str(settings.BASE_DIR),
    base_url='/'
)


def secure_unique_filename(original_filename):
    """
    Generate a secure, collision-free filename preserving the original extension.
    Example output: 8f3a2c1d_backend-development.jpg
    """
    base_name = os.path.basename(original_filename)
    stem, ext = os.path.splitext(base_name)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = '.jpg'

    # Sanitize stem: allow alphanumeric, dashes, and underscores
    sanitized_stem = re.sub(r'[^a-zA-Z0-9_\-]', '_', stem).strip('_')
    if not sanitized_stem:
        sanitized_stem = "upload"
    # Truncate overly long stems
    sanitized_stem = sanitized_stem[:50]

    unique_prefix = uuid.uuid4().hex[:8]
    return f"{unique_prefix}_{sanitized_stem}{ext}"


def client_profile_path(instance, filename):
    return f"uploads/clients/profile/{secure_unique_filename(filename)}"


def client_banner_path(instance, filename):
    return f"uploads/clients/banner/{secure_unique_filename(filename)}"


def client_job_path(instance, filename):
    return f"uploads/clients/jobs/{secure_unique_filename(filename)}"


def client_poster_path(instance, filename):
    return f"uploads/clients/posters/{secure_unique_filename(filename)}"


def freelancer_profile_path(instance, filename):
    return f"uploads/freelancers/profile/{secure_unique_filename(filename)}"


def freelancer_banner_path(instance, filename):
    return f"uploads/freelancers/banner/{secure_unique_filename(filename)}"


def freelancer_talent_path(instance, filename):
    return f"uploads/freelancers/talents/{secure_unique_filename(filename)}"


def freelancer_poster_path(instance, filename):
    return f"uploads/freelancers/posters/{secure_unique_filename(filename)}"


def validate_uploaded_image(file_obj):
    """
    Validate uploaded image for size, extension, MIME type, and Pillow integrity.
    """
    if not file_obj:
        return

    # 1. Size check
    if hasattr(file_obj, 'size') and file_obj.size > MAX_UPLOAD_SIZE:
        raise ValidationError("Image file size exceeds the 5MB limit.")

    # 2. Extension check
    filename = getattr(file_obj, 'name', '')
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file extension '{ext}'. Allowed extensions: JPG, JPEG, PNG, WEBP, AVIF."
        )

    # 3. MIME type check if available
    content_type = getattr(file_obj, 'content_type', '')
    if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Invalid image content type '{content_type}'. Allowed types: JPEG, PNG, WEBP, AVIF."
        )

    # 4. Pillow image integrity verification
    try:
        current_pos = file_obj.tell() if hasattr(file_obj, 'tell') else None
    except Exception:
        current_pos = None

    try:
        img = Image.open(file_obj)
        img.verify()
    except Exception as e:
        raise ValidationError(f"Invalid or corrupted image file: {str(e)}")
    finally:
        if current_pos is not None and hasattr(file_obj, 'seek'):
            file_obj.seek(current_pos)


def safe_delete_unreferenced_file(file_path):
    """
    Deletes the physical file only if:
    1. It is safely inside the project's uploads/ or media/ directory.
    2. No other record across ClientProfile, FreelancerProfile, Job, or JobPost references it.
    """
    if not file_path:
        return False

    # Extract clean relative string if a FieldFile is passed
    if hasattr(file_path, 'name'):
        raw_path = file_path.name
    else:
        raw_path = str(file_path).strip()

    if not raw_path or raw_path.startswith(('http://', 'https://')):
        return False

    # Normalize relative path (remove leading slashes)
    rel_path = raw_path.lstrip('/')
    abs_base = Path(settings.BASE_DIR).resolve()
    target_abs = (abs_base / rel_path).resolve()

    # Security check: must reside inside BASE_DIR / 'uploads' or BASE_DIR / 'media'
    allowed_roots = [
        (abs_base / 'uploads').resolve(),
        (abs_base / 'media').resolve(),
    ]
    is_safe = any(
        str(target_abs).startswith(str(root)) and target_abs != root
        for root in allowed_roots
    )
    if not is_safe:
        return False

    # Check if target file actually exists
    if not target_abs.is_file():
        return False

    # Check for active database references across models
    from client.models import ClientProfile
    from freelancer.models import FreelancerProfile
    from projects.models import Job, JobPost

    # Variations to query (both raw_path and rel_path)
    lookup_values = list({raw_path, rel_path})

    if ClientProfile.objects.filter(profile_picture__in=lookup_values).exists():
        return False

    if hasattr(ClientProfile, 'banner_image') and ClientProfile.objects.filter(banner_image__in=lookup_values).exists():
        return False

    if FreelancerProfile.objects.filter(profile_picture__in=lookup_values).exists():
        return False

    if hasattr(FreelancerProfile, 'banner_image') and FreelancerProfile.objects.filter(banner_image__in=lookup_values).exists():
        return False

    if Job.objects.filter(image__in=lookup_values).exists():
        return False
    if hasattr(Job, 'poster') and Job.objects.filter(poster__in=lookup_values).exists():
        return False

    if JobPost.objects.filter(image__in=lookup_values).exists():
        return False
    if hasattr(JobPost, 'poster') and JobPost.objects.filter(poster__in=lookup_values).exists():
        return False

    # No references found, safe to delete physical file
    try:
        target_abs.unlink()
        return True
    except OSError:
        return False


class SafeImageFieldFile(ImageFieldFile):
    """
    FieldFile subclass that:
    1. Evaluates to True for newly uploaded in-memory files (_committed=False) so Django saves them.
    2. For saved files, returns False if the physical file does not exist on disk
       (preventing broken image tags from rendering in templates).
    3. Gracefully returns empty string or valid URL without raising ValueError.
    4. Preserves self.name on str() conversion so Django properly saves relative path to DB.
    """
    def __bool__(self):
        if not self.name:
            return False
        # If the file is newly attached in-memory and not yet committed, return True so Django commits it
        if hasattr(self, '_file') and self._file is not None and not getattr(self, '_committed', True):
            return True
        name_str = str(self.name).strip()
        if not name_str:
            return False
        if name_str.startswith(('http://', 'https://')):
            return True
        try:
            rel_path = name_str.lstrip('/')
            abs_path = os.path.join(settings.BASE_DIR, rel_path)
            if os.path.isfile(abs_path):
                return True
            media_path = os.path.join(settings.MEDIA_ROOT, rel_path)
            if os.path.isfile(media_path):
                return True
            return False
        except Exception:
            return False

    @property
    def url(self):
        if not self.name:
            return ""
        name_str = str(self.name).strip()
        if name_str.startswith(('http://', 'https://')):
            return name_str
        try:
            rel_path = name_str.lstrip('/')
            abs_path = os.path.join(settings.BASE_DIR, rel_path)
            if os.path.isfile(abs_path):
                if rel_path.startswith(('uploads/', 'media/')):
                    return f"/{rel_path}"
                return self.storage.url(name_str)
            media_path = os.path.join(settings.MEDIA_ROOT, rel_path)
            if os.path.isfile(media_path):
                return f"/media/{rel_path}"
            return ""
        except Exception:
            return ""

    def __str__(self):
        return str(self.name or "")


class SafeImageField(models.ImageField):
    attr_class = SafeImageFieldFile

    def __init__(self, *args, **kwargs):
        # Default storage to portal_upload_storage if not specified
        kwargs.setdefault('storage', portal_upload_storage)
        super().__init__(*args, **kwargs)
