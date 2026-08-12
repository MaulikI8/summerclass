import os

def delete_old_file_on_update(instance, model, field):
    if not instance.pk: return
    try:
        old = getattr(model.objects.get(pk=instance.pk), field)
        new = getattr(instance, field)
        if old and old != new and os.path.isfile(old.path): os.remove(old.path)
    except Exception: pass

def delete_file_on_delete(instance, field):
    f = getattr(instance, field, None)
    if f:
        try:
            if os.path.isfile(f.path): os.remove(f.path)
        except Exception: pass
