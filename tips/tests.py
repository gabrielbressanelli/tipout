from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from .email_backends import ResendEmailBackend
from .models import TipEntry, current_paycheck_window, next_pay_date, paycheck_window
from .models import Profile
from .views import _last_paid_pay_date, _stats_for_entries


class TipEntryCalculationTests(TestCase):
    def test_assistant_tipout_uses_food_sales_and_bar_tipout_uses_alcohol(self):
        user = User.objects.create_user(username='server')
        entry = TipEntry(
            server=user,
            tips_made=Decimal('250.00'),
            total_sales=Decimal('1000.00'),
            liquor_sales=Decimal('100.00'),
            beer_sales=Decimal('50.00'),
            wine_sales=Decimal('50.00'),
            assistant_percent=2,
        )

        self.assertEqual(entry.combined_sales, Decimal('1200.00'))
        self.assertEqual(entry.alcohol_sales, Decimal('200.00'))
        self.assertEqual(entry.assistant_tipout, Decimal('20.00'))
        self.assertEqual(entry.bar_tipout, Decimal('6.00'))
        self.assertEqual(entry.total_tipout, Decimal('26.00'))
        self.assertEqual(entry.net_tips, Decimal('224.00'))


class PaycheckWindowTests(TestCase):
    def test_august_10_paycheck_holds_back_previous_week(self):
        pay_date = date(2026, 8, 10)

        self.assertEqual(paycheck_window(pay_date), (date(2026, 7, 20), date(2026, 8, 2)))
        self.assertEqual(
            current_paycheck_window(date(2026, 8, 9)),
            {
                'pay_date': pay_date,
                'period_start': date(2026, 7, 20),
                'period_end': date(2026, 8, 2),
            },
        )

    def test_next_pay_date_follows_biweekly_mondays(self):
        self.assertEqual(next_pay_date(date(2026, 8, 10)), date(2026, 8, 10))
        self.assertEqual(next_pay_date(date(2026, 8, 11)), date(2026, 8, 24))
        self.assertEqual(paycheck_window(date(2026, 8, 24)), (date(2026, 8, 3), date(2026, 8, 16)))

    def test_last_paid_paycheck_before_august_10_is_july_27(self):
        self.assertEqual(_last_paid_pay_date(date(2026, 8, 9)), date(2026, 7, 27))
        self.assertEqual(paycheck_window(date(2026, 7, 27)), (date(2026, 7, 6), date(2026, 7, 19)))


class PaycheckHistoryTests(TestCase):
    def test_history_stats_include_10_percent_tax_paid_without_after_tax_total(self):
        user = User.objects.create_user(username='history-server')
        entries = [
            TipEntry.objects.create(
                server=user,
                service_date=date(2026, 7, 8),
                tips_made=Decimal('200.00'),
                total_sales=Decimal('1000.00'),
                liquor_sales=Decimal('100.00'),
                beer_sales=Decimal('50.00'),
                wine_sales=Decimal('50.00'),
                assistant_percent=2,
            ),
            TipEntry.objects.create(
                server=user,
                service_date=date(2026, 7, 9),
                tips_made=Decimal('100.00'),
                total_sales=Decimal('500.00'),
                liquor_sales=Decimal('0.00'),
                beer_sales=Decimal('0.00'),
                wine_sales=Decimal('0.00'),
                assistant_percent=0,
            ),
        ]

        stats = _stats_for_entries(entries)

        self.assertEqual(stats['total'], Decimal('274.00'))
        self.assertEqual(stats['tax_paid'], Decimal('27.40'))
        self.assertEqual(stats['days_worked'], 2)
        self.assertEqual(stats['average_per_day'], Decimal('137.00'))

    def test_paycheck_history_month_view_renders_total_and_tax(self):
        user = User.objects.create_user(username='history-render', password='pass12345')
        TipEntry.objects.create(
            server=user,
            service_date=date(2026, 7, 8),
            tips_made=Decimal('200.00'),
            total_sales=Decimal('1000.00'),
            liquor_sales=Decimal('100.00'),
            beer_sales=Decimal('50.00'),
            wine_sales=Decimal('50.00'),
            assistant_percent=2,
        )

        self.client.force_login(user)
        response = self.client.get('/paychecks/?view=month&month=2026-07')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paycheck history')
        self.assertContains(response, '$174.00')
        self.assertContains(response, '10% tax paid: $17.40')


class PasswordResetEmailTests(TestCase):
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='Tipout <no-reply@example.com>',
    )
    def test_password_reset_sends_branded_email_to_profile_email(self):
        user = User.objects.create_user(
            username='reset-server',
            email='old@example.com',
            password='pass12345',
        )
        Profile.objects.create(
            user=user,
            system_username='reset-server',
            name='Reset Server',
            email='server@example.com',
        )

        response = self.client.post('/password-reset/', {'email': 'server@example.com'})

        self.assertRedirects(response, '/password-reset/done/')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['server@example.com'])
        self.assertEqual(mail.outbox[0].alternatives[0][1], 'text/html')
        self.assertIn('Tipout', mail.outbox[0].alternatives[0][0])
        self.assertIn('/reset/', mail.outbox[0].body)

    @override_settings(
        RESEND_API_KEY='test-key',
        RESEND_API_URL='https://api.resend.test/emails',
        DEFAULT_FROM_EMAIL='Tipout <no-reply@example.com>',
    )
    def test_resend_backend_posts_email_payload(self):
        message = EmailMultiAlternatives(
            subject='Reset your Tipout password',
            body='Plain reset link',
            from_email='Tipout <no-reply@example.com>',
            to=['server@example.com'],
        )
        message.attach_alternative('<strong>Reset</strong>', 'text/html')
        response = Mock()
        response.status = 202
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)

        with patch('tips.email_backends.urlopen', return_value=response) as mocked_urlopen:
            sent = ResendEmailBackend().send_messages([message])

        self.assertEqual(sent, 1)
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.resend.test/emails')
        self.assertEqual(request.headers['Authorization'], 'Bearer test-key')
        self.assertIn(b'"from": "Tipout <no-reply@example.com>"', request.data)
        self.assertIn(b'"to": ["server@example.com"]', request.data)
        self.assertIn(b'"html": "<strong>Reset</strong>"', request.data)
        self.assertIn(b'"server@example.com"', request.data)
