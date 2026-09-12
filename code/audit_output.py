import csv

output = list(csv.DictReader(open('dataset/output.csv', encoding='utf-8')))
requests = {r['request_id']: r for r in csv.DictReader(open('dataset/requests.csv', encoding='utf-8'))}

# Check: for wait, plan date should match earliest_date
mismatch = []
for row in output:
    if row['recommended_payment_method'] == 'wait':
        plan = row['payment_plan']
        earliest = row['earliest_date_for_full_payment']
        if plan != 'none':
            plan_date = plan.split(':')[0]
            if plan_date != earliest:
                mismatch.append((row['request_id'], plan_date, earliest))

print(f'wait plan_date != earliest_date mismatches: {len(mismatch)}')
for m in mismatch[:10]:
    print(' ', m)

# Installment rows: show earliest_date vs request_date
inst_rows = [r for r in output if r['recommended_payment_method'] == 'installments']
print(f'\nInstallment rows: {len(inst_rows)}')
for r in inst_rows[:8]:
    req = requests[r['request_id']]
    print(f"  {r['request_id']}: req_date={req['request_date']} earliest={r['earliest_date_for_full_payment']} plan={r['payment_plan'][:70]}")

# Check spending_changes: all 3-change combos
sc3 = [(r['request_id'], r['spending_changes_needed']) for r in output if r['spending_changes_needed'].count('|') >= 2]
print(f'\n3-change spending changes: {len(sc3)}')
for s in sc3[:5]:
    print(' ', s)

# Count status distribution
from collections import Counter
print('\nStatus distribution:', Counter(r['affordability_status'] for r in output))
print('Method distribution:', Counter(r['recommended_payment_method'] for r in output))
