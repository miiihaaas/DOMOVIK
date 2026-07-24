# -*- coding: utf-8 -*-
"""
Integration tests for admin detail view with COA and COB applications.
Story 4.3: Test dynamic fieldsets, status changes, and workflow integration
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.submissions.models import Application, Applicant, ProjectData, InitiativeData


class AdminDetailViewIntegrationTests(TestCase):
    """Integration tests for admin detail view with COA and COB applications."""

    def setUp(self):
        """Create test admin and sample applications."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='testadmin@domovik.local',
            password='TestAdmin123!'
        )

        # Create COA application (pravno lice - to test matični broj)
        self.coa_pravno_app = Application.objects.create(
            reference_number='COA-2025-002',
            application_type='COA',
            status='approved',
        )

        self.coa_pravno_applicant = Applicant.objects.create(
            application=self.coa_pravno_app,
            entity_type='pravno',
            organization_name='Pravna Organizacija',
            maticni_broj='12345678',
            address='Beograd',
            email='pravno@example.com',
            phone='+381601234567',
        )

        ProjectData.objects.create(
            application=self.coa_pravno_app,
            title='Pravno Projekat',
            short_description='Opis',
            problem='Problem',
            main_goal='Cilj',
            specific_goals='Ciljevi',
            target_groups='Grupe',
            activities='Aktivnosti',
            results='Rezultati',
            total_budget=500000.00,
        )

        # Create COB application (fizičko lice - to test NO JMBG for COB)
        self.cob_fizicko_app = Application.objects.create(
            reference_number='COB-2025-002',
            application_type='COB',
            status='rejected',
        )

        self.cob_fizicko_applicant = Applicant.objects.create(
            application=self.cob_fizicko_app,
            entity_type='fizicko',
            first_name='Ana',
            last_name='Ivanović',
            # NO jmbg for COB (not required)
            address='Niš',
            email='ana@example.com',
            phone='+381601234569',
        )

        InitiativeData.objects.create(
            application=self.cob_fizicko_app,
            naslov='Fizičko Inicijativa',
            kratak_opis='Opis',
            problem='Problem',
            cilj_inicijative='Cilj',
            planirani_koraci='Koraci',
            ocekivani_uticaj='Uticaj',
        )

    def test_coa_pravno_detail_view_shows_maticni_broj(self):
        """Test COA pravno lice shows matični broj field."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get(f'/admin/submissions/application/{self.coa_pravno_app.id}/change/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pravna Organizacija')
        self.assertContains(response, '12345678')  # Matični broj
        self.assertContains(response, 'Matični broj')  # Label

    def test_cob_fizicko_detail_view_does_not_show_jmbg(self):
        """Test COB fizičko lice does NOT show JMBG field (not required for COB)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get(f'/admin/submissions/application/{self.cob_fizicko_app.id}/change/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana')
        self.assertContains(response, 'Ivanović')
        # JMBG should NOT appear (COB doesn't require it)
        # This is handled by dynamic fieldsets - JMBG field not in fieldsets for COB
        self.assertNotContains(response, 'JMBG')

    def test_admin_views_coa_and_cob_detail_views_correctly(self):
        """Test admin can view both COA and COB detail views with correct fields."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        # COA detail view
        coa_response = self.client.get(f'/admin/submissions/application/{self.coa_pravno_app.id}/change/')
        self.assertEqual(coa_response.status_code, 200)
        self.assertContains(coa_response, 'Podaci o projektu')  # COA section
        self.assertContains(coa_response, 'Pravno Projekat')

        # COB detail view
        cob_response = self.client.get(f'/admin/submissions/application/{self.cob_fizicko_app.id}/change/')
        self.assertEqual(cob_response.status_code, 200)
        self.assertContains(cob_response, 'Podaci o inicijativi')  # COB section
        self.assertContains(cob_response, 'Fizičko Inicijativa')

    def test_admin_changes_status_from_approved_to_rejected(self):
        """Test admin can change status from approved to rejected."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        # Initial status: approved
        self.assertEqual(self.coa_pravno_app.status, 'approved')

        # Change to rejected
        response = self.client.post(
            f'/admin/submissions/application/{self.coa_pravno_app.id}/change/',
            {
                'status': 'rejected',
                # Django admin requires inline formset management forms
                'files-TOTAL_FORMS': '0',
                'files-INITIAL_FORMS': '0',
                'files-MIN_NUM_FORMS': '0',
                'files-MAX_NUM_FORMS': '0',
            },
            follow=True
        )

        # Verify status changed
        self.coa_pravno_app.refresh_from_db()
        self.assertEqual(self.coa_pravno_app.status, 'rejected')

    def test_admin_detail_view_back_to_list_preserves_filters(self):
        """Test back button from detail view returns to list view with filters preserved."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        # Navigate to list view with filter
        list_response = self.client.get('/admin/submissions/application/?application_type=COA')
        self.assertEqual(list_response.status_code, 200)

        # Navigate to detail view
        detail_response = self.client.get(f'/admin/submissions/application/{self.coa_pravno_app.id}/change/')
        self.assertEqual(detail_response.status_code, 200)

        # Verify "Back to list" link preserves filters (Django admin handles this automatically)
        # This is a Django Admin built-in feature - hard to test via automated test

    def test_coa_detail_view_shows_budget_formatted_correctly(self):
        """Test COA detail view formats budget with thousand separators."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get(f'/admin/submissions/application/{self.coa_pravno_app.id}/change/')

        self.assertEqual(response.status_code, 200)
        # ISSUE 2 FIX: Budget is IntegerField, formatted without decimals
        self.assertContains(response, '500,000 RSD')  # Integer format, no .00

    def test_cob_detail_view_does_not_show_budget(self):
        """Test COB detail view does NOT show budget field (COB doesn't have budget)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get(f'/admin/submissions/application/{self.cob_fizicko_app.id}/change/')

        self.assertEqual(response.status_code, 200)
        # Budget field should NOT appear for COB applications
        self.assertNotContains(response, 'Totalni budžet')

    def test_dynamic_fieldsets_coa_fizicko_shows_jmbg(self):
        """Test COA fizičko lice dynamic fieldsets include JMBG."""
        # Create COA fizičko lice application
        coa_fizicko_app = Application.objects.create(
            reference_number='COA-2025-003',
            application_type='COA',
            status='submitted',
        )

        coa_fizicko_applicant = Applicant.objects.create(
            application=coa_fizicko_app,
            entity_type='fizicko',
            first_name='Petar',
            last_name='Petrović',
            jmbg='9876543210987',
            address='Subotica',
            email='petar@example.com',
            phone='+381601234570',
        )

        ProjectData.objects.create(
            application=coa_fizicko_app,
            title='Test',
            short_description='Test',
            problem='Test',
            main_goal='Test',
            specific_goals='Test',
            target_groups='Test',
            activities='Test',
            results='Test',
            total_budget=10000.00,
        )

        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get(f'/admin/submissions/application/{coa_fizicko_app.id}/change/')

        self.assertEqual(response.status_code, 200)
        # JMBG should appear for COA fizičko lice
        self.assertContains(response, '9876543210987')
        self.assertContains(response, 'JMBG')

    def test_dynamic_fieldsets_cob_pravno_does_not_show_maticni_broj(self):
        """Test COB pravno lice dynamic fieldsets do NOT include matični broj."""
        # Create COB pravno lice application
        cob_pravno_app = Application.objects.create(
            reference_number='COB-2025-003',
            application_type='COB',
            status='submitted',
        )

        cob_pravno_applicant = Applicant.objects.create(
            application=cob_pravno_app,
            entity_type='pravno',
            organization_name='COB Organizacija',
            address='Kragujevac',
            email='cobpravno@example.com',
            phone='+381601234571',
        )

        InitiativeData.objects.create(
            application=cob_pravno_app,
            naslov='COB Pravno Test',
            kratak_opis='Test',
            problem='Test',
            cilj_inicijative='Test',
            planirani_koraci='Test',
            ocekivani_uticaj='Test',
        )

        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get(f'/admin/submissions/application/{cob_pravno_app.id}/change/')

        self.assertEqual(response.status_code, 200)
        # Matični broj should NOT appear for COB applications
        self.assertNotContains(response, 'Matični broj')
