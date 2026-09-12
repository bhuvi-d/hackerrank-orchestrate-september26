"""
Analyze exact cash flows between request_date and request_date + 90 days.
"""

import sys, os
from datetime import datetime, timedelta
from collections import defaultdict
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader

loader = DataLoader('dataset')

def parse_d(s):
    if not s:
        return None
    return datetime.strptime(s, '%Y-%m-%d').date()

def add_months(d, m):
    import calendar
    month = d.month - 1 + m
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day).date()

for req in loader.sample_requests[:10]:
    uid = req['user_id']
    prof = loader.profiles[uid]
    req_date = parse_d(req['request_date'])
    events = loader.events_by_user[uid]
    start_bal = prof['current_available_balance']
    min_bal = prof['minimum_balance_to_keep']
    home_curr = prof['home_currency']
    
    print(f"\n==========================================")
    print(f"Sample {req['request_id']} ({uid}): ReqDate={req_date}, ReqAmt={req['requested_amount']}, SafeAmt={req['amount_safe_to_pay']}")
    print(f"StartBal={start_bal}, MinBal={min_bal}, StartBuffer={start_bal - min_bal}")
    
    # Check all events around req_date
    for e in events:
        s_date = parse_d(e['settlement_date'] or e['event_date'])
        if s_date and req_date - timedelta(days=35) <= s_date <= req_date + timedelta(days=90):
            print(f"  {e['event_id']} ({s_date}): type={e['event_type']}, cat={e['category']}, dir={e['direction']}, amt={e['amount']} {e['currency']}, stat={e['status']}, flex={e['flexibility']}, desc='{e['description']}'")
