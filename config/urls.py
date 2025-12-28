"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from apps.submissions import views as submission_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.landing.urls')),  # Root → landing page
    path('projekat/', submission_views.ProjectApplicationView.as_view(), name='coa_form'),
    path('inicijativa/', submission_views.InitiativeApplicationView.as_view(), name='cob_form'),
    # File upload and submission API endpoints (Story 2.8, 2.11)
    path('api/files/', include(('apps.submissions.urls', 'submissions'), namespace='files')),
    path('api/submissions/', include(('apps.submissions.urls', 'submissions'), namespace='submissions')),
]
