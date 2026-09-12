import sys
sys.path.insert(0, 'code')
from data_loader import DataLoader
from simulator import FinancialSimulator, parse_date
from datetime import timedelta

loader = DataLoader('dataset')
sim = FinancialSimulator(loader)

uid = 'user_17'
req_date = '2026-03-01'

# Look at raw events for user_17
events = loader.events_by_user.get(uid, [])
prof = loader.profiles[uid]
print(f'Balance: {prof["current_available_balance"]}')
print(f'Min bal: {prof["minimum_balance_to_keep"]}')
print(f'Home curr: {prof["home_currency"]}')
print(f'Total events: {len(events)}')

# Show events in the simulation window
from datetime import date
req_d = parse_date(req_date)
end_d = req_d + timedelta(days=90)

print('\nEvents in window:')
for e in sorted(events, key=lambda x: x['event_date']):
    s_date = parse_date(e['settlement_date'] or e['event_date'])
    if s_date and req_d <= s_date <= end_d:
        print(f"  {s_date} [{e['status']}] {e['direction']} {e['amount']} {e['currency']} cat={e['category']} eid={e['event_id']}")

print('\nAll events (for recurrence analysis):')
by_cat = {}
for e in events:
    k = (e['category'], e['direction'])
    by_cat.setdefault(k, []).append(e)

for k, evs in sorted(by_cat.items()):
    dates = sorted([parse_date(e['settlement_date'] or e['event_date']) for e in evs if parse_date(e['settlement_date'] or e['event_date'])])
    statuses = [e['status'] for e in evs]
    print(f'  {k}: {len(evs)} events, statuses={set(statuses)}, dates={dates[:5]}...')

print('\nRecurring streams built:')
streams = sim.build_recurring_streams(uid, req_date)
for s in streams:
    print(f"  {s['category']} {s['direction']} amt={s['amount']:.2f} is_monthly={s['is_monthly']} last_date={s['last_date']} eid={s['last_event_id']}")
