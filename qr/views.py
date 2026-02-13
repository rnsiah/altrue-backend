import base64
import binascii
import functools


from django.shortcuts import render
from api.models import User, UserProfile
from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.signing import BadSignature, Signer
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import condition










  



