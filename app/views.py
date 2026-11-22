
import os
import uuid
import json

from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse, FileResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Thumbnail

from .services.analyzer import (
    analyze_image,
    detect_text,
    predict_ctr,
    analyze_heatmap
)

from .services.ai_service import (
    analyze_thumbnail,
    generate_thumbnail_from_prompt
)

from .services.builder import build_thumbnail


# =====================================================
# FILE UPLOAD SETTINGS
# =====================================================

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_uploaded_file(uploaded_file):
    upload_dir = settings.MEDIA_ROOT / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    extension = uploaded_file.name.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{extension}"

    filepath = upload_dir / filename

    with open(filepath, "wb+") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    return str(filepath), filename


def get_user_id(request):
    if request.user.is_authenticated:
        return request.user.id
    return None


def get_upload_url(filename):
    return f"{settings.MEDIA_URL.rstrip('/')}/uploads/{filename}"


# =====================================================
# HOME PAGE
# =====================================================

def index(request):
    return render(request, "app/index.html")


# =====================================================
# ANALYZE THUMBNAIL
# =====================================================

@require_POST
def analyze(request):

    uploaded_file = request.FILES.get("thumbnail")

    if not uploaded_file:
        return JsonResponse({
            "success": False,
            "error": "Please upload a thumbnail."
        }, status=400)

    if not allowed_file(uploaded_file.name):
        return JsonResponse({
            "success": False,
            "error": "Invalid file format."
        }, status=400)

    try:
        filepath, filename = save_uploaded_file(uploaded_file)

        image_analysis = analyze_image(filepath)
        text_analysis = detect_text(filepath)

        ctr_prediction = predict_ctr(
            image_analysis,
            text_analysis
        )

        heatmap = analyze_heatmap(
            filepath,
            settings.MEDIA_ROOT / "uploads",
            settings.MEDIA_URL.rstrip("/") + "/uploads/"
        )

        ai_analysis = None

        try:
            ai_analysis = analyze_thumbnail(filepath)
        except Exception as error:
            print("Gemini Analysis Error:", error)

        return JsonResponse({
            "success": True,
            "image_analysis": image_analysis,
            "text_analysis": text_analysis,
            "ctr_prediction": ctr_prediction,
            "heatmap_analysis": heatmap,
            "heatmap": heatmap,
            "ai_analysis": ai_analysis
        })

    except Exception as error:
        return JsonResponse({
            "success": False,
            "error": str(error)
        }, status=500)


# =====================================================
# BUILD THUMBNAIL
# =====================================================

@require_POST
def build(request):

    image = (
        request.FILES.get("image")
        or request.FILES.get("thumbnail")
        or request.FILES.get("base_image")
    )

    person_image = (
        request.FILES.get("person")
        or request.FILES.get("person_image")
    )

    if not image:
        return JsonResponse({
            "success": False,
            "error": "Please upload a base image."
        }, status=400)

    if not allowed_file(image.name):
        return JsonResponse({
            "success": False,
            "error": "Invalid base image format."
        }, status=400)

    if person_image and not allowed_file(person_image.name):
        return JsonResponse({
            "success": False,
            "error": "Invalid person image format."
        }, status=400)

    try:
        filepath, original_filename = save_uploaded_file(image)

        person_path = None

        if person_image:
            person_path, person_filename = save_uploaded_file(person_image)

        text = request.POST.get("text", "")
        headline = request.POST.get("headline", text)

        font_size = int(request.POST.get("font_size", 60))
        text_color = request.POST.get("text_color", "#ffffff")
        position = request.POST.get("position", "bottom")

        output_path = build_thumbnail(
            image_path=filepath,
            text=text,
            font_size=font_size,
            text_color=text_color,
            position=position,
            person_image_path=person_path,
            output_dir=settings.MEDIA_ROOT / "uploads"
        )

        filename = os.path.basename(output_path)

        # Save thumbnail details in SQLite for logged-in users.
        if request.user.is_authenticated:
            Thumbnail.objects.create(
                user=request.user,
                filename=filename,
                prompt=request.POST.get("prompt", ""),
                headline=headline,
                aspect_ratio=request.POST.get("aspect_ratio", "16:9")
            )

        return JsonResponse({
            "success": True,
            "image_url": get_upload_url(filename),
            "filename": filename,
            "message": "Thumbnail created successfully."
        })

    except Exception as error:
        return JsonResponse({
            "success": False,
            "error": str(error)
        }, status=500)


# =====================================================
# GENERATE THUMBNAIL USING AI
# =====================================================

@require_POST
def generate_thumbnail(request):

    try:
        data = json.loads(request.body)

        prompt = data.get("prompt", "").strip()
        aspect_ratio = data.get("aspect_ratio", "16:9")

        if not prompt:
            return JsonResponse({
                "success": False,
                "error": "Please enter a prompt."
            }, status=400)

        result = generate_thumbnail_from_prompt(
            prompt,
            settings.MEDIA_ROOT / "uploads",
            settings.MEDIA_URL.rstrip("/") + "/uploads/",
            aspect_ratio
        )

        if not result.get("success"):
            return JsonResponse({
                "success": False,
                "error": result.get(
                    "error",
                    "Thumbnail generation failed."
                )
            }, status=500)

        return JsonResponse({
            "success": True,
            "image_url": result["image_url"]
        })

    except Exception as error:
        print("Thumbnail generation error:", error)

        return JsonResponse({
            "success": False,
            "error": str(error)
        }, status=500)


# =====================================================
# SIGN IN
# =====================================================

def signin(request):

    if request.method == "POST":

        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=email,
            password=password
        )

        if user is not None:
            auth_login(request, user)

            request.session["user_id"] = user.id
            request.session["user_name"] = user.first_name
            request.session["user_email"] = user.email

            return redirect("index")

        return render(request, "app/signin.html", {
            "error": "Invalid email or password."
        })

    return render(request, "app/signin.html")


# =====================================================
# SIGN UP
# =====================================================

def signup(request):

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not name or not email or not password:
            return render(request, "app/signup.html", {
                "error": "Please fill in all fields."
            })

        if password != confirm_password:
            return render(request, "app/signup.html", {
                "error": "Passwords do not match."
            })

        if User.objects.filter(
            Q(username__iexact=email) | Q(email__iexact=email)
        ).exists():
            return render(request, "app/signup.html", {
                "error": "An account with this email already exists."
            })

        try:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=name
            )

            auth_login(request, user)

            request.session["user_id"] = user.id
            request.session["user_name"] = user.first_name
            request.session["user_email"] = user.email

            return redirect("index")

        except Exception as error:
            return render(request, "app/signup.html", {
                "error": str(error)
            })

    return render(request, "app/signup.html")


# =====================================================
# LOGOUT
# =====================================================

def logout(request):

    auth_logout(request)

    return redirect("index")


# =====================================================
# MY COLLECTION
# =====================================================

def collection(request):

    if not request.user.is_authenticated:
        return redirect("signin")

    thumbnails = Thumbnail.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(request, "app/collection.html", {
        "thumbnails": thumbnails,
        "MEDIA_URL": settings.MEDIA_URL
    })


# =====================================================
# DOWNLOAD THUMBNAIL
# =====================================================

def download_thumbnail(request, thumbnail_id):

    if not request.user.is_authenticated:
        return redirect("signin")

    try:
        thumbnail = Thumbnail.objects.get(
            pk=thumbnail_id,
            user=request.user
        )
    except (Thumbnail.DoesNotExist, ValueError, TypeError):
        return JsonResponse({
            "error": "Thumbnail not found."
        }, status=404)

    filename = os.path.basename(thumbnail.filename)

    filepath = settings.MEDIA_ROOT / "uploads" / filename

    if not filepath.is_file():
        return JsonResponse({
            "error": "Thumbnail file not found."
        }, status=404)

    thumbnail.downloaded_at = timezone.now()
    thumbnail.save(update_fields=["downloaded_at"])

    return FileResponse(
        open(filepath, "rb"),
        as_attachment=True,
        filename=filename
    )


# =====================================================
# DELETE THUMBNAIL
# =====================================================

@require_POST
def delete_thumbnail(request, thumbnail_id):

    if not request.user.is_authenticated:
        return redirect("signin")

    try:
        thumbnail = Thumbnail.objects.get(
            pk=thumbnail_id,
            user=request.user
        )
    except (Thumbnail.DoesNotExist, ValueError, TypeError):
        return redirect("collection")

    filename = os.path.basename(thumbnail.filename)

    filepath = settings.MEDIA_ROOT / "uploads" / filename

    if filepath.is_file():
        filepath.unlink()

    thumbnail.delete()

    return redirect("collection")
