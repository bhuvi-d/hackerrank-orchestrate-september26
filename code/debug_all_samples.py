import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader

loader = DataLoader('dataset')

for req in loader.sample_requests:
    uid = req['user_id']
    prof = loader.profiles[uid]
    req_date = req['request_date']
    opts = loader.payment_options_by_req.get(req['request_id'], [])
    print(f"[{req['request_id']}] user={uid} ({prof['home_currency']}) req_amt={req['requested_amount']} safe_amt={req['amount_safe_to_pay']} status={req['affordability_status']} method={req['recommended_payment_method']} plan='{req['payment_plan']}' earliest='{req['earliest_date_for_full_payment']}' changes='{req['spending_changes_needed']}'")
    for opt in opts:
        print(f"    Opt {opt['payment_option_id']}: method={opt['payment_method']}, amt={opt['payment_amount']}, count={opt['number_of_payments']}, start={opt['first_payment_date']}, freq={opt['payment_frequency_days']}, fee={opt['financing_fee']}, total={opt['total_payable_amount']}")
