import sys, os
from collections import defaultdict
sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader

loader = DataLoader('dataset')

# Check user_01 to user_05 categories and frequencies
for uid in ['user_01', 'user_02', 'user_03', 'user_04', 'user_05']:
    events = loader.events_by_user[uid]
    cat_events = defaultdict(list)
    for e in events:
        cat_events[(e['category'], e['event_type'], e['direction'])].append(e)
    
    print(f"\nUser {uid} event categories:")
    for (cat, etype, edir), ev_list in cat_events.items():
        ev_list.sort(key=lambda x: x['settlement_date'])
        dates = [e['settlement_date'] for e in ev_list]
        amounts = [e['amount'] for e in ev_list]
        statuses = set(e['status'] for e in ev_list)
        flexes = set(e['flexibility'] for e in ev_list)
        print(f"  Cat '{cat}' ({etype}, {edir}, len={len(ev_list)}): flex={flexes}, stats={statuses}, last_3_dates={dates[-3:]}, last_3_amts={amounts[-3:]}")
