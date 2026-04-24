from django.test import TestCase


class LandingContentTest(TestCase):
    def test_landing_endpoint(self):
        response = self.client.get('/api/content/landing/')
        data = response.json()

        self.assertEqual(response.status_code, 200)

        self.assertIn('hero', data)
        self.assertIn('for_whom', data)
        self.assertIn('why_worth', data)
        self.assertIn('footer_links', data)
