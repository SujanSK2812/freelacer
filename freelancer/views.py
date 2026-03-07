from django.shortcuts import render
from django.contrib.auth.decorators import login_required




@login_required
def freelancer_home(request):
    return render(request,"freelancer/home.html")


@login_required
def freelancer_dashboard(request):
    return render(request,"freelancer/dashboard.html")