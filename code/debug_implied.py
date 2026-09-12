"""
Analyze the exact bills before payday across all 25 sample requests.
"""

import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader
from simulator import parse_date, format_date

loader = DataLoader('dataset')

print(f"{'Req ID':<12} | {'StartBal - MinBal':<20} | {'Target SafeAmt':<15} | {'Implied Outflows':<20}")
print("-" * 75)

for req in loader.sample_requests:
    uid = req['user_id']
    prof = loader.profiles[uid]
    start_bal = prof['current_available_balance']
    min_bal = prof['minimum_balance_to_keep']
    headroom = start_bal - min_bal
    target_safe = req['amount_safe_to_pay']
    implied_outflow = headroom - target_safe
    print(f"{req['request_id']:<12} | {headroom:<20.2f} | {target_safe:<15.2f} | {implied_outflow:<20.2f}")
