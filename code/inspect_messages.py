import csv

with open('dataset/messages.csv', mode='r', encoding='utf-8') as f:
    msgs = list(csv.DictReader(f))

print(f"Total messages: {len(msgs)}")
sources = set(m['source_type'] for m in msgs)
print("Source types:", sources)

for i, m in enumerate(msgs):
    print(f"[{i+1}] ID={m['message_id']}, Source={m['source_type']}, User={m['user_id']}, Req={m['request_id']}, Event={m['related_event_id']}, Date={m['sent_at']}")
    print(f"    Text: {m['message_text']}\n")
