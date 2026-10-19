from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from auth_app.utils import account_activation_token, encode_uid

from .helpers import create_user

FAILED = {'message': 'Activation failed.'}


class ActivationTests(APITestCase):
    """Tests for GET /api/activate/<uidb64>/<token>/."""

    def setUp(self):
        self.user = create_user(is_active=False)
        self.uid = encode_uid(self.user)
        self.token = account_activation_token.make_token(self.user)

    def activate(self, uid, token):
        return self.client.get(reverse('activate', args=[uid, token]))

    def test_valid_link_activates_account(self):
        response = self.activate(self.uid, self.token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {'message': 'Account successfully activated.'}
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_link_can_only_be_used_once(self):
        self.activate(self.uid, self.token)
        response = self.activate(self.uid, self.token)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, FAILED)

    def test_invalid_links_are_rejected(self):
        invalid_links = {
            'wrong token': (self.uid, 'abc-123'),
            'garbage uid': ('!!!', self.token),
            'unknown user': (encode_uid(type(self.user)(pk=999)), self.token),
        }
        for case, (uid, token) in invalid_links.items():
            with self.subTest(case=case):
                response = self.activate(uid, token)
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST
                )
                self.assertEqual(response.data, FAILED)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_token_of_another_user_is_rejected(self):
        other_user = create_user(email='other@example.com', is_active=False)
        other_token = account_activation_token.make_token(other_user)
        response = self.activate(self.uid, other_token)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
