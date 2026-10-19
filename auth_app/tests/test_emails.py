from django.core import mail
from django.test import SimpleTestCase, override_settings

from auth_app.utils import send_templated_email


class EmailFormatTests(SimpleTestCase):
    """The logo must show up once and at a fixed size in all clients."""

    def send_reset_email(self):
        context = {'reset_link': 'http://127.0.0.1:5500/reset'}
        send_templated_email(
            'Reset your Password',
            'password_reset_email',
            context,
            'user@example.com',
        )
        return mail.outbox[0].message()

    def test_logo_is_embedded_in_html_part_not_attached(self):
        message = self.send_reset_email()
        self.assertEqual(list(message.iter_attachments()), [])
        related = message.get_body(preferencelist=('related',))
        content_types = [
            part.get_content_type() for part in related.iter_parts()
        ]
        self.assertEqual(content_types, ['text/html', 'image/png'])

    def test_logo_has_content_id_and_fixed_width(self):
        message = self.send_reset_email()
        html = message.get_body(preferencelist=('html',)).get_content()
        self.assertIn('src="cid:videoflix-logo"', html)
        self.assertIn('width: 251px', html)
        logo = message.get_body(preferencelist=('related',)).get_payload()[1]
        self.assertEqual(logo['Content-ID'], '<videoflix-logo>')

    def test_plain_text_version_is_included(self):
        message = self.send_reset_email()
        text = message.get_body(preferencelist=('plain',)).get_content()
        self.assertIn('http://127.0.0.1:5500/reset', text)

    @override_settings(DEFAULT_FROM_EMAIL='Videoflix <team@videoflix.dev>')
    def test_message_id_uses_sender_domain(self):
        message = self.send_reset_email()
        self.assertTrue(message['Message-ID'].endswith('@videoflix.dev>'))
