import os

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect, get_object_or_404
from pyexpat.errors import messages
from dotenv import load_dotenv
from .models import Docs, Users_To_Docs

load_dotenv()
fast_api_url = os.getenv('FAST_API_URL')

allowed_file_types = ['.jpg']

@login_required
def index(request):
    documents = Docs.objects.all()
    return render(request, 'frapp/index.html', {'documents': documents})


@login_required
def add_image(request):
    message = ''
    if request.method == 'POST':

        uploaded_file = request.FILES['file']
        filename = uploaded_file.name
        type = os.path.splitext(filename)[1].lower()
        if type not in allowed_file_types:
            message = 'Загружать можно только .jpg!'
            return render(request, 'frapp/upload.html', {'message': message})
        url = f'http://{fast_api_url}/upload_doc'
        files = {'file': (filename, uploaded_file.read())}
        response = requests.post(url, files=files)

        if response.status_code == 200:
            new_doc = Docs(file_path=uploaded_file)
            new_doc.save()

            Users_To_Docs.objects.create(
                username=request.user.username,
                docs_id=new_doc
            )

            return redirect('index')
        else:
            message = "Ошибка при загрузке файла на сервер."
            return render(request, 'frapp/upload.html', {'message': message})

    return render(request, 'frapp/upload.html')

@login_required
def delete_image(request):
    if not request.user.is_superuser:
        return render(request, 'frapp/need_admin_rights.html')
    message = ''
    if request.method == 'POST':
        doc_id = request.POST.get('doc_id')
        try:
            doc = get_object_or_404(Docs, id=doc_id)
            fastapi_url = f'http://{fast_api_url}/doc_delete/{doc_id}'
            response = requests.delete(fastapi_url)

            if response.status_code == 200:
                file_path = str(doc.file_path)
                full_path = os.path.join(settings.MEDIA_ROOT, 'documents', os.path.basename(file_path))
                if os.path.exists(full_path):
                    os.remove(full_path)
                doc.delete()
                message = f"Документ {doc_id} успешно удален."
            else:
                message = "Какая-то ошибка 500."
        except Docs.DoesNotExist:
            message = "Ошибка 404"
        except Exception as e:
            message = f"Произошла ошибка: {str(e)}"

    return render(request, 'frapp/delete_image.html', {'message': message})

@login_required
def analyze(request):
    message = ''
    if request.method == 'POST':
        doc_id = request.POST.get('doc_id')
        try:
            doc = get_object_or_404(Docs, id=doc_id)
            fastapi_url = f'http://{fast_api_url}/doc_analyse/{doc_id}'
            response = requests.patch(fastapi_url)

            if response.status_code == 200:
                message = f"Документ с ID {doc_id} успешно отправлен сдавать анализы."
            else:
                message = "Какая-то ошибка 500."
        except Docs.DoesNotExist:
            message = "Ошибка 404"
        except Exception as e:
            message = f"Произошла ошибка: {str(e)}"

    return render(request, 'frapp/analyze.html', {'message': message})

@login_required
def info(request):
    message = ''
    if request.method == 'POST':
        doc_id = request.POST.get('doc_id')
        try:
            doc = get_object_or_404(Docs, id=doc_id)
            user = get_object_or_404(Users_To_Docs, docs_id=doc_id)
            fastapi_url = f'http://{fast_api_url}/get_text/{doc_id}'
            response = requests.get(fastapi_url)
            response.raise_for_status()

            data = response.json()
            text_from_api = data.get('Text on image')

            if response.status_code == 200:
                return render(request, 'frapp/info.html', {
                    'doc': doc,
                    'text_from_api': text_from_api,
                    'user': user,
                    'show_info': True
                })
            else:
                message = "Какая-то ошибка 500."
        except Docs.DoesNotExist:
            message = "Ошибка 404"
        except Exception as e:
            message = f"Произошла ошибка: {str(e)}"
        except requests.RequestException:
            message = 'Ошибка FASTAPI'
    return render(request, 'frapp/info.html', {'message': message, 'show_info': False})


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'frapp/register.html', {'form': form})
