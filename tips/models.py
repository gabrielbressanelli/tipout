from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


PAYCHECK_ANCHOR_DATE = date(2026, 8, 10)
PAYCHECK_INTERVAL_DAYS = 14
HELD_BACK_DAYS = 7
MONEY_QUANT = Decimal('0.01')
BAR_TIPOUT_PERCENT = Decimal('3')


def money(value):
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def next_pay_date(today=None):
    today = today or timezone.localdate()
    if today <= PAYCHECK_ANCHOR_DATE:
        return PAYCHECK_ANCHOR_DATE

    days_since_anchor = (today - PAYCHECK_ANCHOR_DATE).days
    periods_after_anchor = (days_since_anchor + PAYCHECK_INTERVAL_DAYS - 1) // PAYCHECK_INTERVAL_DAYS
    return PAYCHECK_ANCHOR_DATE + timedelta(days=periods_after_anchor * PAYCHECK_INTERVAL_DAYS)


def paycheck_window(pay_date):
    period_end = pay_date - timedelta(days=HELD_BACK_DAYS + 1)
    period_start = period_end - timedelta(days=PAYCHECK_INTERVAL_DAYS - 1)
    return period_start, period_end


def current_paycheck_window(today=None):
    pay_date = next_pay_date(today)
    period_start, period_end = paycheck_window(pay_date)
    return {
        'pay_date': pay_date,
        'period_start': period_start,
        'period_end': period_end,
    }


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    system_username = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)

    def __str__(self):
        return self.name


class TipEntry(models.Model):
    ASSISTANT_PERCENT_CHOICES = (
        (0, 'No assistant'),
        (1, '1%'),
        (2, '2%'),
        (3, '3%'),
    )

    server = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tip_entries')
    service_date = models.DateField(default=timezone.localdate)
    tips_made = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    total_sales = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    liquor_sales = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    beer_sales = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    wine_sales = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    assistant_percent = models.PositiveSmallIntegerField(
        choices=ASSISTANT_PERCENT_CHOICES,
        default=0,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-service_date', '-created_at']
        indexes = [
            models.Index(fields=['server', 'service_date']),
        ]

    def __str__(self):
        return f'{self.server.username} - {self.service_date}'

    @property
    def combined_sales(self):
        return money(self.total_sales + self.liquor_sales + self.beer_sales + self.wine_sales)

    @property
    def alcohol_sales(self):
        return money(self.liquor_sales + self.beer_sales + self.wine_sales)

    @property
    def assistant_tipout(self):
        rate = Decimal(self.assistant_percent) / Decimal('100')
        return money(self.total_sales * rate)

    @property
    def bar_tipout(self):
        rate = BAR_TIPOUT_PERCENT / Decimal('100')
        return money(self.alcohol_sales * rate)

    @property
    def total_tipout(self):
        return money(self.assistant_tipout + self.bar_tipout)

    @property
    def net_tips(self):
        return money(self.tips_made - self.total_tipout)
