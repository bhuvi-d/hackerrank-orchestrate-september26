import sys, os
from datetime import datetime, timedelta
import calendar
from collections import defaultdict
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader
from simulator import parse_date, format_date

loader = DataLoader('dataset')

for req in loader.sample_requests[:10]:
    uid = req['user_id']
    req_d = parse_date(req['request_date'])
    events = loader.events_by_user[uid]
    prof = loader.profiles[uid]
    headroom = prof['current_available_balance'] - prof['minimum_balance_to_keep']
    target_safe = req['amount_safe_to_pay']
    
    # Identify unique recurring events
    # Find next salary date
    sal_events = [e for e in events if e['category'] == 'salary' or e['event_type'] == 'salary']
    sal_days = [parse_date(e['settlement_date'] or e['event_date']).day for e in sal_events if parse_date(e['settlement_date'] or e['event_date'])]
    sal_day = sal_days[-1] if sal_days else 15
    
    # Find all monthly expenses whose day is between req_d.day and sal_day
    # Let's inspect events
    print(f"\n[{req['request_id']}] {uid} ReqDate={req_d} SalDay={sal_day} Headroom={headroom:.2f} TargetSafe={target_safe:.2f} ImpliedOutflow={headroom - target_safe:.2f}")
    
    # Group by category to find monthly amounts
    cat_amts = defaultdict(list)
    for e in events:
        d = parse_date(e['settlement_date'] or e['event_date'])
        if d and e['status'] == 'settled' and e['direction'] == 'debit':
            cat_amts[(e['category'], e['description'], d.day)].append(e['amount'])
    
    total_window_outflow = 0.0
    for (cat, desc, d_day), amts in cat_amts.items():
        recent_amt = amts[-1]
        # If d_day between req_d.day and sal_day
        if req_d.day <= d_day <= sal_day:
            print(f"    Bill on day {d_day}: {cat} ('{desc}') = {recent_amt}")
            total_window_outflow += recent_amt
    print(f"  Sum of window bills: {total_window_outflow:.2f}")
