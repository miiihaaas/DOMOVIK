# -*- coding: utf-8 -*-
"""
Story 4.2: Admin List View Integration Tests
Integration tests for admin list view with real data from Epic 2-3.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.submissions.models import Application, Applicant, ProjectData, InitiativeData


class AdminListViewIntegrationTests(TestCase):
    """Integration tests for admin list view with real data from Epic 2-3."""

    def setUp(self):
        """Create test admin and sample COA + COB applications."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='testadmin@domovik.local',
            password='TestAdmin123!'
        )

        # Create COA application (from Epic 2)
        self.coa_app = Application.objects.create(
            reference_number='COA-2025-001',
            application_type='COA',
            status='submitted',
        )

        coa_applicant = Applicant.objects.create(
            application=self.coa_app,
            entity_type='fizicko',
            first_name='Marko',
            last_name='Petrović',
            jmbg='1234567890123',
            address='Beograd, Srbija',
            email='marko@example.com',
            phone='+381601234567',
        )

        self.coa_app.applicant = coa_applicant
        self.coa_app.save()

        ProjectData.objects.create(
            application=self.coa_app,
            title='Test Projekat',
            short_description='Opis projekta',
            problem='Problem',
            main_goal='Cilj',
            specific_goals='Specifični ciljevi',
            target_groups='Ciljne grupe',
            activities='Aktivnosti',
            results='Rezultati',
            total_budget=100000,
        )

        # Create COB application (from Epic 3)
        self.cob_app = Application.objects.create(
            reference_number='COB-2025-001',
            application_type='COB',
            status='under_review',
        )

        cob_applicant = Applicant.objects.create(
            application=self.cob_app,
            entity_type='pravno',
            organization_name='Test Organizacija',
            address='Novi Sad, Srbija',
            email='org@example.com',
            phone='+381601234568',
        )

        self.cob_app.applicant = cob_applicant
        self.cob_app.save()

        InitiativeData.objects.create(
            application=self.cob_app,
            naslov='Test Inicijativa',
            kratak_opis='Opis inicijative',
            problem='Problem',
            cilj_inicijative='Cilj',
            planirani_koraci='Koraci',
            ocekivani_uticaj='Uticaj',
        )

    def test_admin_views_both_coa_and_cob_in_list(self):
        """Test admin sees both COA and COB applications in single list."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # COA application
        self.assertContains(response, 'COA-2025-001')
        self.assertContains(response, 'Marko Petrović')
        self.assertContains(response, 'Test Projekat')
        # COB application
        self.assertContains(response, 'COB-2025-001')
        self.assertContains(response, 'Test Organizacija')
        self.assertContains(response, 'Test Inicijativa')

    def test_admin_filters_coa_only(self):
        """Test filtering to show only COA applications."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/?application_type=COA')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COA-2025-001')

    def test_admin_filters_cob_only(self):
        """Test filtering to show only COB applications."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/?application_type=COB')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COB-2025-001')

    def test_admin_searches_across_coa_and_cob(self):
        """Test search works for both COA and COB applications."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        # Search by COA applicant
        response = self.client.get('/admin/submissions/application/?q=Marko')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COA-2025-001')

        # Search by COB organization
        response = self.client.get('/admin/submissions/application/?q=Test Organizacija')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COB-2025-001')

    def test_admin_clicks_on_application_row_to_view_details(self):
        """Test clicking on application row navigates to detail view."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Verify link to COA detail exists
        self.assertContains(response, f'/admin/submissions/application/{self.coa_app.id}/change/')
        # Verify link to COB detail exists
        self.assertContains(response, f'/admin/submissions/application/{self.cob_app.id}/change/')

    def test_concurrent_admin_access(self):
        """Test multiple admins can access list view simultaneously (NFR7)."""
        # Create 5 admin users
        admin_clients = []
        for i in range(5):
            admin = User.objects.create_superuser(
                username=f'admin{i}',
                email=f'admin{i}@domovik.local',
                password='TestAdmin123!'
            )
            client = Client()
            client.login(username=f'admin{i}', password='TestAdmin123!')
            admin_clients.append(client)

        # All 5 admins access list view simultaneously
        responses = []
        for client in admin_clients:
            response = client.get('/admin/submissions/application/')
            responses.append(response)

        # Verify all requests succeed
        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'COA-2025-001')
            self.assertContains(response, 'COB-2025-001')

    def test_admin_list_shows_applicant_entity_icons(self):
        """Test applicant names show entity type icons (👤 fizičko, 🏢 pravno)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Fizičko lice icon for COA
        self.assertContains(response, '👤')
        # Pravno lice icon for COB
        self.assertContains(response, '🏢')

    def test_admin_list_shows_application_type_icons(self):
        """Test application types show icons (📋 Projekat, 💡 Inicijativa)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Projekat icon for COA
        self.assertContains(response, '📋')
        # Inicijativa icon for COB
        self.assertContains(response, '💡')
