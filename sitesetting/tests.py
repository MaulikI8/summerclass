from django.test import TestCase, RequestFactory
from .models import SiteSetting
from .context_processors import site_settings

class SiteSettingContextProcessorTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_context_processor_with_no_settings(self):
        request = self.factory.get('/')
        context = site_settings(request)
        self.assertIn('site_setting', context)
        self.assertIsNone(context['site_setting'])

    def test_context_processor_with_settings(self):
        setting = SiteSetting.objects.create(
            site_title="Test Title",
            meta_description="Test Description",
            meta_keywords="test,keywords",
            copyright="© 2026 Test Inc."
        )
        request = self.factory.get('/')
        context = site_settings(request)
        self.assertIn('site_setting', context)
        self.assertEqual(context['site_setting'], setting)
        self.assertEqual(context['site_setting'].site_title, "Test Title")
