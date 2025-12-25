# -*- coding: utf-8 -*-
"""
Views for COA/COB application submission.
Story 1.3: Created placeholder views
Story 2.2: Add COAFormSectionI form handling
"""
from django.views.generic import TemplateView
from apps.submissions.forms import COAFormSectionI


class ProjectApplicationView(TemplateView):
    """
    COA (Projekat) application form view.

    Story 1.3: Basic template rendering
    Story 2.2: Add Section I form handling (GET request - display form)
    Story 2.11: Add POST request handling (form submission)
    """
    template_name = 'submissions/coa_form.html'

    def get_context_data(self, **kwargs):
        """Add COAFormSectionI form to context"""
        context = super().get_context_data(**kwargs)
        context['form'] = COAFormSectionI()
        context['current_section'] = 1  # Section I
        return context


class InitiativeApplicationView(TemplateView):
    """
    Placeholder view for COB (Initiative) application form.
    Full implementation in Epic 3 (Stories 3.1-3.6).
    """
    template_name = 'submissions/cob_form.html'
