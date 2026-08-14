import os
import mimetypes
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible

@deconstructible
class DatabaseStorage(Storage):
    """
    Stores all uploaded media files directly in PostgreSQL (BinaryField).
    Persists permanently across Render deploys without external storage dependencies.
    """
    def _open(self, name, mode='rb'):
        from .models import DbFile
        try:
            db_file = DbFile.objects.get(name=name)
            return ContentFile(db_file.data, name=name)
        except Exception:
            raise FileNotFoundError(f"File {name} not found in database.")

    def _save(self, name, content):
        from .models import DbFile
        content.seek(0)
        data = content.read()
        content_type, _ = mimetypes.guess_type(name)
        content_type = content_type or 'application/octet-stream'

        # Generate unique filename if already exists
        base_name, ext = os.path.splitext(name)
        final_name = name
        counter = 1
        while DbFile.objects.filter(name=final_name).exists():
            final_name = f"{base_name}_{counter}{ext}"
            counter += 1

        DbFile.objects.create(
            name=final_name,
            content_type=content_type,
            data=data,
            size=len(data)
        )
        return final_name

    def exists(self, name):
        from .models import DbFile
        try:
            return DbFile.objects.filter(name=name).exists()
        except Exception:
            return False

    def url(self, name):
        return f"/media/{name}"

    def size(self, name):
        from .models import DbFile
        try:
            return DbFile.objects.get(name=name).size
        except Exception:
            return 0

    def delete(self, name):
        from .models import DbFile
        try:
            DbFile.objects.filter(name=name).delete()
        except Exception:
            pass

def sync_local_media_to_db():
    """
    Scans local media directory and saves any files into PostgreSQL DbFile table.
    """
    from django.conf import settings
    from .models import DbFile
    media_root = str(settings.MEDIA_ROOT)
    if not os.path.exists(media_root): return
    for root, _, files in os.walk(media_root):
        for f in files:
            full_p = os.path.join(root, f)
            rel_name = os.path.relpath(full_p, media_root).replace('\\', '/')
            if not DbFile.objects.filter(name=rel_name).exists():
                try:
                    with open(full_p, 'rb') as fp:
                        raw = fp.read()
                        ctype, _ = mimetypes.guess_type(rel_name)
                        DbFile.objects.create(
                            name=rel_name,
                            content_type=ctype or 'application/octet-stream',
                            data=raw,
                            size=len(raw)
                        )
                        print(f"[DB Media Sync]: Saved {rel_name} to PostgreSQL ({len(raw)} bytes)")
                except Exception as ex:
                    print(f"[DB Media Sync Error for {rel_name}]: {ex}")

