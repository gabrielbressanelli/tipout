import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMultiAlternatives


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0
        for message in email_messages:
            if self._send_message(message):
                sent_count += 1
        return sent_count

    def _send_message(self, message):
        api_key = settings.RESEND_API_KEY
        if not api_key:
            if self.fail_silently:
                return False
            raise ValueError('RESEND_API_KEY is required to send email.')

        request = Request(
            settings.RESEND_API_URL,
            data=json.dumps(self._payload(message)).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'Tipout Django Password Reset',
            },
            method='POST',
        )

        try:
            with urlopen(request, timeout=15) as response:
                return 200 <= response.status < 300
        except (HTTPError, URLError):
            if self.fail_silently:
                return False
            raise

    def _payload(self, message):
        html_body = self._html_body(message)
        payload = {
            'from': message.from_email or settings.DEFAULT_FROM_EMAIL,
            'to': message.to,
            'subject': ''.join(message.subject.splitlines()),
            'text': message.body or 'Open the password reset link to continue.',
        }

        if html_body:
            payload['html'] = html_body

        return payload

    def _html_body(self, message):
        if isinstance(message, EmailMultiAlternatives):
            for alternative in message.alternatives:
                content, mimetype = alternative[:2]
                if mimetype == 'text/html':
                    return content
        return None
