import sys
sys.path.insert(0, 'code')
from data_loader import DataLoader
from simulator import FinancialSimulator, parse_date, format_date, add_days
from datetime import timedelta

loader = DataLoader('dataset')
sim = FinancialSimulator(loader)

# Debug specific requests
for rid, expected_safe in [
    ('request_16', 122500.0),
    ('request_17', 243849.58),
    ('request_25', 1425000.0),
    ('request_13', 433.4),
    ('request_22', 475.46),
]:
    req = next(r for r in loader.sample_requests if r['request_id']==rid)
    uid = req['user_id']
    req_date = req['request_date']
    req_amt = req['requested_amount']
    prof = loader.profiles[uid]

    print(f'=== {rid} ({uid}) ===')
    print(f'  balance: {prof["current_available_balance"]}')
    print(f'  min_bal: {prof["minimum_balance_to_keep"]}')
    print(f'  home_curr: {prof["home_currency"]}')
    print(f'  requested: {req_amt}, expected safe: {expected_safe}')

    _, base_headroom, _ = sim.simulate_balance(uid, req_date)
    print(f'  base headroom (no payment): {base_headroom:.2f}')

    is_safe, h, _ = sim.simulate_balance(uid, req_date, additional_outflows=[(req_date, req_amt)])
    print(f'  safe with full payment: {is_safe}, headroom: {h:.2f}')
    
    is_safe2, h2, _ = sim.simulate_balance(uid, req_date, additional_outflows=[(req_date, expected_safe)])
    print(f'  safe with expected safe amt {expected_safe}: {is_safe2}, headroom: {h2:.2f}')

    safe_amt = sim.compute_amount_safe_to_pay(uid, req_date, req_amt)
    print(f'  computed safe_amt: {safe_amt}')

    timeline = sim.generate_timeline(uid, req_date)
    req_d = parse_date(req_date)
    print('  Timeline (non-zero days):')
    for offset in range(91):
        d = req_d + timedelta(days=offset)
        v = timeline.get(d, 0)
        if abs(v) > 0.01:
            print(f'    {d}: {v:+.2f}')
    print()
