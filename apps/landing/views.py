from django.views.generic import TemplateView


class LandingPageView(TemplateView):
    """
    Landing page view prikazuje početnu stranu sa informacijama o prijavi.

    Acceptance Criteria: AC1-8
    - AC1: Domovik i donor logotipi
    - AC2: Informativni tekst o procesu prijave
    - AC3: Excel template download
    - AC4: Baneri za odabir tipa prijave (COA/COB)
    - AC5: Civic Tech color palette
    - AC6: Performance < 2s
    - AC7: Browser compatibility
    - AC8: Responsive design
    """
    template_name = 'landing/home.html'
