from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.common.test_utils import auth_client, create_user


class RegistrationTests(APITestCase):
    def test_registration_creates_user(self):
        url = reverse("auth-register")
        response = self.client.post(url, {
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "first_name": "New",
            "last_name": "User",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_weak_password_rejected(self):
        url = reverse("auth-register")
        response = self.client.post(url, {
            "email": "weak@example.com",
            "password": "123",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginAndMeTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="u1@example.com", password="StrongPass123!")

    def test_login_returns_tokens(self):
        url = reverse("auth-login")
        response = self.client.post(url, {"email": "u1@example.com", "password": "StrongPass123!"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_me_endpoint(self):
        client = auth_client(self.user)
        response = client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "u1@example.com")

    def test_logout_blacklists_refresh_token(self):
        login_response = self.client.post(reverse("auth-login"), {"email": "u1@example.com", "password": "StrongPass123!"})
        refresh = login_response.data["refresh"]
        client = auth_client(self.user)
        logout_response = client.post(reverse("auth-logout"), {"refresh": refresh})
        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)

        refresh_response = self.client.post(reverse("auth-refresh"), {"refresh": refresh})
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
