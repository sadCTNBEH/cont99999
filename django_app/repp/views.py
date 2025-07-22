import requests
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from prometheus_client import generate_latest

from cont99998.settings import BASE_URL
from repp.forms import LoginForm


def is_token_valid(token):
    try:
        response = requests.post(f"{BASE_URL}:8080/api/v1/token/verify/", json={
            'token': token
        })
        return response.status_code == 200
    except requests.RequestException:
        return False


def refresh_access_token(refresh_token):
    try:
        response = requests.post(f"{BASE_URL}:8080/api/v1/token/refresh/", json={
            'refresh': refresh_token
        })
        if response.status_code == 200:
            data = response.json()
            return data['access']
    except Exception as e:
        return None

def jwt_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            response = requests.post(f"{BASE_URL}:8080/api/v1/token/", json={
                'username': username,
                'password': password
            })
            if response.status_code == 200:
                data = response.json()
                request.session['access_token'] = data['access']
                request.session['refresh_token'] = data['refresh']
                return redirect('index')
            else:
                messages.error(request, 'Неверные данные')
    else:
        form = LoginForm()
    return render(request, 'frapp/login.html', {'form': form})


def metrics(request):
    return HttpResponse(generate_latest(), content_type='text/plain')