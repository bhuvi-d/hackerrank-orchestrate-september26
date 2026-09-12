import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader
from simulator import FinancialSimulator, parse_date, add_days

loader = DataLoader('dataset')
sim = FinancialSimulator(loader)

print("Investigating headroom and lowest balance point on sample requests:")
for req in loader.sample_requests:
    uid = req['user_id']
    req_d_str = req['request_date']
    is_safe, min_hr, curve = sim.simulate_balance(uid, req_d_str)
    
    # Find day of min headroom
    min_day = min(curve, key=lambda d: curve[d])
    prof = loader.profiles[uid]
    print(f"[{req['request_id']}] GT_Safe={req['amount_safe_to_pay']:<12} | Sim_HR={min_hr:<12.2f} | Diff={min_hr - req['amount_safe_to_pay']:<10.2f} | MinDay={min_day} (Bal={curve[min_day]:.2f}, MinReq={prof['minimum_balance_to_keep']})")
