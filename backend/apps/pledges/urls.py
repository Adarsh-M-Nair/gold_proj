from django.urls import path

from .views import (
    CustomerOnboardingView,
    CatalogueItemDetailView,
    CatalogueItemImageView,
    ImageUploadView,
    MatchingSearchView,
    PledgeDetailView,
    PledgeListView,
)


urlpatterns = [
    path("pledges/", PledgeListView.as_view(), name="pledge-list"),
    path("pledges/<uuid:id>/", PledgeDetailView.as_view(), name="pledge-detail"),
    path("onboarding/register-customer/", CustomerOnboardingView.as_view(), name="customer-onboarding"),
    path("uploads/", ImageUploadView.as_view(), name="image-upload"),
    path("matching/search/", MatchingSearchView.as_view(), name="matching-search"),
    path("catalogue/<str:category>/<str:item_id>/", CatalogueItemDetailView.as_view(), name="catalogue-item-detail"),
    path(
        "catalogue/<str:category>/<str:item_id>/images/<str:filename>",
        CatalogueItemImageView.as_view(),
        name="catalogue-item-image",
    ),
]