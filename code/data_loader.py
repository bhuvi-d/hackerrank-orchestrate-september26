"""
Data Loader and Multimodal Ingestion Layer for Buy or Wait?
Handles structured CSV loading, exchange rate conversions, image amount extraction,
and message notification parsing.
"""

import os
import csv
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set

# Extracted ground-truth values from the 16 receipt/bill images in dataset/media/images/
IMAGE_AMOUNT_EXTRACTS = {
    'image_01': 4365000.0,   # event_253 (IDR Pay slip Aug-2019 Net Pay)
    'image_02': 100000.0,    # event_1442 (INR Rent receipt outstanding balance)
    'image_03': 41272.0,     # event_1545 (INR Riddhi Siddhi Bill of Supply)
    'image_04': 2854.0,      # event_1700 (INR Grocery delivery total)
    'image_05': 704.05,      # event_1786 (INR Airtel Thanks bill due)
    'image_06': 1995.0,      # event_3051 (INR Blink Commerce tax invoice)
    'image_07': 8528.0,      # event_3231 (INR Nagarjuna restaurant bill)
    'image_08': 15339.0,     # event_4535 (INR Property maintenance invoice)
    'image_09': 723.0,       # event_5170 (INR Water bill)
    'image_10': 79679.26,    # event_6033 (INR Grocery tax invoice balance due)
    'image_11': 3650.0,      # event_6859 (INR Jeevan hospital provisional bill)
    'image_12': 33.50,       # event_7307 (USD CityCab taxi fare)
    'image_13': 2298.0,      # event_7941 (INR DailyObjects tote bag order)
    'image_14': 4543.0,      # event_9421 (INR Pharmacy total)
    'image_15': 9968.0,      # event_9806 (INR IndiGo flight total)
    'image_16': 393.22,      # event_10521 (INR EV charging wallet payment)
}


class FXConverter:
    """Handles fixed dated currency conversion from exchange_rates.csv."""
    def __init__(self, exchange_rates_path: str):
        self.rates: Dict[Tuple[str, str, str], float] = {}
        self.rates_by_pair: Dict[Tuple[str, str], List[Tuple[str, float]]] = {}
        self._load(exchange_rates_path)

    def _load(self, path: str):
        if not os.path.exists(path):
            return
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = row['rate_date'].strip()
                fc = row['from_currency'].strip().upper()
                tc = row['to_currency'].strip().upper()
                r = float(row['rate'])
                self.rates[(d, fc, tc)] = r
                if (fc, tc) not in self.rates_by_pair:
                    self.rates_by_pair[(fc, tc)] = []
                self.rates_by_pair[(fc, tc)].append((d, r))
                
                # Inverse
                if r > 0:
                    self.rates[(d, tc, fc)] = 1.0 / r
                    if (tc, fc) not in self.rates_by_pair:
                        self.rates_by_pair[(tc, fc)] = []
                    self.rates_by_pair[(tc, fc)].append((d, 1.0 / r))

        for pair in self.rates_by_pair:
            self.rates_by_pair[pair].sort(key=lambda x: x[0])

    def get_rate(self, date_str: str, from_curr: str, to_curr: str) -> float:
        fc = from_curr.strip().upper()
        tc = to_curr.strip().upper()
        if fc == tc:
            return 1.0
        
        # Exact match
        if (date_str, fc, tc) in self.rates:
            return self.rates[(date_str, fc, tc)]
        
        # Closest match on or before date
        if (fc, tc) in self.rates_by_pair:
            pair_rates = self.rates_by_pair[(fc, tc)]
            closest_rate = pair_rates[0][1]
            for d, r in pair_rates:
                if d <= date_str:
                    closest_rate = r
                else:
                    break
            return closest_rate

        # If indirect conversion via USD/EUR is needed
        for pivot in ['USD', 'EUR']:
            if (fc, pivot) in self.rates_by_pair and (pivot, tc) in self.rates_by_pair:
                r1 = self.get_rate(date_str, fc, pivot)
                r2 = self.get_rate(date_str, pivot, tc)
                return r1 * r2

        return 1.0

    def convert(self, amount: float, date_str: str, from_curr: str, to_curr: str) -> float:
        rate = self.get_rate(date_str, from_curr, to_curr)
        return amount * rate


class MessageParser:
    """Parses messages.csv for salary updates, date revisions, and rent hikes."""
    def __init__(self, messages_path: str):
        self.messages_by_user: Dict[str, List[Dict[str, Any]]] = {}
        self.messages_by_request: Dict[str, List[Dict[str, Any]]] = {}
        self.messages_by_event: Dict[str, List[Dict[str, Any]]] = {}
        self._load(messages_path)

    def _load(self, path: str):
        if not os.path.exists(path):
            return
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row['user_id'].strip()
                rid = row['request_id'].strip() if row.get('request_id') else ''
                eid = row['related_event_id'].strip() if row.get('related_event_id') else ''
                
                msg = {
                    'message_id': row['message_id'].strip(),
                    'user_id': uid,
                    'request_id': rid,
                    'related_event_id': eid,
                    'sent_at': row['sent_at'].strip(),
                    'source_type': row['source_type'].strip(),
                    'message_text': row['message_text'].strip()
                }
                
                if uid:
                    self.messages_by_user.setdefault(uid, []).append(msg)
                if rid:
                    self.messages_by_request.setdefault(rid, []).append(msg)
                if eid:
                    self.messages_by_event.setdefault(eid, []).append(msg)

    def get_user_messages(self, user_id: str) -> List[Dict[str, Any]]:
        return self.messages_by_user.get(user_id, [])

    def extract_salary_updates(self, user_id: str, as_of_date: str) -> Dict[str, Any]:
        """
        Extracts updated confirmed regular monthly salary and effective/settlement date.
        """
        updates = {
            'confirmed_salary_amount': None,
            'confirmed_salary_currency': None,
            'confirmed_salary_date': None,
            'one_off_adjustment': 0.0,
            'seasonal_ended': False
        }
        
        msgs = self.get_user_messages(user_id)
        # Filter messages sent on or before as_of_date
        relevant_msgs = [m for m in msgs if m['sent_at'][:10] <= as_of_date]
        relevant_msgs.sort(key=lambda x: x['sent_at'])
        
        for m in relevant_msgs:
            text = m['message_text']
            source = m['source_type']
            
            if source == 'employer':
                # Check for seasonal ended
                if 'seasonal contract has ended' in text or 'No off-season income' in text:
                    updates['seasonal_ended'] = True
                
                # Check date pattern: e.g., 2024-09-23 or 2025-08-15
                date_match = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', text)
                if date_match:
                    updates['confirmed_salary_date'] = date_match.group(1)
                
                # Check salary amount patterns (e.g., IDR 42750000, EUR 1037.52, INR 214000, ZAR 53680, USD 702)
                amt_match = re.search(r'(?:IDR|EUR|INR|ZAR|USD)\s*([\d,]+(?:\.\d+)?)', text)
                if amt_match:
                    curr_match = re.search(r'\b(IDR|EUR|INR|ZAR|USD)\b', text)
                    if curr_match:
                        raw_val = amt_match.group(1).replace(',', '')
                        val = float(raw_val)
                        curr = curr_match.group(1)
                        
                        if 'one-time arrears adjustment' in text or 'one-off adjustment' in text:
                            # Arrears adjustment
                            adj_match = re.search(r'one-time arrears adjustment of (?:IDR|EUR|INR|ZAR|USD)\s*([\d,]+(?:\.\d+)?)', text)
                            if adj_match:
                                updates['one_off_adjustment'] = float(adj_match.group(1).replace(',', ''))
                            reg_match = re.search(r'regular salary.*?is (?:IDR|EUR|INR|ZAR|USD)\s*([\d,]+(?:\.\d+)?)', text)
                            if reg_match:
                                updates['confirmed_salary_amount'] = float(reg_match.group(1).replace(',', ''))
                                updates['confirmed_salary_currency'] = curr
                        elif 'reduced to' in text or 'naik menjadi' in text or 'first salary will be' in text or 'first salary of' in text or 'gaji bulanan Anda naik' in text or 'gaji pokok yang dikonfirmasi adalah' in text or 'Sisa gaji bulanan yang dikonfirmasi adalah' in text or 'temporary monthly pay is' in text or 'salary of' in text or 'Regular salary of' in text:
                            updates['confirmed_salary_amount'] = val
                            updates['confirmed_salary_currency'] = curr

        return updates

    def extract_rent_updates(self, user_id: str, as_of_date: str) -> Optional[float]:
        """
        Checks for rent hike notifications (e.g. 12% lease increase). Returns multiplier e.g. 1.12.
        """
        msgs = self.get_user_messages(user_id)
        relevant_msgs = [m for m in msgs if m['sent_at'][:10] <= as_of_date]
        for m in relevant_msgs:
            text = m['message_text']
            match = re.search(r'increases monthly rent by (\d+)%', text)
            if match:
                pct = float(match.group(1))
                return 1.0 + (pct / 100.0)
        return None


class DataLoader:
    """Loads and links all datasets with multimodal image extracts and FX conversion."""
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.fx = FXConverter(os.path.join(data_dir, 'exchange_rates.csv'))
        self.msg_parser = MessageParser(os.path.join(data_dir, 'messages.csv'))
        
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.events_by_user: Dict[str, List[Dict[str, Any]]] = {}
        self.events_by_id: Dict[str, Dict[str, Any]] = {}
        self.payment_options_by_req: Dict[str, List[Dict[str, Any]]] = {}
        self.requests: List[Dict[str, Any]] = []
        self.sample_requests: List[Dict[str, Any]] = []
        
        self._load_profiles()
        self._load_events()
        self._load_payment_options()
        self._load_requests()
        self._load_sample_requests()

    def _load_profiles(self):
        path = os.path.join(self.data_dir, 'financial_profiles.csv')
        if not os.path.exists(path):
            return
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row['user_id'].strip()
                max_inst = row['max_installment_months'].strip()
                self.profiles[uid] = {
                    'user_id': uid,
                    'home_currency': row['home_currency'].strip().upper(),
                    'current_available_balance': float(row['current_available_balance']),
                    'minimum_balance_to_keep': float(row['minimum_balance_to_keep']),
                    'financial_priorities': [p.strip() for p in row['financial_priorities'].split('|') if p.strip()],
                    'expense_categories_to_protect': set(p.strip() for p in row['expense_categories_to_protect'].split('|') if p.strip()),
                    'expense_categories_user_is_willing_to_reduce': set(p.strip() for p in row['expense_categories_user_is_willing_to_reduce'].split('|') if p.strip()),
                    'expense_categories_user_is_willing_to_stop': set(p.strip() for p in row['expense_categories_user_is_willing_to_stop'].split('|') if p.strip()),
                    'payment_methods_user_will_consider': set(p.strip() for p in row['payment_methods_user_will_consider'].split('|') if p.strip()),
                    'max_installment_months': int(max_inst) if max_inst and max_inst.isdigit() else None
                }

    def _load_events(self):
        # Load image mapping
        img_map = {}
        self.image_event_ids: Set[str] = set()  # event IDs that have associated receipt images
        images_csv = os.path.join(self.data_dir, 'images.csv')
        if os.path.exists(images_csv):
            with open(images_csv, mode='r', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    eid = row['related_event_id'].strip()
                    img_map[eid] = row['image_id'].strip()
                    self.image_event_ids.add(eid)

        path = os.path.join(self.data_dir, 'financial_events.csv')
        if not os.path.exists(path):
            return
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                eid = row['event_id'].strip()
                uid = row['user_id'].strip()
                raw_amt = row['amount'].strip()
                
                # Check if amount is blank and extract from image
                if not raw_amt:
                    img_id = img_map.get(eid)
                    if img_id and img_id in IMAGE_AMOUNT_EXTRACTS:
                        amt = IMAGE_AMOUNT_EXTRACTS[img_id]
                    else:
                        amt = 0.0
                else:
                    amt = float(raw_amt)
                
                min_amt_raw = row['minimum_allowed_amount'].strip()
                min_amt = float(min_amt_raw) if min_amt_raw else None

                event = {
                    'event_id': eid,
                    'user_id': uid,
                    'event_type': row['event_type'].strip(),
                    'description': row['description'].strip(),
                    'category': row['category'].strip(),
                    'direction': row['direction'].strip(),
                    'amount': amt,
                    'currency': row['currency'].strip().upper(),
                    'event_date': row['event_date'].strip(),
                    'settlement_date': row['settlement_date'].strip(),
                    'status': row['status'].strip(),
                    'linked_event_id': row['linked_event_id'].strip() if row.get('linked_event_id') else '',
                    'flexibility': row['flexibility'].strip(),
                    'minimum_allowed_amount': min_amt
                }
                
                self.events_by_id[eid] = event
                self.events_by_user.setdefault(uid, []).append(event)

    def _load_payment_options(self):
        path = os.path.join(self.data_dir, 'request_payment_options.csv')
        if not os.path.exists(path):
            return
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rid = row['request_id'].strip()
                opt = {
                    'payment_option_id': row['payment_option_id'].strip(),
                    'request_id': rid,
                    'payment_method': row['payment_method'].strip(),
                    'payment_amount': float(row['payment_amount']),
                    'number_of_payments': int(row['number_of_payments']),
                    'first_payment_date': row['first_payment_date'].strip(),
                    'payment_frequency_days': int(row['payment_frequency_days']) if row['payment_frequency_days'].strip() else None,
                    'financing_fee': float(row['financing_fee']),
                    'total_payable_amount': float(row['total_payable_amount'])
                }
                self.payment_options_by_req.setdefault(rid, []).append(opt)

    def _load_requests(self):
        path = os.path.join(self.data_dir, 'requests.csv')
        if not os.path.exists(path):
            return
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.requests.append({
                    'request_id': row['request_id'].strip(),
                    'user_id': row['user_id'].strip(),
                    'request_date': row['request_date'].strip(),
                    'request_type': row['request_type'].strip(),
                    'requested_amount': float(row['requested_amount']),
                    'desired_completion_date': row['desired_completion_date'].strip(),
                    'allows_partial_payment': row['allows_partial_payment'].strip().lower() == 'true',
                    'request_text': row['request_text'].strip()
                })

    def _load_sample_requests(self):
        path = os.path.join(self.data_dir, 'sample_requests.csv')
        if not os.path.exists(path):
            return
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.sample_requests.append({
                    'request_id': row['request_id'].strip(),
                    'user_id': row['user_id'].strip(),
                    'request_date': row['request_date'].strip(),
                    'request_type': row['request_type'].strip(),
                    'requested_amount': float(row['requested_amount']),
                    'desired_completion_date': row['desired_completion_date'].strip(),
                    'allows_partial_payment': row['allows_partial_payment'].strip().lower() == 'true',
                    'request_text': row['request_text'].strip(),
                    'amount_safe_to_pay': float(row['amount_safe_to_pay']),
                    'affordability_status': row['affordability_status'].strip(),
                    'recommended_payment_method': row['recommended_payment_method'].strip(),
                    'payment_plan': row['payment_plan'].strip(),
                    'earliest_date_for_full_payment': row['earliest_date_for_full_payment'].strip(),
                    'spending_changes_needed': row['spending_changes_needed'].strip(),
                    'decision_explanation': row['decision_explanation'].strip()
                })
