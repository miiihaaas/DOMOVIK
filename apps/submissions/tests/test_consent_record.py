# -*- coding: utf-8 -*-
"""
Tests for the consent record - Z11 (2026-07-25).

GDPR Art. 7(1) / ZZPL čl. 15 require the controller to be able to DEMONSTRATE that
consent was given. Before Z11 the three checkboxes were validated and discarded, and
the COA path did not validate them on the server at all.
"""
import json

from django.test import Client, TestCase
from django.utils import timezone

from apps.submissions.constants import POLICY_VERSION
from apps.submissions.models import Application
from apps.submissions.services import client_ip, consent_fields, consent_is_complete


class ConsentIsCompleteTests(TestCase):
    """All three checkboxes are required; anything else is refused."""

    def test_accepts_all_three(self):
        self.assertTrue(consent_is_complete({'privacy': True, 'terms': True, 'accuracy': True}))

    def test_rejects_each_missing_checkbox(self):
        for missing in ('privacy', 'terms', 'accuracy'):
            data = {'privacy': True, 'terms': True, 'accuracy': True}
            data[missing] = False
            with self.subTest(missing=missing):
                self.assertFalse(consent_is_complete(data))

    def test_rejects_empty_and_non_dict(self):
        for value in ({}, None, [], 'true'):
            with self.subTest(value=value):
                self.assertFalse(consent_is_complete(value))

    def test_rejects_extra_key_without_the_required_ones(self):
        self.assertFalse(consent_is_complete({'something_else': True}))


class ConsentFieldsTests(TestCase):
    """The stored record pins down what was agreed, when, and to which policy text."""

    def test_records_all_values(self):
        before = timezone.now()
        fields = consent_fields(
            {'privacy': True, 'terms': True, 'accuracy': True}, '203.0.113.7'
        )

        self.assertTrue(fields['consent_privacy'])
        self.assertTrue(fields['consent_terms'])
        self.assertTrue(fields['consent_accuracy'])
        self.assertEqual(fields['consent_ip'], '203.0.113.7')
        self.assertEqual(fields['consent_policy_version'], POLICY_VERSION)
        self.assertGreaterEqual(fields['consent_at'], before)

    def test_policy_version_is_recorded_so_later_edits_cannot_rewrite_history(self):
        """The version must be a concrete value, not blank."""
        fields = consent_fields({'privacy': True, 'terms': True, 'accuracy': True})
        self.assertTrue(fields['consent_policy_version'])

    def test_missing_ip_is_stored_as_null_not_empty_string(self):
        """GenericIPAddressField rejects '' - it has to be None."""
        self.assertIsNone(consent_fields({'privacy': True}, None)['consent_ip'])


class ClientIpTests(TestCase):
    """gunicorn is on a unix socket, so the address comes from X-Forwarded-For."""

    class _Request:
        def __init__(self, **meta):
            self.META = meta

    def test_uses_leftmost_forwarded_address(self):
        req = self._Request(HTTP_X_FORWARDED_FOR='203.0.113.7, 10.0.0.1', REMOTE_ADDR='')
        self.assertEqual(client_ip(req), '203.0.113.7')

    def test_falls_back_to_remote_addr(self):
        self.assertEqual(client_ip(self._Request(REMOTE_ADDR='198.51.100.4')), '198.51.100.4')

    def test_accepts_ipv6(self):
        req = self._Request(HTTP_X_FORWARDED_FOR='2001:db8::1')
        self.assertEqual(client_ip(req), '2001:db8::1')

    def test_returns_none_when_absent(self):
        self.assertIsNone(client_ip(self._Request()))

    def test_discards_garbage_rather_than_crashing_the_submission(self):
        """A spoofed header must not blow up the insert with a ValidationError."""
        for junk in ('not-an-ip', '<script>alert(1)</script>', '999.999.999.999'):
            with self.subTest(junk=junk):
                self.assertIsNone(client_ip(self._Request(HTTP_X_FORWARDED_FOR=junk)))


class ConsentSubmissionTests(TestCase):
    """End to end: a real POST to /submit/ must persist the consent it validated."""

    PAYLOAD = {
        'application_type': 'COA',
        'applicant': {
            'entity_type': 'fizicko',
            'first_name': 'Marko',
            'last_name': 'Marković',
            'address': 'Kneza Miloša 10, Beograd',
            'email': 'marko@example.com',
            'phone': '+381111234567',
        },
        'project': {
            'title': 'Projekat za proveru saglasnosti',
            'short_description': 'Opis',
            'problem': 'Problem',
            'main_goal': 'Cilj',
            'specific_goals': 'Ciljevi',
            'target_groups': 'Grupe',
            'activities': 'Aktivnosti',
            'results': 'Rezultati',
            'total_budget': 500000,
        },
        'consent': {'privacy': True, 'terms': True, 'accuracy': True},
    }

    def _submit(self, payload, forwarded_for='203.0.113.42'):
        client = Client()
        session = client.session  # the submit view refuses requests without a session
        session.save()
        return client.post(
            '/submit/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_FORWARDED_FOR=forwarded_for,
        )

    def test_consent_is_stored_on_the_application(self):
        before = timezone.now()

        response = self._submit(self.PAYLOAD)
        self.assertEqual(response.status_code, 200, response.content[:300])

        application = Application.objects.get(reference_number=response.json()['reference_number'])
        self.assertTrue(application.consent_privacy)
        self.assertTrue(application.consent_terms)
        self.assertTrue(application.consent_accuracy)
        self.assertEqual(application.consent_policy_version, POLICY_VERSION)
        self.assertEqual(application.consent_ip, '203.0.113.42')
        self.assertGreaterEqual(application.consent_at, before)

    def test_submission_without_full_consent_is_refused_and_stores_nothing(self):
        payload = {**self.PAYLOAD, 'consent': {'privacy': True, 'terms': True, 'accuracy': False}}

        response = self._submit(payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn('saglasnosti', response.json()['error'])
        self.assertEqual(Application.objects.count(), 0)

    def test_submission_without_any_consent_key_is_refused(self):
        payload = {k: v for k, v in self.PAYLOAD.items() if k != 'consent'}

        response = self._submit(payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Application.objects.count(), 0)
