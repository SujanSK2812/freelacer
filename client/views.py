from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required


from django.contrib.auth import get_user_model

User = get_user_model()

def client_home(request):
    freelancers = User.objects.filter(role="freelancer")

    return render(request, "client/home.html", {
        "freelancers": freelancers
    })

@login_required
def client_dashboard(request):
    return render(request,"client/dashboard.html")


@login_required
def create_job(request):
    if request.method == "POST":
        description = request.POST.get("description")
        image = request.FILES.get("image")

        # temporary print (later save to DB)
        print(description, image)

        return redirect('client_home')  # redirect after post

    return redirect('client_home')