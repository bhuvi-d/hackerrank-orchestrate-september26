import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader

loader = DataLoader('dataset')

for s in loader.sample_requests[:5]:
    uid = s['user_id']
    prof = loader.profiles[uid]
    req_date = s['request_date']
    user_events = loader.events_by_user[uid]
    
    print(f"\n==========================================")
    print(f"Sample {s['request_id']}: User {uid}, ReqDate={req_date}, ReqAmt={s['requested_amount']}")
    print(f"Profile: CurrBal={prof['current_available_balance']}, MinBal={prof['minimum_balance_to_keep']}, Currency={prof['home_currency']}")
    print(f"Methods: {prof['payment_methods_user_will_consider']}, MaxMonths={prof['max_installment_months']}")
    print(f"Target GT: SafeAmt={s['amount_safe_to_pay']}, Status={s['affordability_status']}, Method={s['recommended_payment_method']}")
    print(f"Target Plan: {s['payment_plan']}, EarliestDate={s['earliest_date_for_full_payment']}, Changes={s['spending_changes_needed']}")
    
    # Check events after req_date or scheduled/pending
    future_events = [e for e in user_events if e['settlement_date'] >= req_date]
    print(f"Future events count: {len(future_events)}")
    for e in future_events[:10]:
        print(f"  {e['event_id']} ({e['settlement_date']}): type={e['event_type']}, dir={e['direction']}, amt={e['amount']} {e['currency']}, status={e['status']}, cat={e['category']}, flex={e['flexibility']}")
