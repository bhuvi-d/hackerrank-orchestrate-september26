import sys
sys.path.insert(0, 'code')
from data_loader import DataLoader
from simulator import FinancialSimulator, parse_date
from datetime import timedelta

loader = DataLoader('dataset')
sim = FinancialSimulator(loader)

uid = 'user_21'
req_date = '2026-04-03'
req_amt = 1574.40

prof = loader.profiles[uid]
print(f'Balance: {prof["current_available_balance"]}')
print(f'Min bal: {prof["minimum_balance_to_keep"]}')
print(f'Home curr: {prof["home_currency"]}')
print(f'Allowed methods: {prof["payment_methods_user_will_consider"]}')
print(f'Stoppable cats: {prof["expense_categories_user_is_willing_to_stop"]}')
print(f'Reducible cats: {prof["expense_categories_user_is_willing_to_reduce"]}')

print(f'\nRequested: {req_amt}')
_, base_headroom, _ = sim.simulate_balance(uid, req_date)
print(f'Base headroom (no payment): {base_headroom:.2f}')

is_safe, h, _ = sim.simulate_balance(uid, req_date, additional_outflows=[(req_date, req_amt)])
print(f'Safe with full payment: {is_safe}, headroom: {h:.2f}')

safe_amt = sim.compute_amount_safe_to_pay(uid, req_date, req_amt)
print(f'Computed safe_amt: {safe_amt}')
print(f'Expected safe_amt: 1543.35')

# Check the timeline
req_d = parse_date(req_date)
timeline = sim.generate_timeline(uid, req_date)
print('\nTimeline (non-zero days):')
running_bal = prof['current_available_balance']
for offset in range(91):
    d = req_d + timedelta(days=offset)
    v = timeline.get(d, 0)
    if abs(v) > 0.01:
        running_bal += v
        print(f'  {d}: delta={v:+.2f}, balance={running_bal:.2f}, headroom={running_bal - prof["minimum_balance_to_keep"]:.2f}')

# Check streams
print('\nStreams:')
streams = sim.build_recurring_streams(uid, req_date)
for s in streams:
    print(f"  {s['category']} {s['direction']} amt={s['amount']:.2f} eid={s['last_event_id']} flex={s['flexibility']}")

# Check stoppable events
print('\nStoppable actions:')
stoppable_cats = prof['expense_categories_user_is_willing_to_stop']
for s in streams:
    if s['category'] in stoppable_cats:
        print(f"  event={s['last_event_id']} cat={s['category']} amt={s['amount']:.2f} flex={s['flexibility']}")
