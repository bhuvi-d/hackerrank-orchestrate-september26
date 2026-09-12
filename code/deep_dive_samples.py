import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader

loader = DataLoader('dataset')

for rid in ['request_02', 'request_03', 'request_05', 'request_11', 'request_17']:
    req = next(r for r in loader.sample_requests if r['request_id'] == rid)
    uid = req['user_id']
    prof = loader.profiles[uid]
    req_date = req['request_date']
    events = loader.events_by_user[uid]
    
    print(f"\n==========================================")
    print(f"Investigating {rid} (User {uid}, ReqDate={req_date}):")
    print(f"Profile: CurrBal={prof['current_available_balance']}, MinBal={prof['minimum_balance_to_keep']}, Currency={prof['home_currency']}")
    print(f"Target SafeAmt: {req['amount_safe_to_pay']}, EarliestDate: {req['earliest_date_for_full_payment']}, Status: {req['affordability_status']}")
    print(f"Target Plan: {req['payment_plan']}, Changes: {req['spending_changes_needed']}")
    print(f"Decision Explanation: {req['decision_explanation']}")
    
    msgs = loader.msg_parser.get_user_messages(uid)
    print("Messages:")
    for m in msgs:
        print(f"  [{m['sent_at']}] {m['message_text']}")
