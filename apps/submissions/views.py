from django.views.generic import TemplateView


class ProjectApplicationView(TemplateView):
    """
    Placeholder view for COA (Project) application form.
    Full implementation in Epic 2 (Stories 2.1-2.15).
    """
    template_name = 'submissions/coa_form.html'


class InitiativeApplicationView(TemplateView):
    """
    Placeholder view for COB (Initiative) application form.
    Full implementation in Epic 3 (Stories 3.1-3.6).
    """
    template_name = 'submissions/cob_form.html'
