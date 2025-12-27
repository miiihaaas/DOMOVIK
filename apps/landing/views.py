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


class PolitikaPrivatnostiView(TemplateView):
    """
    Politika privatnosti page - Story 2.10 Task 8
    Prikazuje politiku privatnosti za DOMOVIK platformu.

    GDPR Compliance:
    - Data handling policies
    - 7-day draft retention
    - Client-side storage disclosure
    - User rights (access, deletion, portability)
    """
    template_name = 'static_pages/politika-privatnosti.html'


class UsloviKoristenjaView(TemplateView):
    """
    Uslovi korišćenja page - Story 2.10 Task 8
    Prikazuje uslove korišćenja za DOMOVIK platformu.

    Content:
    - Application process terms
    - User responsibilities
    - File upload requirements
    - Submission guidelines
    """
    template_name = 'static_pages/uslovi-koristenja.html'
