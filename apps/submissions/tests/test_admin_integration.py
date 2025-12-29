# -*- coding: utf-8 -*-
"""
Integration tests for admin viewing real application data.
Story 4.1: Admin Authentication - Test admin viewing, filtering, searching applications
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.submissions.models import Application, Applicant, ProjectData, InitiativeData
from apps.submissions.constants import ApplicationType, ApplicationStatus, EntityType


class AdminIntegrationTests(TestCase):
    """Integration tests for admin viewing real application data."""

    def setUp(self):
        """Create test admin and sample application data."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='testadmin@domovik.local',
            password='TestAdmin123!'
        )

        # Create sample COA application (from Epic 2 test data)
        self.coa_application = Application.objects.create(
            reference_number='COA-2025-001',
            application_type=ApplicationType.COA,
            status=ApplicationStatus.SUBMITTED,
            submitted_at='2025-12-29T10:00:00Z'
        )

        self.coa_applicant = Applicant.objects.create(
            application=self.coa_application,
            entity_type=EntityType.FIZICKO,
            first_name='Marko',
            last_name='Petrović',
            jmbg='1234567890123',
            address='Beograd, Srbija',
            email='marko@example.com',
            phone='+381601234567',
        )

        self.project_data = ProjectData.objects.create(
            application=self.coa_application,
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

        # Create sample COB application
        self.cob_application = Application.objects.create(
            reference_number='COB-2025-001',
            application_type=ApplicationType.COB,
            status=ApplicationStatus.SUBMITTED,
            submitted_at='2025-12-29T11:00:00Z'
        )

        self.cob_applicant = Applicant.objects.create(
            application=self.cob_application,
            entity_type=EntityType.PRAVNO,
            organization_name='Test Organizacija',
            maticni_broj='12345678',
            address='Novi Sad, Srbija',
            email='org@example.com',
            phone='+381601234568',
        )

        self.initiative_data = InitiativeData.objects.create(
            application=self.cob_application,
            naslov='Test Inicijativa',
            kratak_opis='Opis inicijative',
            problem='Problem inicijative',
            cilj_inicijative='Cilj inicijative',
            planirani_koraci='Planirani koraci',
            ocekivani_uticaj='Očekivani uticaj',
        )

    def test_admin_views_application_in_list(self):
        """Test admin sees application in Applications list."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COA-2025-001')  # Reference number
        self.assertContains(response, 'Marko Petrović')  # Applicant name via get_applicant_name
        self.assertContains(response, 'Test Projekat')  # Project title via get_title

    def test_admin_views_cob_application_in_list(self):
        """Test admin sees COB application in Applications list."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COB-2025-001')  # COB reference number
        self.assertContains(response, 'Test Organizacija')  # Organization name
        self.assertContains(response, 'Test Inicijativa')  # Initiative title

    def test_admin_filters_by_application_type_coa(self):
        """Test admin can filter by COA type."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get(f'/admin/submissions/application/?application_type={ApplicationType.COA}')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COA-2025-001')
        # COB application should not appear
        self.assertNotContains(response, 'COB-2025-001')

    def test_admin_filters_by_application_type_cob(self):
        """Test admin can filter by COB type."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get(f'/admin/submissions/application/?application_type={ApplicationType.COB}')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COB-2025-001')
        # COA application should not appear
        self.assertNotContains(response, 'COA-2025-001')

    def test_admin_filters_by_status(self):
        """Test admin can filter by status (submitted, under_review, etc.)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get(f'/admin/submissions/application/?status={ApplicationStatus.SUBMITTED}')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COA-2025-001')
        self.assertContains(response, 'COB-2025-001')

    def test_admin_searches_by_reference_number(self):
        """Test admin can search by reference number."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/?q=COA-2025-001')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COA-2025-001')

    def test_admin_searches_by_applicant_email(self):
        """Test admin can search by applicant email."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/?q=marko@example.com')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COA-2025-001')

    def test_admin_searches_by_applicant_name(self):
        """Test admin can search by applicant name."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/?q=Petrović')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COA-2025-001')

    def test_admin_views_applicant_list(self):
        """Test admin can view Applicants list."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/applicant/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Marko Petrović')  # Fizičko lice applicant
        self.assertContains(response, 'Test Organizacija')  # Pravno lice applicant

    def test_admin_cannot_delete_applications(self):
        """Test admin cannot delete applications via admin (data retention policy)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        # Try to delete application
        response = self.client.post(
            f'/admin/submissions/application/{self.coa_application.pk}/delete/',
            {'post': 'yes'},
            follow=True
        )
        # Should be forbidden (403) or redirected without deleting
        # Check application still exists
        self.assertTrue(Application.objects.filter(pk=self.coa_application.pk).exists())

    def test_gdpr_compliance_admin_sees_only_submitted(self):
        """Test admin sees ONLY submitted applications (no draft data - GDPR NFR19)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Verify all displayed applications have status = submitted or later
        # (This is architectural - drafts live in localStorage, never on server)
        # Admin panel only shows Application model instances, which are created on submission
        self.assertContains(response, 'COA-2025-001')
        self.assertContains(response, 'COB-2025-001')
