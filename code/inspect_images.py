import csv
import os

with open('dataset/images.csv', mode='r', encoding='utf-8') as f:
    images = list(csv.DictReader(f))

with open('dataset/financial_events.csv', mode='r', encoding='utf-8') as f:
    events = list(csv.DictReader(f))

events_by_id = {e['event_id']: e for e in events}

print(f"Total images: {len(images)}")
print(f"Total events: {len(events)}")

for img in images:
    eid = img['related_event_id']
    ev = events_by_id.get(eid)
    if ev:
        print(f"Image {img['image_id']} -> Event {eid} (User {img['user_id']}, Request {img['request_id']}): type={ev['event_type']}, desc='{ev['description']}', amount='{ev['amount']}', currency={ev['currency']}, status={ev['status']}")
    else:
        print(f"Image {img['image_id']} -> Event {eid} NOT FOUND")
