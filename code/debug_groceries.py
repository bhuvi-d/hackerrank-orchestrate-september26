import sys
sys.path.insert(0, 'code')
from data_loader import DataLoader
from simulator import parse_date
from datetime import timedelta

loader = DataLoader('dataset')

# Examine grocery events for user_17
uid = 'user_17'
events = loader.events_by_user.get(uid, [])
grocery_events = [e for e in events if e['category'] == 'groceries']
grocery_events.sort(key=lambda x: x['event_date'])

print('Grocery events for user_17:')
for e in grocery_events:
    img_note = ''
    # Check if this is an image-extracted amount
    img_events = loader.events_by_id
    print(f"  {e['event_date']} [{e['status']}] {e['amount']:.2f} {e['currency']} eid={e['event_id']} flexibility={e['flexibility']}")

# Check which events have image links
print('\nImage map:')
import csv, os
img_map = {}
with open('dataset/images.csv') as f:
    for row in csv.DictReader(f):
        img_map[row['related_event_id'].strip()] = row['image_id'].strip()
        
for eid, imgid in img_map.items():
    e = loader.events_by_id.get(eid, {})
    if e.get('user_id') == uid:
        print(f'  {eid} -> {imgid}, amount={e["amount"]}, category={e["category"]}')

print('\nGrocery amounts histogram:')
amounts = [e['amount'] for e in grocery_events]
amounts.sort()
print(f'  min: {min(amounts):.2f}')
print(f'  max: {max(amounts):.2f}')
print(f'  median: {sorted(amounts)[len(amounts)//2]:.2f}')
print(f'  mean: {sum(amounts)/len(amounts):.2f}')
print(f'  last 5: {amounts[-5:]}')
