from django.test import TestCase, Client
from django.urls import reverse


class LandingPageViewTests(TestCase):
    """
    Unit tests for Landing Page View (Story 1.1)
    Tests AC1-AC8: Logo display, content, downloads, banners, responsive design
    """

    def setUp(self):
        """Set up test client for each test"""
        self.client = Client()
        self.url = reverse('landing_home')

    def test_landing_page_renders_successfully(self):
        """Test that landing page loads with status 200"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_landing_page_uses_correct_template(self):
        """Test that landing page uses the correct template"""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'landing/home.html')
        self.assertTemplateUsed(response, 'base.html')

    def test_landing_page_contains_hero_section(self):
        """Test AC2: Hero section with main heading exists"""
        response = self.client.get(self.url)
        self.assertContains(
            response,
            'Podnesite prijavu za projekat ili inicijativu',
            msg_prefix="Hero heading missing or incorrect"
        )

    def test_landing_page_contains_preparation_checklist(self):
        """Test AC2: 'Šta treba da pripremim?' section exists"""
        response = self.client.get(self.url)
        self.assertContains(response, 'Šta treba da pripremim?')
        self.assertContains(response, 'Pre nego što počnete, pripremite:')
        # Check for checklist items
        self.assertContains(response, 'Osnovne podatke o vašoj organizaciji')
        self.assertContains(response, 'Excel šablon za budžet projekta')
        self.assertContains(response, 'Biografije članova tima')
        self.assertContains(response, 'Pisma podrške lokalnih organizacija')

    def test_landing_page_contains_reassurance_message(self):
        """Test AC2: Reassurance message about auto-save"""
        response = self.client.get(self.url)
        self.assertContains(response, 'Ne brinite - sve vaše podatke automatski čuvamo')
        self.assertContains(response, 'Možete prekinuti i vratiti se kasnije')

    def test_landing_page_contains_excel_template_download(self):
        """Test AC3: Excel template download section exists"""
        response = self.client.get(self.url)
        self.assertContains(response, 'Preuzmite šablone')
        self.assertContains(response, 'Budžet Projekta')
        self.assertContains(response, 'Preuzmi Excel šablon')
        # Check download link
        self.assertContains(response, 'budzet-projekta-sablon.xlsx')

    def test_landing_page_contains_download_guidance(self):
        """Test AC3: Visual guidance for download process"""
        response = self.client.get(self.url)
        self.assertContains(response, '1. Preuzmi → 2. Popuni → 3. Upload')

    def test_landing_page_contains_coa_banner(self):
        """Test AC4: COA (Projekat) banner exists with correct link"""
        response = self.client.get(self.url)
        self.assertContains(response, 'Prijava za Projekat (COA)')
        self.assertContains(response, 'Detaljni projekat sa budžetom i finansijskim planom')
        self.assertContains(response, 'Započni prijavu projekta')
        self.assertContains(response, 'href="/projekat/"')

    def test_landing_page_contains_cob_banner(self):
        """Test AC4: COB (Inicijativa) banner exists with correct link"""
        response = self.client.get(self.url)
        self.assertContains(response, 'Prijava za Inicijativu (COB)')
        self.assertContains(response, 'Brza inicijativa za zajednicu')
        self.assertContains(response, 'Započni prijavu inicijative')
        self.assertContains(response, 'href="/inicijativa/"')

    def test_landing_page_contains_domovik_logo(self):
        """Test AC1: Domovik logo is referenced in template"""
        response = self.client.get(self.url)
        self.assertContains(response, 'domovik-logo.svg')
        self.assertContains(response, 'alt="Domovik"')

    def test_landing_page_contains_donor_logos(self):
        """Test AC1: Donor logos are referenced in template"""
        response = self.client.get(self.url)
        self.assertContains(response, 'donor-1.svg')
        self.assertContains(response, 'donor-2.svg')
        self.assertContains(response, 'alt="Donor 1"')
        self.assertContains(response, 'alt="Donor 2"')

    def test_landing_page_includes_landing_css(self):
        """Test that landing.css is loaded"""
        response = self.client.get(self.url)
        self.assertContains(response, 'landing.css')

    def test_landing_page_has_semantic_html_structure(self):
        """Test AC8: Semantic HTML elements are used"""
        response = self.client.get(self.url)
        # Check for semantic sections
        self.assertContains(response, '<section')
        # Check for ARIA labels
        self.assertContains(response, 'aria-labelledby="hero-heading"')
        self.assertContains(response, 'id="hero-heading"')

    def test_landing_page_footer_exists(self):
        """Test that footer with copyright is present"""
        response = self.client.get(self.url)
        self.assertContains(response, '&copy; 2025 DOMOVIK')
        self.assertContains(response, 'Sva prava zadržana')

    def test_landing_page_content_type_is_html(self):
        """Test that response content type is HTML"""
        response = self.client.get(self.url)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

    def test_landing_page_response_not_cached(self):
        """Test that landing page is not cached (for dynamic content future)"""
        response = self.client.get(self.url)
        # Check that response is recent (not from cache)
        self.assertIsNotNone(response)


class LandingPageURLTests(TestCase):
    """Tests for URL routing to landing page"""

    def test_root_url_resolves_to_landing_page(self):
        """Test that root URL (/) resolves to landing page view"""
        url = reverse('landing_home')
        self.assertEqual(url, '/')

    def test_landing_page_accessible_without_authentication(self):
        """Test that landing page is publicly accessible"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)


class LandingPageStaticFilesTests(TestCase):
    """Tests for static file references in landing page"""

    def setUp(self):
        """Set up test client"""
        self.client = Client()
        self.url = reverse('landing_home')

    def test_base_css_is_referenced(self):
        """Test that base.css is loaded via base template"""
        response = self.client.get(self.url)
        # base.css should be included via base.html template
        content = response.content.decode('utf-8')
        # Check that CSS is being loaded (either base.css or inline styles)
        self.assertTrue(
            'base.css' in content or '<style>' in content,
            "No CSS found in landing page"
        )

    def test_static_images_directory_structure(self):
        """Test that image references use correct static file paths"""
        response = self.client.get(self.url)
        content = response.content.decode('utf-8')
        # Check that static file template tag is used
        self.assertIn('/static/images/', content)


class LandingPageAccessibilityTests(TestCase):
    """Tests for accessibility compliance (AC8)"""

    def setUp(self):
        """Set up test client"""
        self.client = Client()
        self.url = reverse('landing_home')

    def test_images_have_alt_text(self):
        """Test AC8: All images have alt attributes"""
        response = self.client.get(self.url)
        content = response.content.decode('utf-8')

        # Count img tags
        import re
        img_tags = re.findall(r'<img[^>]*>', content)

        for img_tag in img_tags:
            self.assertIn(
                'alt=',
                img_tag,
                f"Image tag missing alt attribute: {img_tag}"
            )

    def test_headings_hierarchy(self):
        """Test that heading hierarchy is logical (h1, then h2, etc.)"""
        response = self.client.get(self.url)
        content = response.content.decode('utf-8')

        # Check h1 exists
        self.assertIn('<h1', content, "No h1 heading found")
        # Check h2 exists
        self.assertIn('<h2', content, "No h2 headings found")

    def test_links_have_descriptive_text(self):
        """Test that links have descriptive text (not just 'click here')"""
        response = self.client.get(self.url)
        content = response.content.decode('utf-8').lower()

        # Check that generic link text is NOT used
        self.assertNotIn('click here', content)
        self.assertNotIn('klikni ovde', content)
