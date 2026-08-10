from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import SignUpForm, TipEntryForm
from .models import (
    PAYCHECK_ANCHOR_DATE,
    PAYCHECK_INTERVAL_DAYS,
    TipEntry,
    current_paycheck_window,
    money,
    paycheck_window,
)


TAX_PERCENT = Decimal('10')


def _sum_net_tips(entries):
    total = Decimal('0.00')
    for entry in entries:
        total += entry.net_tips
    return total


def _last_paid_pay_date(today=None):
    today = today or timezone.localdate()
    if today >= PAYCHECK_ANCHOR_DATE:
        days_since_anchor = (today - PAYCHECK_ANCHOR_DATE).days
        periods_since_anchor = days_since_anchor // PAYCHECK_INTERVAL_DAYS
        return PAYCHECK_ANCHOR_DATE + timedelta(days=periods_since_anchor * PAYCHECK_INTERVAL_DAYS)

    days_until_anchor = (PAYCHECK_ANCHOR_DATE - today).days
    periods_before_anchor = (days_until_anchor + PAYCHECK_INTERVAL_DAYS - 1) // PAYCHECK_INTERVAL_DAYS
    return PAYCHECK_ANCHOR_DATE - timedelta(days=periods_before_anchor * PAYCHECK_INTERVAL_DAYS)


def _last_month_range(today=None):
    today = today or timezone.localdate()
    first_this_month = today.replace(day=1)
    last_previous_month = first_this_month - timedelta(days=1)
    first_previous_month = last_previous_month.replace(day=1)
    return first_previous_month, last_previous_month


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _parse_week(value):
    try:
        year_text, week_text = value.split('-W', 1)
        return date.fromisocalendar(int(year_text), int(week_text), 1)
    except (AttributeError, TypeError, ValueError):
        return None


def _parse_month(value):
    try:
        year_text, month_text = value.split('-', 1)
        year = int(year_text)
        month = int(month_text)
        return date(year, month, 1), date(year, month, monthrange(year, month)[1])
    except (AttributeError, TypeError, ValueError):
        return None


def _week_value(day):
    iso_year, iso_week, _ = day.isocalendar()
    return f'{iso_year}-W{iso_week:02d}'


def _month_value(day):
    return day.strftime('%Y-%m')


def _history_range(request):
    today = timezone.localdate()
    selected_view = request.GET.get('view', 'last_paycheck')

    if selected_view == 'last_month':
        start_date, end_date = _last_month_range(today)
        return {
            'selected_view': selected_view,
            'title': 'Last month',
            'start_date': start_date,
            'end_date': end_date,
            'pay_date': None,
        }

    if selected_view == 'all_time':
        return {
            'selected_view': selected_view,
            'title': 'All time',
            'start_date': None,
            'end_date': None,
            'pay_date': None,
        }

    if selected_view == 'week':
        week_start = _parse_week(request.GET.get('week')) or today - timedelta(days=today.weekday())
        return {
            'selected_view': selected_view,
            'title': 'Selected week',
            'start_date': week_start,
            'end_date': week_start + timedelta(days=6),
            'pay_date': None,
        }

    if selected_view == 'month':
        month_range = _parse_month(request.GET.get('month')) or (today.replace(day=1), today)
        return {
            'selected_view': selected_view,
            'title': 'Selected month',
            'start_date': month_range[0],
            'end_date': month_range[1],
            'pay_date': None,
        }

    if selected_view == 'custom':
        start_date = _parse_date(request.GET.get('start')) or today - timedelta(days=6)
        end_date = _parse_date(request.GET.get('end')) or today
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        return {
            'selected_view': selected_view,
            'title': 'Custom range',
            'start_date': start_date,
            'end_date': end_date,
            'pay_date': None,
        }

    pay_date = _last_paid_pay_date(today)
    start_date, end_date = paycheck_window(pay_date)
    return {
        'selected_view': 'last_paycheck',
        'title': 'Last paycheck',
        'start_date': start_date,
        'end_date': end_date,
        'pay_date': pay_date,
    }


def _stats_for_entries(entries):
    entries = list(entries)
    total = money(sum((entry.net_tips for entry in entries), Decimal('0.00')))
    gross_tips = money(sum((entry.tips_made for entry in entries), Decimal('0.00')))
    assistant_tipout = money(sum((entry.assistant_tipout for entry in entries), Decimal('0.00')))
    bar_tipout = money(sum((entry.bar_tipout for entry in entries), Decimal('0.00')))
    food_sales = money(sum((entry.total_sales for entry in entries), Decimal('0.00')))
    alcohol_sales = money(sum((entry.alcohol_sales for entry in entries), Decimal('0.00')))

    day_totals = {}
    for entry in entries:
        day_totals[entry.service_date] = money(day_totals.get(entry.service_date, Decimal('0.00')) + entry.net_tips)

    days_worked = len(day_totals)
    sorted_day_totals = sorted(day_totals.items())
    highest_day = max(sorted_day_totals, key=lambda item: item[1], default=None)
    lowest_day = min(sorted_day_totals, key=lambda item: item[1], default=None)

    return {
        'total': total,
        'tax_paid': money(total * TAX_PERCENT / Decimal('100')),
        'gross_tips': gross_tips,
        'assistant_tipout': assistant_tipout,
        'bar_tipout': bar_tipout,
        'total_tipout': money(assistant_tipout + bar_tipout),
        'food_sales': food_sales,
        'alcohol_sales': alcohol_sales,
        'days_worked': days_worked,
        'average_per_day': money(total / days_worked) if days_worked else Decimal('0.00'),
        'highest_day': {'date': highest_day[0], 'total': highest_day[1]} if highest_day else None,
        'lowest_day': {'date': lowest_day[0], 'total': lowest_day[1]} if lowest_day else None,
    }


def _month_groups(entries):
    groups = {}
    for entry in entries:
        month_start = entry.service_date.replace(day=1)
        groups.setdefault(month_start, []).append(entry)

    grouped_months = []
    for month_start, month_entries in sorted(groups.items(), reverse=True):
        grouped_months.append({
            'month': month_start,
            'month_value': _month_value(month_start),
            'entries': sorted(month_entries, key=lambda entry: entry.service_date, reverse=True),
            'stats': _stats_for_entries(month_entries),
        })
    return grouped_months


@login_required
def dashboard(request):
    if request.method == 'POST':
        form = TipEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.server = request.user
            entry.save()
            messages.success(request, 'Shift saved.')
            return redirect('dashboard')
    else:
        form = TipEntryForm()

    paycheck = current_paycheck_window()
    entries = TipEntry.objects.filter(server=request.user)
    paycheck_entries = entries.filter(
        service_date__gte=paycheck['period_start'],
        service_date__lte=paycheck['period_end'],
    )
    recent_entries = entries[:12]

    context = {
        'form': form,
        'entries': recent_entries,
        'paycheck': paycheck,
        'paycheck_entries': paycheck_entries,
        'paycheck_total': _sum_net_tips(paycheck_entries),
        'all_time_total': _sum_net_tips(entries),
    }
    return render(request, 'tips/dashboard.html', context)


@login_required
def paycheck_history(request):
    selected_range = _history_range(request)
    entries = TipEntry.objects.filter(server=request.user)

    if selected_range['start_date']:
        entries = entries.filter(service_date__gte=selected_range['start_date'])
    if selected_range['end_date']:
        entries = entries.filter(service_date__lte=selected_range['end_date'])

    entries = list(entries)
    all_entries = list(TipEntry.objects.filter(server=request.user))
    today = timezone.localdate()

    context = {
        'selected_range': selected_range,
        'entries': entries,
        'stats': _stats_for_entries(entries),
        'month_groups': _month_groups(all_entries if selected_range['selected_view'] == 'all_time' else entries),
        'week_value': request.GET.get('week') or _week_value(today),
        'month_value': request.GET.get('month') or _month_value(today),
        'custom_start': selected_range['start_date'] or today,
        'custom_end': selected_range['end_date'] or today,
    }
    return render(request, 'tips/paychecks.html', context)


def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created.')
            return redirect('dashboard')
    else:
        form = SignUpForm()

    return render(request, 'registration/signup.html', {'form': form})


@login_required
@require_POST
def delete_entry(request, entry_id):
    entry = get_object_or_404(TipEntry, id=entry_id, server=request.user)
    entry.delete()
    messages.error(request, 'Shift deleted.')
    return redirect('dashboard')
