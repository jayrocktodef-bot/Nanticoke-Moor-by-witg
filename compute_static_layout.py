import sqlite3
import json
import collections
import math
import os

def generate_static_layout():
    db_path = 'preservation_output/genealogy_preservation.db'
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute('SELECT person_id, name, maiden_name, married_last_name FROM persons')
    persons = c.fetchall()

    c.execute('SELECT person_a_id, person_b_id, relationship_type FROM relationships')
    rels = c.fetchall()

    parents_map = collections.defaultdict(list)
    children_map = collections.defaultdict(list)

    for pa, pb, rtype in rels:
        if rtype == 'child_of':
            parents_map[pa].append(pb)
            children_map[pb].append(pa)
        elif rtype == 'parent_of':
            parents_map[pb].append(pa)
            children_map[pa].append(pb)

    gen_depth = {}
    roots = [pid for pid, name, m, ml in persons if pid not in parents_map or len(parents_map[pid]) == 0]

    queue = collections.deque([(pid, 0) for pid in roots])
    visited = set()

    while queue:
        curr, depth = queue.popleft()
        if curr in visited:
            continue
        visited.add(curr)
        gen_depth[curr] = max(gen_depth.get(curr, 0), depth)

        for child in children_map[curr]:
            queue.append((child, depth + 1))

    for pid, name, m, ml in persons:
        if pid not in gen_depth:
            gen_depth[pid] = 0

    # Group persons by primary surname / clan
    surname_groups = collections.defaultdict(list)
    for pid, name, m, ml in persons:
        s = m or ml or (name.split()[-1] if name else 'Unknown')
        surname_groups[s.upper()].append(pid)

    # Sort surnames by size
    sorted_surnames = sorted(surname_groups.keys(), key=lambda s: len(surname_groups[s]), reverse=True)
    
    # Compact layout: Map surnames to tightly spaced columns
    surname_col_index = {s: idx for idx, s in enumerate(sorted_surnames)}

    layout_nodes = {}
    gen_counts = collections.defaultdict(int)

    for pid, name, m, ml in persons:
        gen = gen_depth[pid]
        s = (m or ml or (name.split()[-1] if name else 'Unknown')).upper()
        col_idx = surname_col_index.get(s, 0)
        
        idx_in_gen = gen_counts[(s, gen)]
        gen_counts[(s, gen)] += 1

        # Compact grid coordinates (120px column step, 140px row step)
        # Limit max columns to 12 main family trunks
        effective_col = col_idx % 12
        row_offset = math.floor(col_idx / 12) * 50

        x = effective_col * 240 + (idx_in_gen % 3) * 70
        y = gen * 180 + row_offset + math.floor(idx_in_gen / 3) * 50

        layout_nodes[pid] = {
            "x": round(x, 1),
            "y": round(y, 1),
            "level": gen,
            "clan": s
        }

    out_file = 'frontend/public/api/layout.json'
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, 'w') as f:
        json.dump(layout_nodes, f, indent=2)

    print(f"Compact precomputed graph layout saved for {len(layout_nodes)} nodes to {out_file}")
    conn.close()

if __name__ == '__main__':
    generate_static_layout()
