import sys, os
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader
from simulator import FinancialSimulator

loader = DataLoader('dataset')
sim = FinancialSimulator(loader)

print(f"{'Req ID':<12} | {'Computed Safe':<15} | {'Target Safe':<15} | {'Diff':<10} | {'Computed Earliest':<18} | {'Target Earliest':<18}")
print("-" * 95)

for req in loader.sample_requests:
    safe_amt = sim.compute_amount_safe_to_pay(req['user_id'], req['request_date'], req['requested_amount'])
    earliest = sim.compute_earliest_date_for_full_payment(req['user_id'], req['request_date'], req['requested_amount'])
    diff = abs(safe_amt - req['amount_safe_to_pay'])
    print(f"{req['request_id']:<12} | {safe_amt:<15} | {req['amount_safe_to_pay']:<15} | {diff:<10.2f} | {earliest:<18} | {req['earliest_date_for_full_payment']:<18}")
