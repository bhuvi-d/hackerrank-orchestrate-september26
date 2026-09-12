"""
Test simulation engine and compare amount_safe_to_pay on all 25 sample requests.
"""

import sys, os
from datetime import datetime, timedelta
from collections import defaultdict
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader

loader = DataLoader('dataset')

def parse_date(s):
    return datetime.strptime(s, '%Y-%m-%d').date()

def format_date(d):
    return d.strftime('%Y-%m-%d')

def add_months(sourcedate, months):
    import calendar
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day).date()

for req in loader.sample_requests:
    uid = req['user_id']
    prof = loader.profiles[uid]
    req_date = parse_date(req['request_date'])
    events = loader.events_by_user[uid]
    start_bal = prof['current_available_balance']
    min_bal = prof['minimum_balance_to_keep']
    home_curr = prof['home_currency']
    
    # Message updates
    salary_update = loader.msg_parser.extract_salary_updates(uid, req['request_date'])
    rent_mult = loader.msg_parser.extract_rent_updates(uid, req['request_date'])
    
    # Group past settled events by category/description to identify recurring rules
    past_events = [e for e in events if parse_date(e['settlement_date']) <= req_date and e['status'] == 'settled']
    future_events = [e for e in events if parse_date(e['settlement_date']) > req_date and e['status'] in ('scheduled', 'pending')]
    
    # Let's inspect the target vs profile
    print(f"Sample {req['request_id']} ({uid}): ReqAmt={req['requested_amount']}, TargetSafeAmt={req['amount_safe_to_pay']}, StartBal={start_bal}, MinBal={min_bal}, Headroom={start_bal - min_bal}")
