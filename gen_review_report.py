import json
from collections import defaultdict

with open('output/removed_triples.json', 'r', encoding='utf-8') as f:
    removed = json.load(f)
with open('output/new_triples_reviewed.json', 'r', encoding='utf-8') as f:
    kept = json.load(f)

lines = []
lines.append('=' * 70)
lines.append('医学审核报告')
lines.append('=' * 70)
lines.append('')
lines.append('审核原则：')
lines.append('1. 基于正确医学知识逐条判断')
lines.append('2. 不要太敏感，保留医学上合理的')
lines.append('3. 记录所有删除/修改理由')
lines.append('')
lines.append(f'原始条数: {len(kept) + len(removed)}')
lines.append(f'保留条数: {len(kept)}')
lines.append(f'删除条数: {len(removed)}')
lines.append('')
lines.append('各类别统计:')

kept_by_rel = defaultdict(int)
removed_by_rel = defaultdict(int)
for t in kept:
    kept_by_rel[t['relation']] += 1
for t in removed:
    removed_by_rel[t['relation']] += 1

all_rels = sorted(set(list(kept_by_rel.keys()) + list(removed_by_rel.keys())))
for rel in all_rels:
    k = kept_by_rel.get(rel, 0)
    r = removed_by_rel.get(rel, 0)
    lines.append(f'  {rel}: 保留{k}条, 删除{r}条')

lines.append('')
lines.append('=' * 70)
lines.append('删除详情（按类别）')
lines.append('=' * 70)

for rel in sorted(removed_by_rel.keys()):
    items = [t for t in removed if t['relation'] == rel]
    lines.append('')
    lines.append(f'【{rel}】删除{len(items)}条:')
    for t in items:
        reason = t.get('remove_reason', '')
        lines.append(f'  {t["head"]} -> {t["tail"]} ({reason})')

with open('output/medical_review_report.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print('报告已生成: output/medical_review_report.txt')
