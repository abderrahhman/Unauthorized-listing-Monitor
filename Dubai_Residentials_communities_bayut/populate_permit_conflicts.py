import os
"""
Finds all scraped community listings that share a permit number with DR's
official Bayut listings, confirms same unit, flags unauthorized agents.
Populates the permit_conflicts table.
"""
import requests, time

URL = 'https://wqaqbqsmyldzqjgdojsg.supabase.co'
KEY = os.getenv("SUPABASE_KEY", "")
H     = {'apikey': KEY, 'Authorization': f'Bearer {KEY}'}
H_POST = {**H, 'Content-Type': 'application/json', 'Prefer': 'return=minimal'}


def fetch_all(table, select):
    rows, offset = [], 0
    while True:
        r = requests.get(
            f'{URL}/rest/v1/{table}?select={select}&limit=1000&offset={offset}',
            headers=H, timeout=30)
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        offset += 1000
        if len(batch) < 1000:
            break
    return rows


def infer_community(location):
    loc = (location or '').lower()
    if 'gardens apartment' in loc or 'gfa' in loc:
        return 'Gardens Apartments'
    if 'the gardens' in loc:
        return 'The Gardens'
    if 'bluewaters' in loc:
        return 'Bluewaters'
    if 'city walk' in loc or 'citywalk' in loc:
        return 'Citywalk'
    if 'meydan' in loc:
        return 'Meydan Residence 1'
    if 'international city' in loc:
        return 'International City'
    if 'discovery gardens' in loc:
        return 'Discovery Gardens'
    if 'manazel al khor' in loc:
        return 'Manazel Al Khor'
    if 'dubai wharf' in loc:
        return 'Dubai Wharf'
    if 'al khail' in loc:
        return 'Al Khail Gate'
    return None


def main():
    print('Fetching DR official Bayut listings...', flush=True)
    dr_official = fetch_all('bayut_dubai_rentals',
        'url,permit_number,reference_number,location,beds,baths')
    print(f'  {len(dr_official)} listings', flush=True)

    print('Fetching scraped community listings...', flush=True)
    scraped = fetch_all('bayut_community_rentals',
        'url,permit_number,reference_number,location,beds,baths,agent,agency')
    print(f'  {len(scraped)} listings', flush=True)

    # Build permit → DR listing lookup
    dr_by_permit = {r['permit_number']: r for r in dr_official if r.get('permit_number')}

    # Build permit → scraped listings lookup
    sc_by_permit = {}
    for r in scraped:
        p = r.get('permit_number')
        if p:
            sc_by_permit.setdefault(p, []).append(r)

    overlap = set(dr_by_permit.keys()) & set(sc_by_permit.keys())
    print(f'\n{len(overlap)} permits appear in both tables', flush=True)

    rows = []
    for permit in sorted(overlap):
        dr = dr_by_permit[permit]
        for sc in sc_by_permit[permit]:
            # Skip if it's the exact same listing (same reference = DR's own)
            if sc.get('reference_number') == dr.get('reference_number'):
                continue
            # Same permit + different reference = confirmed same unit, different agent
            agent  = sc.get('agent') or {}
            agency = sc.get('agency') or {}
            rows.append({
                'permit_number':          permit,
                'dr_bayut_url':           dr.get('url'),
                'dr_reference':           dr.get('reference_number'),
                'dr_location':            dr.get('location'),
                'dr_beds':                dr.get('beds'),
                'dr_baths':               dr.get('baths'),
                'unauthorized_url':       sc.get('url'),
                'unauthorized_reference': sc.get('reference_number'),
                'unauthorized_location':  sc.get('location'),
                'unauthorized_beds':      sc.get('beds'),
                'unauthorized_baths':     sc.get('baths'),
                'agent_name':             agent.get('name'),
                'agency_name':            agency.get('name'),
                'agent_mobile':           agent.get('mobile'),
                'community':              infer_community(sc.get('location')),
            })

    print(f'{len(rows)} unauthorized conflicts found', flush=True)

    # Clear old data
    print('Clearing old data...', flush=True)
    requests.delete(f'{URL}/rest/v1/permit_conflicts?id=gte.0', headers=H_POST, timeout=20)

    # Upload in batches
    print('Uploading...', flush=True)
    BATCH = 50
    success = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        r = requests.post(f'{URL}/rest/v1/permit_conflicts',
            headers=H_POST, json=batch, timeout=30)
        if r.status_code in (200, 201):
            success += len(batch)
        else:
            print(f'  ERROR {r.status_code}: {r.text[:200]}', flush=True)
        time.sleep(0.05)

    print(f'Done: {success}/{len(rows)} rows uploaded', flush=True)

    # Summary by community
    from collections import Counter
    comms = Counter(r['community'] for r in rows)
    print('\nBy community:')
    for c, n in comms.most_common():
        print(f'  {c or "Unknown"}: {n}')

    # Summary by agency
    agencies = Counter(r['agency_name'] for r in rows)
    print('\nTop offending agencies:')
    for a, n in agencies.most_common(10):
        print(f'  {a or "Unknown"}: {n}')


if __name__ == '__main__':
    main()
