from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required


@login_required
def client_home(request):

    if request.user.role != "client":
        return redirect("/")

    return render(request,"client/home.html")

@login_required
def client_dashboard(request):
    return render(request,"client/dashboard.html")