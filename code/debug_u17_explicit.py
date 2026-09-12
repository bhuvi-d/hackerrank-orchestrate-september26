import sys
sys.path.insert(0, 'code')
from data_loader import DataLoader
from simulator import FinancialSimulator, parse_date
from datetime import timedelta
from collections import defaultdict

loader = DataLoader('dataset')
sim = FinancialSimulator(loader)

# For request_17 user_17, manually compute what the expected safe_amt should be
uid = 'user_17'
req_date = '2026-03-01'
expected_safe = 243849.58

prof = loader.profiles[uid]
curr_bal = prof['current_available_balance']
min_bal = prof['minimum_balance_to_keep']
home_curr = prof['home_currency']

req_d = parse_date(req_date)
end_d = req_d + timedelta(days=90)

print(f'Balance: {curr_bal}, min_bal: {min_bal}')
print(f'Initial headroom: {curr_bal - min_bal}')

# Build timeline ONLY from explicit events (no recurring projections)
daily_delta = defaultdict(float)
events = loader.events_by_user.get(uid, [])
for e in events:
    s_date = parse_date(e['settlement_date'] or e['event_date'])
    if not s_date or s_date < req_d or s_date > end_d:
        continue
    if e['status'] == 'pending' and e['direction'] == 'debit':
        amt = e['amount']
        daily_delta[s_date] -= amt
        print(f'  Pending debit: {s_date} {amt} (eid={e["event_id"]})')
    elif e['status'] == 'scheduled':
        amt = e['amount']
        if e['direction'] == 'debit':
            daily_delta[s_date] -= amt
        elif e['direction'] == 'credit':
            daily_delta[s_date] += amt
        print(f'  Scheduled {e["direction"]}: {s_date} {amt} (eid={e["event_id"]})')

print('\nRunning balance with ONLY explicit events:')
running_bal = curr_bal
min_headroom = float('inf')
for offset in range(91):
    d = req_d + timedelta(days=offset)
    delta = daily_delta.get(d, 0)
    if delta != 0:
        running_bal += delta
    headroom = running_bal - min_bal
    if headroom < min_headroom:
        min_headroom = headroom
    if delta != 0:
        print(f'  {d}: delta={delta:+.2f}, balance={running_bal:.2f}, headroom={headroom:.2f}')

print(f'\nMin headroom with ONLY explicit events: {min_headroom:.2f}')
print(f'Expected safe_amt: {expected_safe}')
print(f'Difference: {min_headroom - expected_safe:.2f}')
