from django.urls import path
from .views import LandingPageView, PolitikaPrivatnostiView, UsloviKoristenjaView

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing_home'),
    # Story 2.10 - Policy pages
    path('politika-privatnosti/', PolitikaPrivatnostiView.as_view(), name='politika_privatnosti'),
    path('uslovi-koristenja/', UsloviKoristenjaView.as_view(), name='uslovi_koristenja'),
]
