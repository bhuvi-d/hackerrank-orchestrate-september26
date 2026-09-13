"""
Financial State Simulator and Cash Flow Projection Engine.
Implements the 90-day forward cash ledger, headroom calculation, and earliest date finding.
"""

import os
import calendar
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple, Set

from data_loader import DataLoader


def parse_date(s: Optional[str]) -> Optional[datetime.date]:
    if not s or not s.strip():
        return None
    try:
        return datetime.strptime(s.strip()[:10], '%Y-%m-%d').date()
    except Exception:
        return None


def format_date(d: datetime.date) -> str:
    return d.strftime('%Y-%m-%d')


def add_days(d: datetime.date, days: int) -> datetime.date:
    return d + timedelta(days=days)


def add_months(d: datetime.date, months: int) -> datetime.date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day).date()


class FinancialSimulator:
    """
    Simulates user cash flow trajectories over 90 days following request_date.
    """
    def __init__(self, data_loader: DataLoader):
        self.loader = data_loader

    def build_recurring_streams(self, user_id: str, request_date_str: str) -> List[Dict[str, Any]]:
        req_date = parse_date(request_date_str)
        user_events = self.loader.events_by_user.get(user_id, [])
        prof = self.loader.profiles[user_id]
        home_curr = prof['home_currency']
        
        salary_update = self.loader.msg_parser.extract_salary_updates(user_id, request_date_str)
        rent_mult = self.loader.msg_parser.extract_rent_updates(user_id, request_date_str)

        # Check if salary was declared ended
        has_final_salary = any('Final employer payroll' in e['description'] for e in user_events if e['status'] == 'settled' and (parse_date(e['settlement_date'] or e['event_date']) or req_date) <= req_date)
        salary_ended = salary_update.get('seasonal_ended') or has_final_salary

        image_eids = getattr(self.loader, 'image_event_ids', set())

        # Filter historical events: only settled/scheduled/pending on or before request_date
        historical_events = []
        for e in user_events:
            if e['status'] not in ('settled', 'scheduled', 'pending'):
                continue
            s_date = parse_date(e['settlement_date'] or e['event_date'])
            if not s_date or s_date > req_date:
                continue
            # Exclude non-cash unrealized investments
            if e['status'] == 'unrealized' or e['event_type'] == 'non_cash':
                continue
            # Exclude one-off credits like prizes, lotteries, windfalls
            if e['category'] in ('windfall', 'lottery', 'investment', 'bonus') and e['direction'] == 'credit':
                continue
            # Exclude one-off arrears or promotion adjustments from recurring baseline
            desc_l = e['description'].lower()
            if 'arrears' in desc_l or 'promotion' in desc_l:
                continue
            historical_events.append((s_date, e))

        grouped = defaultdict(list)
        for s_date, e in historical_events:
            key = (e['category'], e['direction'])
            grouped[key].append((s_date, e))

        streams = []
        for (cat, direction), ev_list in grouped.items():
            ev_list.sort(key=lambda x: x[0])
            dates = [x[0] for x in ev_list]
            events = [x[1] for x in ev_list]
            
            if cat == 'salary' and salary_ended:
                continue

            if len(dates) >= 2 or cat == 'salary':
                intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
                avg_interval = sum(intervals) / len(intervals) if intervals else 30
                
                is_monthly = False
                interval_days = None

                if cat in ('rent', 'housing', 'utilities', 'debt_repayment', 'insurance', 
                           'education', 'healthcare', 'family_support', 'music_subscription', 
                           'delivery_membership', 'cloud_storage', 'streaming', 'gym'):
                    is_monthly = True
                elif cat == 'salary':
                    if intervals and sum(5 <= inv <= 9 for inv in intervals) >= len(intervals) * 0.6:
                        is_monthly = False
                        interval_days = 7
                    elif intervals and sum(12 <= inv <= 16 for inv in intervals) >= len(intervals) * 0.6:
                        is_monthly = False
                        interval_days = 14
                    else:
                        is_monthly = True
                else:
                    if any(25 <= inv <= 35 for inv in intervals):
                        is_monthly = True
                    elif intervals:
                        recent_inv = intervals[-1]
                        if 5 <= recent_inv <= 8:
                            interval_days = 7
                        elif 9 <= recent_inv <= 11:
                            interval_days = 10
                        elif 12 <= recent_inv <= 16:
                            interval_days = 14
                        elif 19 <= recent_inv <= 24:
                            interval_days = 21
                        else:
                            interval_days = round(avg_interval) if avg_interval > 0 else 7
                    else:
                        is_monthly = True

                # Representative amount: median of past non-image events
                non_image_events = [e for e in events if e['event_id'] not in image_eids]
                ref_events = non_image_events if non_image_events else events
                last_event = ref_events[-1]
                
                recent_events = ref_events[-12:] if len(ref_events) > 12 else ref_events
                raw_amounts = []
                for ev in recent_events:
                    a = ev['amount']
                    if ev['currency'] != home_curr:
                        a = self.loader.fx.convert(a, request_date_str, ev['currency'], home_curr)
                    raw_amounts.append(a)
                
                if raw_amounts:
                    raw_amounts.sort()
                    n = len(raw_amounts)
                    median_amt = (raw_amounts[n//2 - 1] + raw_amounts[n//2]) / 2.0 if n % 2 == 0 else raw_amounts[n//2]
                    latest_amt = median_amt
                else:
                    latest_amt = last_event['amount']
                    if last_event['currency'] != home_curr:
                        latest_amt = self.loader.fx.convert(latest_amt, request_date_str, last_event['currency'], home_curr)

                # Salary overrides from messages
                if cat == 'salary':
                    if salary_update['confirmed_salary_amount'] is not None:
                        amt = salary_update['confirmed_salary_amount']
                        if salary_update['confirmed_salary_currency'] and salary_update['confirmed_salary_currency'] != home_curr:
                            amt = self.loader.fx.convert(amt, request_date_str, salary_update['confirmed_salary_currency'], home_curr)
                        latest_amt = amt
                    else:
                        latest_amt = last_event['amount']
                        if last_event['currency'] != home_curr:
                            latest_amt = self.loader.fx.convert(latest_amt, request_date_str, last_event['currency'], home_curr)

                # Rent multipliers
                if cat in ('rent', 'housing') and rent_mult is not None:
                    latest_amt *= rent_mult

                streams.append({
                    'category': cat,
                    'direction': direction,
                    'is_monthly': is_monthly,
                    'interval_days': interval_days,
                    'day_of_month': dates[-1].day if is_monthly else None,
                    'last_date': parse_date(last_event['settlement_date'] or last_event['event_date']),
                    'amount': latest_amt,
                    'currency': home_curr,
                    'flexibility': last_event.get('flexibility', 'fixed'),
                    'minimum_allowed_amount': last_event.get('minimum_allowed_amount'),
                    'last_event_id': last_event['event_id'],
                    'description': last_event['description']
                })
        
        return streams

    def generate_timeline(self, user_id: str, request_date_str: str, 
                          spending_changes: Optional[List[Dict[str, Any]]] = None) -> Dict[datetime.date, float]:
        req_date = parse_date(request_date_str)
        end_date = add_days(req_date, 90)
        daily_delta = defaultdict(float)
        
        prof = self.loader.profiles[user_id]
        home_curr = prof['home_currency']
        salary_update = self.loader.msg_parser.extract_salary_updates(user_id, request_date_str)
        
        # Collect already-scheduled / pending events in the 90-day window
        scheduled_by_cat: Dict[Tuple[str, str], Set[datetime.date]] = defaultdict(set)

        for e in self.loader.events_by_user.get(user_id, []):
            s_date = parse_date(e['settlement_date'] or e['event_date'])
            if not s_date or s_date < req_date or s_date > end_date:
                continue
            
            if e['status'] == 'pending' and e['direction'] == 'debit':
                amt = e['amount']
                if e['currency'] != home_curr:
                    amt = self.loader.fx.convert(amt, format_date(s_date), e['currency'], home_curr)
                daily_delta[s_date] -= amt
                scheduled_by_cat[(e['category'], e['direction'])].add(s_date)
            elif e['status'] == 'scheduled':
                amt = e['amount']
                if e['currency'] != home_curr:
                    amt = self.loader.fx.convert(amt, format_date(s_date), e['currency'], home_curr)
                if e['direction'] == 'debit':
                    daily_delta[s_date] -= amt
                elif e['direction'] == 'credit':
                    daily_delta[s_date] += amt
                scheduled_by_cat[(e['category'], e['direction'])].add(s_date)

        # One-off salary adjustment if present
        if salary_update['one_off_adjustment'] > 0 and salary_update['confirmed_salary_date']:
            s_date = parse_date(salary_update['confirmed_salary_date'])
            if req_date <= s_date <= end_date:
                daily_delta[s_date] += salary_update['one_off_adjustment']

        # Recurring streams
        streams = self.build_recurring_streams(user_id, request_date_str)
        for s in streams:
            amt = s['amount']
            direction = s['direction']
            
            if spending_changes:
                for sc in spending_changes:
                    if sc['event_id'] == s['last_event_id']:
                        if sc['action'] == 'stop':
                            amt = 0.0
                        elif sc['action'] == 'reduce_to':
                            amt = sc['new_amount']

            if amt == 0:
                continue

            cat_key = (s['category'], direction)

            curr_d = s['last_date']
            while curr_d <= end_date:
                if s['is_monthly']:
                    curr_d = add_months(curr_d, 1)
                else:
                    curr_d = add_days(curr_d, s['interval_days'] or 7)
                
                if req_date <= curr_d <= end_date:
                    # Skip days already covered by explicit scheduled/pending events within +-3 days
                    if any(abs((curr_d - sd).days) <= 3 for sd in scheduled_by_cat.get(cat_key, set())):
                        continue
                    if direction == 'credit':
                        daily_delta[curr_d] += amt
                    else:
                        daily_delta[curr_d] -= amt

        return daily_delta

    def simulate_balance(self, user_id: str, request_date_str: str,
                         additional_outflows: Optional[List[Tuple[str, float]]] = None,
                         spending_changes: Optional[List[Dict[str, Any]]] = None) -> Tuple[bool, float, Dict[datetime.date, float]]:
        prof = self.loader.profiles[user_id]
        min_bal = prof['minimum_balance_to_keep']
        curr_bal = prof['current_available_balance']
        
        req_date = parse_date(request_date_str)
        daily_delta = self.generate_timeline(user_id, request_date_str, spending_changes)
        
        if additional_outflows:
            for d_str, amt in additional_outflows:
                d = parse_date(d_str)
                if d:
                    daily_delta[d] -= amt
        
        balance_curve = {}
        running_bal = curr_bal
        min_headroom = float('inf')
        is_safe = True
        
        for day_offset in range(91):
            d = add_days(req_date, day_offset)
            running_bal += daily_delta[d]
            headroom = running_bal - min_bal
            balance_curve[d] = running_bal
            if headroom < min_headroom:
                min_headroom = headroom
            if running_bal < min_bal:
                is_safe = False

        return is_safe, min_headroom, balance_curve

    def compute_amount_safe_to_pay(self, user_id: str, request_date_str: str, requested_amount: float) -> float:
        """
        Binary search: find the largest payment P on request_date such that the balance
        never falls below min_bal for any day in [request_date, request_date+90].
        Returns the safe amount, capped at requested_amount.
        """
        # First check: what is the headroom without any payment?
        _, base_headroom, _ = self.simulate_balance(user_id, request_date_str)
        # If even without payment the balance dips below min_bal, safe_amt = 0
        if base_headroom < 0:
            return 0.0

        # Cap: we can't pay more than the headroom (since we pay on day 0, it directly reduces balance)
        # Binary search between 0 and min(requested_amount, base_headroom)
        lo = 0.0
        hi = min(requested_amount, base_headroom)
        
        # Verify hi is actually safe
        is_safe, _, _ = self.simulate_balance(user_id, request_date_str, additional_outflows=[(request_date_str, hi)])
        if not is_safe:
            # Binary search
            lo = 0.0
        else:
            return round(hi, 2)

        # Binary search for max safe amount
        for _ in range(40):
            mid = (lo + hi) / 2.0
            is_safe, _, _ = self.simulate_balance(user_id, request_date_str, additional_outflows=[(request_date_str, mid)])
            if is_safe:
                lo = mid
            else:
                hi = mid
        
        result = max(0.0, lo)
        return round(result, 2)

    def compute_earliest_date_for_full_payment(self, user_id: str, request_date_str: str, requested_amount: float) -> str:
        req_date = parse_date(request_date_str)
        for offset in range(91):
            cand_date = add_days(req_date, offset)
            cand_date_str = format_date(cand_date)
            is_safe, _, _ = self.simulate_balance(user_id, request_date_str, additional_outflows=[(cand_date_str, requested_amount)])
            if is_safe:
                return cand_date_str
        return ""
