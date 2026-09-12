"""
Validation Script for Buy or Wait?
Runs all 25 sample requests from sample_requests.csv and compares predictions against ground truth.
"""

import os
import sys

sys.path.insert(0, os.path.abspath('code'))
from data_loader import DataLoader
from simulator import FinancialSimulator
from decision_engine import DecisionEngine


def run_validation():
    loader = DataLoader('dataset')
    sim = FinancialSimulator(loader)
    engine = DecisionEngine(loader, sim)

    print("=" * 80)
    print("RUNNING VALIDATION AGAINST 25 SAMPLE REQUESTS")
    print("=" * 80)

    total_samples = len(loader.sample_requests)
    status_matches = 0
    method_matches = 0
    plan_matches = 0
    earliest_matches = 0
    changes_matches = 0
    safe_amt_matches = 0

    for req in loader.sample_requests:
        rid = req['request_id']
        pred = engine.evaluate_request(req)
        
        status_ok = pred['affordability_status'] == req['affordability_status']
        method_ok = pred['recommended_payment_method'] == req['recommended_payment_method']
        plan_ok = pred['payment_plan'] == req['payment_plan']
        earliest_ok = pred['earliest_date_for_full_payment'] == req['earliest_date_for_full_payment']
        changes_ok = pred['spending_changes_needed'] == req['spending_changes_needed']
        safe_amt_ok = abs(pred['amount_safe_to_pay'] - req['amount_safe_to_pay']) < 1.0

        if status_ok: status_matches += 1
        if method_ok: method_matches += 1
        if plan_ok: plan_matches += 1
        if earliest_ok: earliest_matches += 1
        if changes_ok: changes_matches += 1
        if safe_amt_ok: safe_amt_matches += 1

        all_ok = status_ok and method_ok and plan_ok and earliest_ok and changes_ok and safe_amt_ok
        status_icon = "PASS" if all_ok else "FAIL"

        print(f"[{status_icon}] {rid} ({req['user_id']}):")
        print(f"    Status:   Pred={pred['affordability_status']} | Target={req['affordability_status']} ({'OK' if status_ok else 'DIFF'})")
        print(f"    Method:   Pred={pred['recommended_payment_method']} | Target={req['recommended_payment_method']} ({'OK' if method_ok else 'DIFF'})")
        print(f"    Plan:     Pred={pred['payment_plan']} | Target={req['payment_plan']} ({'OK' if plan_ok else 'DIFF'})")
        print(f"    Earliest: Pred={pred['earliest_date_for_full_payment']} | Target={req['earliest_date_for_full_payment']} ({'OK' if earliest_ok else 'DIFF'})")
        print(f"    Changes:  Pred={pred['spending_changes_needed']} | Target={req['spending_changes_needed']} ({'OK' if changes_ok else 'DIFF'})")
        print(f"    Safe Amt: Pred={pred['amount_safe_to_pay']} | Target={req['amount_safe_to_pay']} ({'OK' if safe_amt_ok else 'DIFF'})")
        print(f"    Expl:     {pred['decision_explanation']}")
        print("-" * 80)

    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY REPORT")
    print("=" * 80)
    print(f"Total Samples Evaluated: {total_samples}")
    print(f"Affordability Status Matches: {status_matches} / {total_samples} ({status_matches/total_samples*100:.1f}%)")
    print(f"Recommended Method Matches:   {method_matches} / {total_samples} ({method_matches/total_samples*100:.1f}%)")
    print(f"Payment Plan Matches:         {plan_matches} / {total_samples} ({plan_matches/total_samples*100:.1f}%)")
    print(f"Earliest Date Matches:        {earliest_matches} / {total_samples} ({earliest_matches/total_samples*100:.1f}%)")
    print(f"Spending Changes Matches:     {changes_matches} / {total_samples} ({changes_matches/total_samples*100:.1f}%)")
    print(f"Amount Safe to Pay Matches:   {safe_amt_matches} / {total_samples} ({safe_amt_matches/total_samples*100:.1f}%)")
    print("=" * 80)

if __name__ == '__main__':
    run_validation()
