import os
"""
Enriches listing_matches with:
  - dr_building / bayut_building: extracted building identifiers
  - building_match: True=same, False=different, None=unknown
  - is_authorized: True if Bayut registered_agency = Dubai Residential

Strategy: fetch all data, compute, delete+re-insert (faster than 8k PATCHes).
"""
import re
import json
import requests
import time

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wqaqbqsmyldzqjgdojsg.supabase.co")
KEY = os.getenv("SUPABASE_KEY", "")
H = {'apikey': KEY, 'Authorization': f'Bearer {KEY}'}
H_POST = {**H, 'Content-Type': 'application/json', 'Prefer': 'return=minimal'}


def fetch_all(table, select, extra=''):
    rows, offset = [], 0
    while True:
        r = requests.get(
            f'{SUPABASE_URL}/rest/v1/{table}?select={select}{extra}&limit=1000&offset={offset}',
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
    """Extract building number from DR unit ID."""
    if not unit_id:
        return None
    u = unit_id.strip()

    # Standard format: PREFIX-BUILDING-UNIT  e.g. TGR-027-06, GFA-4-805, DGCO-178-301
    m = re.match(r'^[A-Za-z]+-(\d+)-\d+', u)
    if m:
        return str(int(m.group(1)))

    # Dubai Wharf: "DUBAI WHARF TOWER 1-210"
    m = re.search(r'\bTOWER\s+(\d+)', u, re.IGNORECASE)
    if m:
        return m.group(1)

    # Al Khail Gate: "Phase II-1 - 28-406" → last number before final unit
    m = re.search(r'-\s*(\d+)-\d+\s*$', u)
    if m:
        return str(int(m.group(1)))

    # Ghoroob: "Ghr-Building-A23-209" → A23
    m = re.search(r'\bBuilding[-\s]+(\w+)', u, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    return None


def parse_bayut_building(location, building_info):
    """Extract building identifier from Bayut location or building_information."""
    bld_info = building_info or {}
    bld_name = (bld_info.get('building_name') or '').strip()

    # building_name like "GABLD027" → trailing number = 27
    if bld_name:
        m = re.search(r'(\d+)\s*$', bld_name)
        if m:
            return str(int(m.group(1)))
        m = re.search(r'(\d+)', bld_name)
        if m:
            return str(int(m.group(1)))

    # location string: "Building 27", "Tower 1", "Block 3"
    loc = location or ''
    m = re.search(r'\b(?:Building|Tower|Block)\s+(\w+)', loc, re.IGNORECASE)
    if m:
        val = m.group(1)
        try:
            return str(int(val))
        except ValueError:
            return val.upper()

    return None


def check_authorized(regulatory_info):
    if not regulatory_info:
        return False
    agency = (regulatory_info.get('registered_agency') or '').upper()
    return 'DUBAI RESIDENTIAL' in agency


def main():
    print('Fetching listing_matches...', flush=True)
    matches = fetch_all('listing_matches',
        'id,dr_url,bayut_id,score,score_beds,score_baths,score_size,score_price')
    print(f'  {len(matches)} matches', flush=True)

    print('Fetching DR units...', flush=True)
    dr_rows = fetch_all('dubai_residentials_full', 'url,unit_id,community')
    dr_map = {r['url']: r for r in dr_rows}

    print('Fetching Bayut units...', flush=True)
    bayut_rows = fetch_all('bayut_community_rentals',
        'id,location,building_information,regulatory_information')
    bayut_map = {r['id']: r for r in bayut_rows}

    print('Computing building match + authorization...', flush=True)
    rows_out = []
    stats = {'same': 0, 'diff': 0, 'unknown': 0, 'authorized': 0}

    for m in matches:
        dr = dr_map.get(m['dr_url'], {})
        b = bayut_map.get(m['bayut_id'], {})

        dr_bld = parse_dr_building(dr.get('unit_id'))
        bayut_bld = parse_bayut_building(b.get('location'), b.get('building_information'))

        if dr_bld and bayut_bld:
            building_match = (dr_bld == bayut_bld)
            if building_match:
                stats['same'] += 1
            else:
                stats['diff'] += 1
        else:
            building_match = None
            stats['unknown'] += 1

        authorized = check_authorized(b.get('regulatory_information'))
        if authorized:
            stats['authorized'] += 1

        rows_out.append({
            'dr_url':          m['dr_url'],
            'bayut_id':        m['bayut_id'],
            'score':           m['score'],
            'score_beds':      m['score_beds'],
            'score_baths':     m['score_baths'],
            'score_size':      m['score_size'],
            'score_price':     m['score_price'],
            'dr_building':     dr_bld,
            'bayut_building':  bayut_bld,
            'building_match':  building_match,
            'is_authorized':   authorized,
        })

    print(f'  Same building:    {stats["same"]}', flush=True)
    print(f'  Diff building:    {stats["diff"]}', flush=True)
    print(f'  Unknown building: {stats["unknown"]}', flush=True)
    print(f'  Authorized (DR):  {stats["authorized"]}', flush=True)

    # Delete all existing rows
    print('\nClearing listing_matches...', flush=True)
    r = requests.delete(
        f'{SUPABASE_URL}/rest/v1/listing_matches?id=gte.0',
        headers=H_POST, timeout=30)
    print(f'  Delete status: {r.status_code}', flush=True)

    # Re-insert in batches
    print('Re-inserting with building data...', flush=True)
    BATCH = 200
    success = 0
    for i in range(0, len(rows_out), BATCH):
        batch = rows_out[i:i+BATCH]
        r = requests.post(
            f'{SUPABASE_URL}/rest/v1/listing_matches',
            headers=H_POST, json=batch, timeout=30)
        if r.status_code in (200, 201):
            success += len(batch)
        else:
            print(f'  ERROR batch {i//BATCH+1}: {r.status_code} {r.text[:150]}', flush=True)
        time.sleep(0.05)

    print(f'Done: {success}/{len(rows_out)} rows inserted', flush=True)


if __name__ == '__main__':
    main()
