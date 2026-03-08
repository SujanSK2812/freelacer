# # from django.urls import path
# # from . import views

# # urlpatterns = [
# #     
# #     path("job/<int:id>/", views.job_detail, name="job_detail"),
# # ]


# from django.urls import path
# from . import views

# urlpatterns = [

# path('freelancer/home/', views.freelancer_home, name='freelancer_home'),

# path("feed/",views.job_feed,name="job_feed"),

# path("post-job/",views.create_job,name="create_job"),

# path("like/<int:id>/",views.like_job,name="like_job"),


# path("job/<int:id>/", views.job_detail, name="job_detail"),

# path("post-job/",views.post_job,name="post_job"),

# path("client-home/",views.client_home,name="client_home"),

# path("create-job/",views.create_job,name="create_job"),

# path("react/<int:id>/<str:reaction>/",views.react_job,name="react_job"),

# path("comment/<int:id>/",views.comment_job,name="comment_job"),

# ]
from django.urls import path
from . import views

urlpatterns = [

# Freelancer side
path("freelancer/home/", views.freelancer_home, name="freelancer_home"),
path("job/<int:id>/", views.job_detail, name="job_detail"),

# Client side
path("client/home/", views.client_home, name="client_home"),

# Job Post
path("create-post/", views.create_job, name="create_job"),

# Freelancer Job Post
path("post-job/", views.post_job, name="post_job"),

# Reactions
path("react/<int:id>/<str:reaction>/", views.react_job, name="react_job"),

# Comments
path("comment/<int:id>/", views.comment_job, name="comment_job"),

]