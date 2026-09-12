"""
Combinatorial Decision and Plan Optimization Engine for Buy or Wait?
Evaluates all feasible candidate plans, applies lexicographic ranking,
and constructs deterministic grounded explanations.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set

from data_loader import DataLoader
from simulator import FinancialSimulator, parse_date, format_date, add_days


def format_amount(amt: float) -> str:
    """Formats amounts with integer representation if whole number, otherwise 2 decimal places."""
    if amt == int(amt):
        return f"{int(amt)}"
    return f"{amt:.2f}"


def format_currency_amount(curr: str, amt: float) -> str:
    """Formats currency amounts with commas for readability in explanations."""
    if amt == int(amt):
        return f"{curr} {int(amt):,}"
    return f"{curr} {amt:,.2f}"


class DecisionEngine:
    """
    Evaluates requests and selects the optimal recommendation.
    """
    def __init__(self, data_loader: DataLoader, simulator: FinancialSimulator):
        self.loader = data_loader
        self.sim = simulator

    def evaluate_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req_id = request['request_id']
        uid = request['user_id']
        req_date_str = request['request_date']
        req_date = parse_date(req_date_str)
        req_amt = request['requested_amount']
        desired_comp_str = request['desired_completion_date']
        desired_comp_date = parse_date(desired_comp_str)
        allows_partial = request['allows_partial_payment']

        prof = self.loader.profiles[uid]
        home_curr = prof['home_currency']
        min_bal = prof['minimum_balance_to_keep']
        curr_bal = prof['current_available_balance']
        allowed_methods = prof['payment_methods_user_will_consider']
        max_inst_months = prof['max_installment_months']

        # 1. Base calculations
        safe_amt = self.sim.compute_amount_safe_to_pay(uid, req_date_str, req_amt)
        earliest_full_date = self.sim.compute_earliest_date_for_full_payment(uid, req_date_str, req_amt)

        # Compute base min_headroom (without payment) for explanation text
        _, base_headroom, base_curve = self.sim.simulate_balance(uid, req_date_str)

        candidate_plans = []

        # Candidate A: Full Payment Today
        if 'full_payment' in allowed_methods and safe_amt >= req_amt:
            is_safe, min_headroom, _ = self.sim.simulate_balance(
                uid, req_date_str, additional_outflows=[(req_date_str, req_amt)]
            )
            if is_safe:
                plan_str = f"{req_date_str}:{format_amount(req_amt)}"
                # Remaining balance after payment
                remaining = min_headroom + min_bal
                explanation = (
                    f"Pay {format_currency_amount(home_curr, req_amt)} today. "
                    f"This leaves at least {format_currency_amount(home_curr, min_bal)} available over the next 90 days."
                )
                candidate_plans.append({
                    'status': 'affordable_now',
                    'method': 'full_payment',
                    'plan': plan_str,
                    'earliest_date': req_date_str,
                    'spending_changes': 'none',
                    'explanation': explanation,
                    'meets_deadline': True,
                    'num_spending_changes': 0,
                    'total_cost': req_amt,
                    'start_date': req_date_str,
                    'num_payments': 1,
                    'option_id': 'option_00'
                })

        # Candidate B: Seller Installment Options
        seller_options = self.loader.payment_options_by_req.get(req_id, [])
        for opt in seller_options:
            if opt['payment_method'] != 'installments':
                continue
            if 'installments' not in allowed_methods:
                continue
            
            # Check duration against max_installment_months
            n_payments = opt['number_of_payments']
            freq = opt['payment_frequency_days'] or 30
            start_d = parse_date(opt['first_payment_date'])
            total_days = (n_payments - 1) * freq
            duration_months = total_days / 30.0
            
            if max_inst_months is not None and duration_months > max_inst_months:
                continue

            # Build payment schedule
            outflows = []
            plan_tokens = []
            final_payment_date = start_d
            for j in range(n_payments):
                p_date = add_days(start_d, j * freq)
                p_date_str = format_date(p_date)
                p_amt = opt['payment_amount']
                outflows.append((p_date_str, p_amt))
                plan_tokens.append(f"{p_date_str}:{format_amount(p_amt)}")
                final_payment_date = p_date

            is_safe, min_headroom, _ = self.sim.simulate_balance(uid, req_date_str, additional_outflows=outflows)
            if is_safe:
                meets_deadline = final_payment_date <= desired_comp_date if desired_comp_date else True
                plan_str = "|".join(plan_tokens)
                explanation = (
                    f"Use {n_payments} installments of {format_currency_amount(home_curr, opt['payment_amount'])}, "
                    f"starting {start_d.strftime('%d %B %Y').lstrip('0')}. "
                    f"This leaves at least {format_currency_amount(home_curr, min_bal)} available."
                )
                # earliest_date for installments: the date the full amount is completed (last installment date)
                inst_earliest = earliest_full_date if earliest_full_date else format_date(final_payment_date)
                candidate_plans.append({
                    'status': 'affordable_with_plan',
                    'method': 'installments',
                    'plan': plan_str,
                    'earliest_date': inst_earliest,
                    'spending_changes': 'none',
                    'explanation': explanation,
                    'meets_deadline': meets_deadline,
                    'num_spending_changes': 0,
                    'total_cost': opt['total_payable_amount'],
                    'start_date': opt['first_payment_date'],
                    'num_payments': n_payments,
                    'option_id': opt['payment_option_id']
                })

        # Candidate C: Partial Payment
        if (allows_partial and 'partial_payment' in allowed_methods and 
            0 < safe_amt < req_amt and earliest_full_date):
            earliest_d = parse_date(earliest_full_date)
            meets_deadline = earliest_d <= desired_comp_date if desired_comp_date else True
            rem_amt = req_amt - safe_amt
            
            outflows = [(req_date_str, safe_amt), (earliest_full_date, rem_amt)]
            is_safe, _, _ = self.sim.simulate_balance(uid, req_date_str, additional_outflows=outflows)
            if is_safe and earliest_full_date > req_date_str:
                plan_str = f"{req_date_str}:{format_amount(safe_amt)}|{earliest_full_date}:{format_amount(rem_amt)}"
                explanation = (
                    f"Pay {format_currency_amount(home_curr, safe_amt)} today and the remaining "
                    f"{format_currency_amount(home_curr, rem_amt)} on "
                    f"{earliest_d.strftime('%d %B %Y').lstrip('0')}. "
                    f"This completes the full request and keeps the "
                    f"{format_currency_amount(home_curr, min_bal)} minimum protected."
                )
                candidate_plans.append({
                    'status': 'affordable_with_plan',
                    'method': 'partial_payment',
                    'plan': plan_str,
                    'earliest_date': earliest_full_date,
                    'spending_changes': 'none',
                    'explanation': explanation,
                    'meets_deadline': meets_deadline,
                    'num_spending_changes': 0,
                    'total_cost': req_amt,
                    'start_date': req_date_str,
                    'num_payments': 2,
                    'option_id': 'option_partial'
                })

        # Candidate D: Spending Changes
        reducible_cats = prof['expense_categories_user_is_willing_to_reduce']
        stoppable_cats = prof['expense_categories_user_is_willing_to_stop']
        streams = self.sim.build_recurring_streams(uid, req_date_str)
        
        flexible_actions = []
        for s in streams:
            cat = s['category']
            eid = s['last_event_id']
            flex = s['flexibility']
            desc = s['description']
            
            if cat in stoppable_cats and (flex in ('stoppable', 'reducible_or_stoppable')):
                flexible_actions.append({
                    'action': 'stop',
                    'event_id': eid,
                    'desc': desc,
                    'category': cat,
                    'new_amount': 0.0,
                    'savings': s['amount'],
                    'token': f"stop:{eid}"
                })
            elif cat in reducible_cats and (flex in ('reducible', 'reducible_or_stoppable')):
                min_allowed = s['minimum_allowed_amount'] or (s['amount'] * 0.5)
                savings = s['amount'] - min_allowed
                if savings > 0:
                    flexible_actions.append({
                        'action': 'reduce_to',
                        'event_id': eid,
                        'desc': desc,
                        'category': cat,
                        'new_amount': min_allowed,
                        'savings': savings,
                        'token': f"reduce_to:{eid}:{format_amount(min_allowed)}"
                    })

        # Test spending change combinations (1, 2, or 3 changes)
        if flexible_actions and 'full_payment' in allowed_methods:
            # Single spending changes
            for act in flexible_actions:
                spending_changes = [{'event_id': act['event_id'], 'action': act['action'], 'new_amount': act['new_amount']}]
                is_safe, min_headroom, _ = self.sim.simulate_balance(
                    uid, req_date_str, additional_outflows=[(req_date_str, req_amt)], spending_changes=spending_changes
                )
                if is_safe:
                    plan_str = f"{req_date_str}:{format_amount(req_amt)}"
                    changes_str = act['token']
                    action_desc = (
                        f"Stop the {act['desc']}" if act['action'] == 'stop' 
                        else f"Reduce the {act['desc']} to {format_currency_amount(home_curr, act['new_amount'])}"
                    )
                    explanation = (
                        f"{action_desc}, then pay {format_currency_amount(home_curr, req_amt)} today. "
                        f"This leaves at least {format_currency_amount(home_curr, min_bal)} available."
                    )
                    # Recalculate safe_amt with spending changes applied for early_date
                    sc_earliest = self.sim.compute_earliest_date_for_full_payment(uid, req_date_str, req_amt)
                    candidate_plans.append({
                        'status': 'affordable_with_plan',
                        'method': 'full_payment',
                        'plan': plan_str,
                        'earliest_date': sc_earliest or req_date_str,
                        'spending_changes': changes_str,
                        'explanation': explanation,
                        'meets_deadline': True,
                        'num_spending_changes': 1,
                        'total_cost': req_amt,
                        'start_date': req_date_str,
                        'num_payments': 1,
                        'option_id': 'option_spending_1'
                    })

            # Pairs of actions
            for i in range(len(flexible_actions)):
                for j in range(i+1, len(flexible_actions)):
                    act1 = flexible_actions[i]
                    act2 = flexible_actions[j]
                    if act1['event_id'] == act2['event_id']:
                        continue
                    spending_changes = [
                        {'event_id': act1['event_id'], 'action': act1['action'], 'new_amount': act1['new_amount']},
                        {'event_id': act2['event_id'], 'action': act2['action'], 'new_amount': act2['new_amount']}
                    ]
                    is_safe, min_headroom, _ = self.sim.simulate_balance(
                        uid, req_date_str, additional_outflows=[(req_date_str, req_amt)], spending_changes=spending_changes
                    )
                    if is_safe:
                        plan_str = f"{req_date_str}:{format_amount(req_amt)}"
                        changes_str = f"{act1['token']}|{act2['token']}"
                        desc1 = (
                            f"Stop the {act1['desc']}" if act1['action'] == 'stop' 
                            else f"Reduce the {act1['desc']} to {format_currency_amount(home_curr, act1['new_amount'])}"
                        )
                        desc2_part = (
                            f"stop the {act2['desc']}" if act2['action'] == 'stop' 
                            else f"reduce the {act2['desc']} to {format_currency_amount(home_curr, act2['new_amount'])}"
                        )
                        explanation = (
                            f"{desc1} and {desc2_part}, then pay {format_currency_amount(home_curr, req_amt)} today. "
                            f"This leaves at least {format_currency_amount(home_curr, min_bal)} available."
                        )
                        sc_earliest = self.sim.compute_earliest_date_for_full_payment(uid, req_date_str, req_amt)
                        candidate_plans.append({
                            'status': 'affordable_with_plan',
                            'method': 'full_payment',
                            'plan': plan_str,
                            'earliest_date': sc_earliest or req_date_str,
                            'spending_changes': changes_str,
                            'explanation': explanation,
                            'meets_deadline': True,
                            'num_spending_changes': 2,
                            'total_cost': req_amt,
                            'start_date': req_date_str,
                            'num_payments': 1,
                            'option_id': 'option_spending_2'
                        })

            # Triples of actions (up to 3 spending changes per spec)
            for i in range(len(flexible_actions)):
                for j in range(i+1, len(flexible_actions)):
                    for k in range(j+1, len(flexible_actions)):
                        act1 = flexible_actions[i]
                        act2 = flexible_actions[j]
                        act3 = flexible_actions[k]
                        ids = {act1['event_id'], act2['event_id'], act3['event_id']}
                        if len(ids) < 3:
                            continue
                        spending_changes = [
                            {'event_id': act1['event_id'], 'action': act1['action'], 'new_amount': act1['new_amount']},
                            {'event_id': act2['event_id'], 'action': act2['action'], 'new_amount': act2['new_amount']},
                            {'event_id': act3['event_id'], 'action': act3['action'], 'new_amount': act3['new_amount']}
                        ]
                        is_safe, min_headroom, _ = self.sim.simulate_balance(
                            uid, req_date_str, additional_outflows=[(req_date_str, req_amt)], spending_changes=spending_changes
                        )
                        if is_safe:
                            plan_str = f"{req_date_str}:{format_amount(req_amt)}"
                            changes_str = f"{act1['token']}|{act2['token']}|{act3['token']}"
                            desc1 = (
                                f"Stop the {act1['desc']}" if act1['action'] == 'stop'
                                else f"Reduce the {act1['desc']} to {format_currency_amount(home_curr, act1['new_amount'])}"
                            )
                            desc2_part = (
                                f"stop the {act2['desc']}" if act2['action'] == 'stop'
                                else f"reduce the {act2['desc']} to {format_currency_amount(home_curr, act2['new_amount'])}"
                            )
                            desc3_part = (
                                f"stop the {act3['desc']}" if act3['action'] == 'stop'
                                else f"reduce the {act3['desc']} to {format_currency_amount(home_curr, act3['new_amount'])}"
                            )
                            explanation = (
                                f"{desc1}, {desc2_part}, and {desc3_part}, then pay "
                                f"{format_currency_amount(home_curr, req_amt)} today. "
                                f"This leaves at least {format_currency_amount(home_curr, min_bal)} available."
                            )
                            sc_earliest = self.sim.compute_earliest_date_for_full_payment(uid, req_date_str, req_amt)
                            candidate_plans.append({
                                'status': 'affordable_with_plan',
                                'method': 'full_payment',
                                'plan': plan_str,
                                'earliest_date': sc_earliest or req_date_str,
                                'spending_changes': changes_str,
                                'explanation': explanation,
                                'meets_deadline': True,
                                'num_spending_changes': 3,
                                'total_cost': req_amt,
                                'start_date': req_date_str,
                                'num_payments': 1,
                                'option_id': 'option_spending_3'
                            })

        # Candidate E: Wait (Affordable Later)
        if earliest_full_date and 'full_payment' in allowed_methods and earliest_full_date > req_date_str:
            earliest_d = parse_date(earliest_full_date)
            meets_deadline = earliest_d <= desired_comp_date if desired_comp_date else True
            plan_str = f"{earliest_full_date}:{format_amount(req_amt)}"
            explanation = (
                f"Pay {format_currency_amount(home_curr, req_amt)} in full on "
                f"{earliest_d.strftime('%d %B %Y').lstrip('0')}. "
                f"Paying earlier would take the balance below the "
                f"{format_currency_amount(home_curr, min_bal)} minimum."
            )
            candidate_plans.append({
                'status': 'affordable_later',
                'method': 'wait',
                'plan': plan_str,
                'earliest_date': earliest_full_date,
                'spending_changes': 'none',
                'explanation': explanation,
                'meets_deadline': meets_deadline,
                'num_spending_changes': 0,
                'total_cost': req_amt,
                'start_date': earliest_full_date,
                'num_payments': 1,
                'option_id': 'option_wait'
            })

        # 4. Rank candidates using strict Lexicographic order
        # Priority: meets_deadline > fewest spending changes > total_cost > start_date > num_payments
        # Status priority: affordable_now > affordable_with_plan(no changes) > affordable_with_plan(with changes) > affordable_later
        STATUS_RANK = {
            'affordable_now': 0,
            'affordable_with_plan': 1,
            'affordable_later': 2,
            'not_affordable': 3
        }
        
        if candidate_plans:
            candidate_plans.sort(key=lambda p: (
                0 if p['meets_deadline'] else 1,
                p['num_spending_changes'],
                STATUS_RANK.get(p['status'], 9),
                p['total_cost'],
                p['start_date'],
                p['num_payments'],
                p['option_id']
            ))
            best_plan = candidate_plans[0]
        else:
            # Candidate F: Not Recommended Fallback
            if desired_comp_date:
                deadline_str = desired_comp_date.strftime('%d %B %Y').lstrip('0')
            else:
                deadline_str = 'deadline'
            
            # Check if a partial safe amount exists to use in explanation
            if safe_amt > 0 and allows_partial:
                explanation = (
                    f"Do not proceed with the {format_currency_amount(home_curr, req_amt)} request. "
                    f"Although {format_currency_amount(home_curr, safe_amt)} is available today, "
                    f"the full amount cannot be completed safely within 90 days."
                )
            else:
                explanation = (
                    f"Do not make this payment by {deadline_str}. "
                    f"None of the available options keeps the "
                    f"{format_currency_amount(home_curr, min_bal)} minimum protected."
                )
            
            best_plan = {
                'status': 'not_affordable',
                'method': 'not_recommended',
                'plan': 'none',
                'earliest_date': '',
                'spending_changes': 'none',
                'explanation': explanation
            }

        return {
            'request_id': req_id,
            'amount_safe_to_pay': safe_amt,
            'affordability_status': best_plan['status'],
            'recommended_payment_method': best_plan['method'],
            'payment_plan': best_plan['plan'],
            'earliest_date_for_full_payment': best_plan['earliest_date'],
            'spending_changes_needed': best_plan['spending_changes'],
            'decision_explanation': best_plan['explanation']
        }
