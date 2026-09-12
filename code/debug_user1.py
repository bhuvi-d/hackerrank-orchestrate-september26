import sys, os
from collections import defaultdict
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader

loader = DataLoader('dataset')
u1_events = loader.events_by_user['user_01']

print("All user_01 events:")
for e in u1_events:
    print(f"  {e['event_id']}: date={e['event_date']}, set_date={e['settlement_date']}, type={e['event_type']}, cat={e['category']}, dir={e['direction']}, amt={e['amount']}, stat={e['status']}, flex={e['flexibility']}, desc='{e['description']}'")
