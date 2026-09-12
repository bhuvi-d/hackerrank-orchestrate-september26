import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader

loader = DataLoader('dataset')

def parse_date(s):
    return datetime.strptime(s, '%Y-%m-%d').date()

def format_date(d):
    return d.strftime('%Y-%m-%d')

for req in loader.sample_requests[:10]:
    uid = req['user_id']
    prof = loader.profiles[uid]
    req_d = parse_date(req['request_date'])
    events = loader.events_by_user[uid]
    home_curr = prof['home_currency']
    min_bal = prof['minimum_balance_to_keep']
    start_bal = prof['current_available_balance']
    
    # Check messages for salary / rent
    salary_update = loader.msg_parser.extract_salary_updates(uid, req['request_date'])
    rent_mult = loader.msg_parser.extract_rent_updates(uid, req['request_date'])
    
    print(f"\n--- {req['request_id']} User {uid} ({home_curr}) ReqDate={req['request_date']} Target SafeAmt={req['amount_safe_to_pay']} ---")
    print(f"StartBal: {start_bal}, MinBal: {min_bal}")
    print(f"SalaryUpdate: {salary_update}, RentMult: {rent_mult}")
