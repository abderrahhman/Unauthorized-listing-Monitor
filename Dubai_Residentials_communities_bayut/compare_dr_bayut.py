import os
"""
Compares dubai_residentials_full (DR website) vs bayut_dubai_rentals (DR's own Bayut page).
Classifies each unit as:
  - matched:             found on both, may have price/size discrepancies
  - missing_from_bayut:  on DR website but no match on Bayut
  - extra_on_bayut:      on Bayut but no match on DR website
"""
import re
import requests
import time

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wqaqbqsmyldzqjgdojsg.supabase.co")
KEY = os.getenv("SUPABASE_KEY", "")
H = {'apikey': KEY, 'Authorization': f'Bearer {KEY}'}
H_POST = {**H, 'Content-Type': 'application/json', 'Prefer': 'return=minimal'}


def fetch_all(table, select):
    rows, offset = [], 0
    while True:
        r = requests.get(
            f'{SUPABASE_URL}/rest/v1/{table}?select={select}&limit=1000&offset={offset}',
            headers=H, timeout=30)
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        offset += 1000
        if len(batch) < 1000:
            break
    return rows


def parse_dr_building(unit_id):
    if not unit_id:
        return None
    u = unit_id.strip()
    m = re.match(r'^[A-Za-z]+-(\d+)-\d+', u)
    if m:
        return str(int(m.group(1)))
    m = re.search(r'\bTOWER\s+(\d+)', u, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'-\s*(\d+)-\d+\s*$', u)
    if m:
        return str(int(m.group(1)))
    m = re.search(r'\bBuilding[-\s]+(\w+)', u, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def parse_bayut_building(location, building_info):
    bld_info = building_info or {}
    bld_name = (bld_info.get('building_name') or '').strip()
    if bld_name:
        m = re.search(r'(\d+)\s*$', bld_name)
        if m:
            return str(int(m.group(1)))
        m = re.search(r'(\d+)', bld_name)
        if m:
            return str(int(m.group(1)))
    loc = location or ''
    m = re.search(r'\b(?:Building|Tower|Block)\s+(\w+)', loc, re.IGNORECASE)
    if m:
        val = m.group(1)
        try:
            return str(int(val))
        except ValueError:
            return val.upper()
    return None


def parse_dr_unit(unit_id):
    """Extract unit number (last segment) from DR unit ID."""
    if not unit_id:
        return None
    parts = re.split(r'[-\s]+', unit_id.strip())
    try:
        return str(int(parts[-1]))
    except (ValueError, IndexError):
        return None


def parse_ref_unit(reference_number):
    """Extract unit from Bayut reference like AL-27-4 → 4, MZ-27-11 → 11."""
    if not reference_number:
        return None
    parts = reference_number.strip().split('-')
    if len(parts) == 3:
        try:
            int(parts[1])  # middle = building number
            return str(int(parts[2]))  # last = unit number
        except ValueError:
            return None
    return None


def match_score(dr, b, dr_bld, b_bld):
    """Returns (score, price_diff_pct, size_diff_pct, building_match)."""
    dr_beds   = dr.get('beds')
    dr_baths  = dr.get('baths')
    dr_sqft   = dr.get('size_sqft')
    dr_price  = dr.get('price_aed')
    b_beds    = b.get('beds')
    b_baths   = b.get('baths')
    b_sqft    = b.get('area_sqft')
    b_price   = (b.get('price') or {}).get('amount')

    if dr_beds != b_beds or dr_baths != b_baths:
        return 0, None, None, None

    score = 40  # beds + baths match

    size_diff = abs(dr_sqft - b_sqft) / dr_sqft if (dr_sqft and b_sqft) else None
    price_diff = abs(dr_price - b_price) / dr_price if (dr_price and b_price) else None

    if size_diff is not None and size_diff <= 0.15:
        score += 30

    if price_diff is not None and price_diff <= 0.20:
        score += 20

    if dr_bld and b_bld:
        bld_match = (dr_bld == b_bld)
        if bld_match:
            score += 10
    else:
        bld_match = None

    return score, (round(price_diff * 100, 1) if price_diff is not None else None), \
           (round(size_diff * 100, 1) if size_diff is not None else None), bld_match


def main():
    print('Fetching DR website units...', flush=True)
    dr_rows = fetch_all('dubai_residentials_full',
        'url,community,unit_id,location,beds,baths,size_sqft,price_aed')
    print(f'  {len(dr_rows)} units', flush=True)

    print('Fetching DR Bayut listings...', flush=True)
    b_rows = fetch_all('bayut_dubai_rentals',
        'id,url,reference_number,permit_number,beds,baths,area_sqft,price,location,building_information')
    print(f'  {len(b_rows)} listings', flush=True)

    # Pre-compute building numbers
    for dr in dr_rows:
        dr['_bld'] = parse_dr_building(dr.get('unit_id'))
        dr['_unit'] = parse_dr_unit(dr.get('unit_id'))
    for b in b_rows:
        b['_bld'] = parse_bayut_building(b.get('location'), b.get('building_information'))
        b['_unit'] = parse_ref_unit(b.get('reference_number'))

    matched_bayut_ids = set()
    results = []

    # For each DR unit, find best Bayut match
    for dr in dr_rows:
        best_score = 0
        best_b = None
        best_price_diff = None
        best_size_diff = None
        best_bld_match = None

        for b in b_rows:
            score, pdiff, sdiff, bld_match = match_score(dr, b, dr['_bld'], b['_bld'])
            if score > best_score:
                best_score = score
                best_b = b
                best_price_diff = pdiff
                best_size_diff = sdiff
                best_bld_match = bld_match

        if best_score >= 40 and best_b:
            matched_bayut_ids.add(best_b['id'])
            status = 'matched'
            b = best_b
            results.append({
                'status':          status,
                'dr_url':          dr.get('url'),
                'bayut_url':       b.get('url'),
                'dr_beds':         dr.get('beds'),
                'dr_baths':        dr.get('baths'),
                'dr_size_sqft':    dr.get('size_sqft'),
                'dr_price_aed':    dr.get('price_aed'),
                'dr_location':     dr.get('location'),
                'dr_community':    dr.get('community'),
                'dr_unit_id':      dr.get('unit_id'),
                'bayut_beds':      b.get('beds'),
                'bayut_baths':     b.get('baths'),
                'bayut_sqft':      b.get('area_sqft'),
                'bayut_price':     (b.get('price') or {}).get('amount'),
                'bayut_location':  b.get('location'),
                'bayut_reference': b.get('reference_number'),
                'bayut_permit':    b.get('permit_number'),
                'price_diff_pct':  best_price_diff,
                'size_diff_pct':   best_size_diff,
                'building_match':  best_bld_match,
                'dr_building':     dr['_bld'],
                'bayut_building':  b['_bld'],
            })
        else:
            results.append({
                'status':       'missing_from_bayut',
                'dr_url':       dr.get('url'),
                'bayut_url':    None,
                'dr_beds':      dr.get('beds'),
                'dr_baths':     dr.get('baths'),
                'dr_size_sqft': dr.get('size_sqft'),
                'dr_price_aed': dr.get('price_aed'),
                'dr_location':  dr.get('location'),
                'dr_community': dr.get('community'),
                'dr_unit_id':   dr.get('unit_id'),
                'dr_building':  dr['_bld'],
                'building_match': None,
            })

    # Bayut listings with no DR match
    for b in b_rows:
        if b['id'] not in matched_bayut_ids:
            results.append({
                'status':          'extra_on_bayut',
                'dr_url':          None,
                'bayut_url':       b.get('url'),
                'bayut_beds':      b.get('beds'),
                'bayut_baths':     b.get('baths'),
                'bayut_sqft':      b.get('area_sqft'),
                'bayut_price':     (b.get('price') or {}).get('amount'),
                'bayut_location':  b.get('location'),
                'bayut_reference': b.get('reference_number'),
                'bayut_permit':    b.get('permit_number'),
                'bayut_building':  b['_bld'],
                'building_match':  None,
            })

    # Stats
    matched   = [r for r in results if r['status'] == 'matched']
    missing   = [r for r in results if r['status'] == 'missing_from_bayut']
    extra     = [r for r in results if r['status'] == 'extra_on_bayut']
    price_mis = [r for r in matched if r.get('price_diff_pct') and r['price_diff_pct'] > 5]

    print(f'\nResults:')
    print(f'  Matched:            {len(matched)}')
    print(f'  Missing from Bayut: {len(missing)}')
    print(f'  Extra on Bayut:     {len(extra)}')
    print(f'  Price mismatch >5%: {len(price_mis)}')

    # Normalize all rows to same keys
    all_keys = [
        'status', 'dr_url', 'bayut_url', 'dr_beds', 'dr_baths', 'dr_size_sqft',
        'dr_price_aed', 'dr_location', 'dr_community', 'dr_unit_id',
        'bayut_beds', 'bayut_baths', 'bayut_sqft', 'bayut_price', 'bayut_location',
        'bayut_reference', 'bayut_permit', 'price_diff_pct', 'size_diff_pct',
        'building_match', 'dr_building', 'bayut_building',
    ]
    results = [{k: row.get(k) for k in all_keys} for row in results]

    # Upload
    print('\nClearing old data...', flush=True)
    requests.delete(f'{SUPABASE_URL}/rest/v1/dr_bayut_comparison?id=gte.0', headers=H_POST, timeout=20)

    print('Uploading...', flush=True)
    BATCH = 50
    success = 0
    for i in range(0, len(results), BATCH):
        batch = results[i:i+BATCH]
        r = requests.post(f'{SUPABASE_URL}/rest/v1/dr_bayut_comparison',
            headers=H_POST, json=batch, timeout=30)
        if r.status_code in (200, 201):
            success += len(batch)
        else:
            print(f'  ERROR: {r.status_code} {r.text[:150]}', flush=True)
        time.sleep(0.05)

    print(f'Done: {success}/{len(results)} rows uploaded', flush=True)


if __name__ == '__main__':
    main()
