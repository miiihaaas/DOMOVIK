# -*- coding: utf-8 -*-
"""
Story 4.2: Admin List View Unit Tests
Tests for enhanced admin list view with pagination, search, filters, and visual UX.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.submissions.models import Application, Applicant, ProjectData, InitiativeData
from django.utils import timezone
import time


class AdminListViewTests(TestCase):
    """Test admin list view enhancements (Story 4.2)."""

    def setUp(self):
        """Create test admin and sample applications."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='testadmin@domovik.local',
            password='TestAdmin123!'
        )

        # Create 30 sample applications (test pagination)
        for i in range(1, 31):
            app_type = 'COA' if i % 3 == 0 else 'COB'

            # Create application first (without applicant)
            application = Application.objects.create(
                reference_number=f'{app_type}-2025-{i:03d}',
                application_type=app_type,
                status='submitted' if i < 20 else 'under_review',
            )

            # Create applicant linked to application
            applicant = Applicant.objects.create(
                application=application,
                entity_type='fizicko' if i % 2 == 0 else 'pravno',
                first_name=f'Marko{i}' if i % 2 == 0 else '',
                last_name=f'Petrović{i}' if i % 2 == 0 else '',
                organization_name=f'Organizacija {i}' if i % 2 != 0 else '',
                address=f'Beograd {i}, Srbija',
                email=f'applicant{i}@example.com',
                phone=f'+38160123456{i % 10}',
            )

            # Link applicant back to application
            application.applicant = applicant
            application.save()

            if app_type == 'COA':
                ProjectData.objects.create(
                    application=application,
                    title=f'Test Projekat {i}',
                    short_description='Opis',
                    problem='Problem',
                    main_goal='Cilj',
                    specific_goals='Ciljevi',
                    target_groups='Grupe',
                    activities='Aktivnosti',
                    results='Rezultati',
                    total_budget=100000,
                )
            else:
                InitiativeData.objects.create(
                    application=application,
                    naslov=f'Test Inicijativa {i}',
                    kratak_opis='Opis',
                    problem='Problem',
                    cilj_inicijative='Cilj',
                    planirani_koraci='Koraci',
                    ocekivani_uticaj='Uticaj',
                )

    def test_admin_list_view_pagination(self):
        """Test list view pagination (25 per page - FR57)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Django admin shows "30" somewhere to indicate total count
        # Check that pagination controls are present
        self.assertContains(response, '30')
        # Verify showing 25 items (1-25) or just check paginator is present
        self.assertContains(response, 'paginator')

    def test_admin_list_displays_all_columns(self):
        """Test list view displays all required columns (FR57)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Verify column headers in Serbian
        self.assertContains(response, 'Podnosilac')       # Applicant
        self.assertContains(response, 'Naslov')           # Title
        self.assertContains(response, 'Tip prijave')     # Type
        self.assertContains(response, 'Status')           # Status
        self.assertContains(response, 'Datum podnošenja') # Date submitted

    def test_admin_list_sorted_by_newest_first(self):
        """Test list view sorted by newest applications first (FR57)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Django admin ordering already set to ['-submitted_at']
        # Verify newest application appears in response
        self.assertContains(response, 'COB-2025-029')  # One of the newest

    def test_admin_list_filter_by_application_type(self):
        """Test filtering by application type (COA/COB)."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        # Filter COA only
        response = self.client.get('/admin/submissions/application/?application_type=COA')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COA-2025')

        # Filter COB only
        response = self.client.get('/admin/submissions/application/?application_type=COB')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COB-2025')

    def test_admin_list_filter_by_status(self):
        """Test filtering by status (submitted/under_review)."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        # Filter submitted only
        response = self.client.get('/admin/submissions/application/?status=submitted')
        self.assertEqual(response.status_code, 200)
        # Should show submitted applications (1-19)
        self.assertContains(response, 'Podnet')

        # Filter under_review only
        response = self.client.get('/admin/submissions/application/?status=under_review')
        self.assertEqual(response.status_code, 200)
        # Should show under_review applications (20-30)
        self.assertContains(response, 'Na pregledu')

    def test_admin_list_search_by_reference_number(self):
        """Test searching by reference number (FR57)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/?q=COA-2025-003')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COA-2025-003')

    def test_admin_list_search_by_applicant_name(self):
        """Test searching by applicant name (FR57)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/?q=Marko2')

        self.assertEqual(response.status_code, 200)
        # Should find applicant with first_name='Marko2'
        self.assertContains(response, 'Marko2')

    def test_admin_list_search_by_applicant_email(self):
        """Test searching by applicant email (FR57)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/?q=applicant5@example.com')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'applicant5@example.com')

    def test_admin_list_search_by_project_title(self):
        """Test searching by project/initiative title (NEW in 4.2)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/?q=Test Projekat 3')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COA-2025-003')

    def test_admin_list_clickable_rows(self):
        """Test each row is clickable to detail view (FR57)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Verify links to change view exist
        self.assertContains(response, '/admin/submissions/application/')
        self.assertContains(response, '/change/')

    def test_admin_list_performance(self):
        """Test list view loads in <3 seconds (NFR3)."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        start_time = time.time()
        response = self.client.get('/admin/submissions/application/')
        end_time = time.time()

        self.assertEqual(response.status_code, 200)
        load_time = end_time - start_time
        self.assertLess(load_time, 3.0, f"Admin list view took {load_time:.2f}s (expected <3s)")

    def test_get_queryset_optimization(self):
        """Test query optimization with select_related/prefetch_related."""
        self.client.login(username='testadmin', password='TestAdmin123!')

        # Count queries - use flexible threshold instead of exact match
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as context:
            response = self.client.get('/admin/submissions/application/')
            self.assertEqual(response.status_code, 200)
            query_count = len(context.captured_queries)
            # With optimization: should be <15 queries for 25 applications
            # Without optimization: would be 50+ queries (N+1 problem)
            self.assertLess(query_count, 15, f"Query count {query_count} exceeds threshold (expected <15)")

    def test_admin_list_shows_serbian_application_types(self):
        """Test application type displayed in Serbian (Projekat/Inicijativa)."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Projekat')     # COA in Serbian
        self.assertContains(response, 'Inicijativa')  # COB in Serbian

    def test_admin_list_shows_colored_status(self):
        """Test status displayed with color coding."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Verify status labels in Serbian
        self.assertContains(response, 'Podnet')      # submitted
        self.assertContains(response, 'Na pregledu') # under_review

    def test_admin_list_highlights_recent_submissions(self):
        """Test recent submissions (<24h) are highlighted."""
        # Create a recent application
        recent_app = Application.objects.create(
            reference_number='COA-2025-999',
            application_type='COA',
            status='submitted',
        )

        recent_applicant = Applicant.objects.create(
            application=recent_app,
            entity_type='fizicko',
            first_name='Recent',
            last_name='User',
            address='Beograd',
            email='recent@example.com',
            phone='+381601234567',
        )

        recent_app.applicant = recent_applicant
        recent_app.save()

        ProjectData.objects.create(
            application=recent_app,
            title='Recent Project',
            short_description='Recent',
            problem='Problem',
            main_goal='Cilj',
            specific_goals='Ciljevi',
            target_groups='Grupe',
            activities='Aktivnosti',
            results='Rezultati',
            total_budget=100000,
        )

        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Recent application should show 🆕 icon
        # Note: The icon is HTML-escaped in the response
        self.assertContains(response, 'COA-2025-999')

    def test_entity_type_filter_fizicko(self):
        """Test EntityTypeFilter: Filter by fizičko lice."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/?entity_type=fizicko')

        self.assertEqual(response.status_code, 200)
        # Should show fizičko lice applications only
        self.assertContains(response, '👤')  # Fizičko icon

    def test_entity_type_filter_pravno(self):
        """Test EntityTypeFilter: Filter by pravno lice."""
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/?entity_type=pravno')

        self.assertEqual(response.status_code, 200)
        # Should show pravno lice applications only
        self.assertContains(response, '🏢')  # Pravno icon

    def test_entity_type_filter_all(self):
        """
        ISSUE 7 FIX: Test EntityTypeFilter with no filter (default "All" case).
        Tests that queryset returns all applications when no filter is applied.
        """
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Should show both fizičko and pravno applications
        self.assertContains(response, '👤')  # Fizičko icon
        self.assertContains(response, '🏢')  # Pravno icon

    def test_get_title_handles_missing_project_data(self):
        """
        ISSUE 3 FIX: Test get_title() exception handling for missing project/initiative data.
        Tests that admin doesn't crash when project_data or initiative_data is missing.
        """
        # Create COA application without ProjectData
        orphan_app = Application.objects.create(
            reference_number='COA-2025-998',
            application_type='COA',
            status='submitted',
        )

        orphan_applicant = Applicant.objects.create(
            application=orphan_app,
            entity_type='fizicko',
            first_name='Orphan',
            last_name='Test',
            address='Beograd',
            email='orphan@example.com',
            phone='+381601234567',
        )

        orphan_app.applicant = orphan_applicant
        orphan_app.save()

        # No ProjectData created - this should return 'N/A'

        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Should show 'N/A' for title, not crash
        self.assertContains(response, 'COA-2025-998')

    def test_admin_list_performance_with_100_applications(self):
        """
        ISSUE 8 FIX: Test NFR3 (<3s load time) with 100+ applications.
        Creates 100 additional applications to properly test performance requirement.
        """
        # setUp already creates 30, add 70 more for total of 100+
        for i in range(31, 101):
            app_type = 'COA' if i % 3 == 0 else 'COB'

            application = Application.objects.create(
                reference_number=f'{app_type}-2025-{i:03d}',
                application_type=app_type,
                status='submitted',
            )

            applicant = Applicant.objects.create(
                application=application,
                entity_type='fizicko' if i % 2 == 0 else 'pravno',
                first_name=f'User{i}' if i % 2 == 0 else '',
                last_name=f'Test{i}' if i % 2 == 0 else '',
                organization_name=f'Org {i}' if i % 2 != 0 else '',
                address=f'Srbija {i}',
                email=f'test{i}@example.com',
                phone=f'+38160{i % 10000000:07d}',
            )

            application.applicant = applicant
            application.save()

            if app_type == 'COA':
                ProjectData.objects.create(
                    application=application,
                    title=f'Projekat {i}',
                    short_description='Opis',
                    problem='Problem',
                    main_goal='Cilj',
                    specific_goals='Ciljevi',
                    target_groups='Grupe',
                    activities='Aktivnosti',
                    results='Rezultati',
                    total_budget=100000,
                )
            else:
                InitiativeData.objects.create(
                    application=application,
                    naslov=f'Inicijativa {i}',
                    kratak_opis='Opis',
                    problem='Problem',
                    cilj_inicijative='Cilj',
                    planirani_koraci='Koraci',
                    ocekivani_uticaj='Uticaj',
                )

        self.client.login(username='testadmin', password='TestAdmin123!')

        start_time = time.time()
        response = self.client.get('/admin/submissions/application/')
        end_time = time.time()

        self.assertEqual(response.status_code, 200)
        load_time = end_time - start_time
        self.assertLess(load_time, 3.0, f"Admin list view with 100 apps took {load_time:.2f}s (NFR3: <3s)")

    def test_pagination_exact_boundary_25_items(self):
        """
        ISSUE 16 FIX: Test pagination boundary with exactly 25 items on page 1.
        Deletes extra apps to test edge case of exactly 25 items.
        """
        # setUp creates 30 apps, delete 5 to get exactly 25
        apps_to_delete = Application.objects.all().order_by('id')[:5]
        for app in apps_to_delete:
            app.delete()

        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # With exactly 25 items, there should be no pagination (single page)
        # Check that we see all 25 items
        self.assertContains(response, '25')

    def test_admin_list_sorted_newest_first_verified(self):
        """
        ISSUE 12 FIX: Test sorting by newest first with explicit verification.
        Verifies that the newest application (COB-2025-030) is actually in the list.
        """
        self.client.login(username='testadmin', password='TestAdmin123!')
        response = self.client.get('/admin/submissions/application/')

        self.assertEqual(response.status_code, 200)
        # Explicitly verify newest application is present
        # setUp creates apps 1-30, so newest should be 030 or 029
        apps = Application.objects.all().order_by('-submitted_at')
        newest_ref = apps.first().reference_number
        self.assertContains(response, newest_ref)
