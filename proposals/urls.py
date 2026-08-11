from django.urls import path
from . import views

urlpatterns = [

    path(
        "submit/<int:job_id>/",
        views.submit_proposal,
        name="submit_proposal"
    ),

    path(
        "my-proposals/",
        views.my_proposals,
        name="my_proposals"
    ),

]