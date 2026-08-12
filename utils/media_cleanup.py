import os

def delete_old_file_on_update(instance, model, field_name):
    """Delete the old file from disk when updating the field."""
    if not instance.pk:
        return
    try:
        old_instance = model.objects.get(pk=instance.pk)
    except model.DoesNotExist:
        return
    old_file = getattr(old_instance, field_name)
    new_file = getattr(instance, field_name)
    if old_file and old_file != new_file:
        try:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)
        except (ValueError, OSError):
            pass

def delete_file_on_delete(instance, field_name):
    """Delete the file from disk when the instance is deleted."""
    file_field = getattr(instance, field_name)
    if file_field:
        try:
            if os.path.isfile(file_field.path):
                os.remove(file_field.path)
        except (ValueError, OSError):
            pass
