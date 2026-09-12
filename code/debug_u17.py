import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader

loader = DataLoader('dataset')
u17_events = loader.events_by_user['user_17']

print("All user_17 events from 2026-02-01 onwards:")
for e in u17_events:
    d = e['settlement_date'] or e['event_date']
    if d >= '2026-02-01':
        print(f"  {e['event_id']}: date={d}, type={e['event_type']}, cat={e['category']}, dir={e['direction']}, amt={e['amount']}, stat={e['status']}, desc='{e['description']}'")
