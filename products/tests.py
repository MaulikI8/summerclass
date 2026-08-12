import os
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from .models import Category, Product

@override_settings(MEDIA_ROOT=os.path.join(settings.BASE_DIR, 'test_media'))
class ProductImageCleanupTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Electronics")
        self.media_root = settings.MEDIA_ROOT
        if not os.path.exists(self.media_root):
            os.makedirs(self.media_root)

    def tearDown(self):
        import shutil
        if os.path.exists(self.media_root):
            shutil.rmtree(self.media_root)

    def test_image_cleanup_on_update_and_delete(self):
        file1 = SimpleUploadedFile("product1.jpg", b"file1_content", content_type="image/jpeg")
        product = Product.objects.create(
            name="Test Product",
            price=99.9,
            description="Test Description",
            category=self.category,
            product_image=file1
        )
        
        path1 = product.product_image.path
        self.assertTrue(os.path.exists(path1))

        file2 = SimpleUploadedFile("product2.jpg", b"file2_content", content_type="image/jpeg")
        product.product_image = file2
        product.save()

        path2 = product.product_image.path

        self.assertFalse(os.path.exists(path1))
        self.assertTrue(os.path.exists(path2))

        product.delete()

        self.assertFalse(os.path.exists(path2))
