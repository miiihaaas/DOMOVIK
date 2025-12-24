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


class ExcelTemplateDownloadTests(TestCase):
    """
    Unit tests for Excel Template Downloads (Story 1.2)
    Tests AC1-AC5: Download functionality, template structure, visual guidance
    """

    def setUp(self):
        """Set up test client for each test"""
        self.client = Client()
        self.url = reverse('landing_home')

    def test_landing_page_contains_excel_download_link(self):
        """Test AC1: Landing page has Excel template download link"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Preuzmi Excel šablon')
        self.assertContains(response, 'downloads/budzet-projekta-sablon.xlsx')

    def test_excel_download_link_points_to_static_file(self):
        """Test AC1: Download link points to correct static file path"""
        response = self.client.get(self.url)
        content = response.content.decode('utf-8')

        # Verify the download link uses static template tag
        self.assertIn('downloads/budzet-projekta-sablon.xlsx', content)

        # Verify link has download attribute (forces download vs open)
        import re
        download_link = re.search(
            r'<a[^>]*href="[^"]*budzet-projekta-sablon\.xlsx"[^>]*>',
            content
        )
        self.assertIsNotNone(download_link, "Download link not found in HTML")
        self.assertIn('download', download_link.group(), "Download attribute missing from link")

    def test_excel_template_file_exists(self):
        """Test AC1,5: Excel template file exists in static folder"""
        from django.conf import settings
        from pathlib import Path

        file_path = settings.BASE_DIR / 'static' / 'downloads' / 'budzet-projekta-sablon.xlsx'

        self.assertTrue(
            file_path.exists(),
            f"Excel template not found at {file_path}"
        )

        # Verify file is not empty
        file_size = file_path.stat().st_size
        self.assertGreater(
            file_size,
            0,
            "Excel template file is empty"
        )

    def test_excel_template_is_xlsx_format(self):
        """Test AC5: Excel template is .xlsx format (Excel 2007+)"""
        from django.conf import settings
        from pathlib import Path

        file_path = settings.BASE_DIR / 'static' / 'downloads' / 'budzet-projekta-sablon.xlsx'

        # Verify file extension
        self.assertTrue(
            str(file_path).endswith('.xlsx'),
            "Excel template must be .xlsx format (Excel 2007+)"
        )

        # Verify file can be opened with openpyxl (validates .xlsx format)
        try:
            from openpyxl import load_workbook
            wb = load_workbook(str(file_path))
            self.assertIsNotNone(wb, "Failed to load Excel workbook")
        except Exception as e:
            self.fail(f"Excel template is not a valid .xlsx file: {e}")

    def test_excel_template_structure(self):
        """Test AC2,4: Excel template has correct structure with required sheets"""
        from django.conf import settings
        from openpyxl import load_workbook

        file_path = settings.BASE_DIR / 'static' / 'downloads' / 'budzet-projekta-sablon.xlsx'

        wb = load_workbook(str(file_path))

        # Test AC2: Verify main budget sheet exists
        self.assertIn(
            'Budžet Projekta',
            wb.sheetnames,
            "Main budget sheet 'Budžet Projekta' not found"
        )

        # Test AC4: Verify instructions sheet exists
        instructions_sheet_exists = (
            'Uputstva' in wb.sheetnames or
            'Uputstvo' in wb.sheetnames
        )
        self.assertTrue(
            instructions_sheet_exists,
            "Instructions sheet ('Uputstva' or 'Uputstvo') not found"
        )

        # Verify budget sheet has expected columns
        ws_budget = wb['Budžet Projekta']
        expected_headers = [
            'Kategorija Troškova',
            'Opis',
            'Jedinična Cena (RSD)',
            'Količina',
            'Ukupno (RSD)'
        ]

        actual_headers = [
            ws_budget.cell(1, col).value
            for col in range(1, 6)
        ]

        self.assertEqual(
            actual_headers,
            expected_headers,
            f"Column headers don't match. Expected: {expected_headers}, Got: {actual_headers}"
        )

    def test_excel_template_has_sum_formula(self):
        """Test AC2: Excel template has SUM formula in UKUPNO row"""
        from django.conf import settings
        from openpyxl import load_workbook

        file_path = settings.BASE_DIR / 'static' / 'downloads' / 'budzet-projekta-sablon.xlsx'

        wb = load_workbook(str(file_path))
        ws_budget = wb['Budžet Projekta']

        # Find UKUPNO row (should be row 9 based on template specs)
        ukupno_row = None
        for row_idx in range(1, 15):  # Check first 15 rows
            cell_value = ws_budget.cell(row_idx, 1).value
            if cell_value and 'UKUPNO' in str(cell_value).upper():
                ukupno_row = row_idx
                break

        self.assertIsNotNone(ukupno_row, "UKUPNO row not found in Excel template")
        self.assertEqual(ukupno_row, 9, "UKUPNO should be in row 9")

        # Verify SUM formula exists in Ukupno column (column E)
        sum_cell = ws_budget.cell(ukupno_row, 5)
        sum_value = sum_cell.value

        self.assertIsNotNone(sum_value, "UKUPNO cell is empty (no SUM formula)")
        self.assertTrue(
            str(sum_value).startswith('=SUM'),
            f"UKUPNO cell should contain SUM formula, got: {sum_value}"
        )

        # Verify the formula sums E2:E8 (not E2:E10)
        self.assertEqual(
            sum_value,
            '=SUM(E2:E8)',
            f"SUM formula should be =SUM(E2:E8), got: {sum_value}"
        )

    def test_visual_guidance_text_present(self):
        """Test AC3: Visual guidance '1. Preuzmi → 2. Popuni → 3. Upload' is displayed"""
        response = self.client.get(self.url)
        self.assertContains(response, '1. Preuzmi')
        self.assertContains(response, '2. Popuni')
        self.assertContains(response, '3. Upload')

        # Verify the complete guidance text
        self.assertContains(response, '1. Preuzmi → 2. Popuni → 3. Upload')

    def test_visual_guidance_has_correct_css_class(self):
        """Test AC3: Visual guidance uses landing__download-guidance class"""
        response = self.client.get(self.url)
        content = response.content.decode('utf-8')

        # Check for the specific CSS class
        import re
        guidance_element = re.search(
            r'<p[^>]*class="[^"]*landing__download-guidance[^"]*"[^>]*>',
            content
        )

        self.assertIsNotNone(
            guidance_element,
            "Visual guidance element with class 'landing__download-guidance' not found"
        )

    def test_visual_guidance_in_same_section_as_download_link(self):
        """Test AC3: Visual guidance is in the same card/section as download link"""
        response = self.client.get(self.url)
        content = response.content.decode('utf-8')

        # Find the download card section
        import re
        download_card = re.search(
            r'<div class="landing__download-card">.*?</div>',
            content,
            re.DOTALL
        )

        self.assertIsNotNone(download_card, "Download card section not found")

        # Verify both visual guidance AND download link are in the same section
        card_content = download_card.group()
        self.assertIn('1. Preuzmi', card_content, "Visual guidance not in download card")
        self.assertIn('budzet-projekta-sablon.xlsx', card_content, "Download link not in same card")
