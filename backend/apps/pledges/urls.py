from django.urls import path

from .views import CustomerOnboardingView, ImageUploadView, PledgeDetailView, PledgeListView


urlpatterns = [
    path("pledges/", PledgeListView.as_view(), name="pledge-list"),
    path("pledges/<uuid:id>/", PledgeDetailView.as_view(), name="pledge-detail"),
    path("onboarding/register-customer/", CustomerOnboardingView.as_view(), name="customer-onboarding"),
    path("uploads/", ImageUploadView.as_view(), name="image-upload"),
]