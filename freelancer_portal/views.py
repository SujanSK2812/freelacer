from django.shortcuts import render

def home(request):
    context = {}

    if request.user.is_authenticated:
        context["role"] = request.user.role
    else:
        context["role"] = "public"

    return render(request, "home/index.html", context)


def how_it_works(request):
    return render(request, "how_it_works.html")