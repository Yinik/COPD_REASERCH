import json
from collections import defaultdict

with open('output/new_triples_reviewed.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

by_rel = defaultdict(list)
for t in data:
    by_rel[t['relation']].append(t)

lines = []
lines.append('审核后保留的304条新关系详细列表')
lines.append('=' * 60)

for rel in sorted(by_rel.keys()):
    items = by_rel[rel]
    lines.append('')
    lines.append('===== ' + rel + ' (' + str(len(items)) + '条) =====')
    for i, t in enumerate(items, 1):
        lines.append(str(i) + '. ' + t['head'] + ' -> ' + t['tail'])

with open('output/review_304_detailed.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print('已生成: output/review_304_detailed.txt')
print('各类别数量:')
for rel in sorted(by_rel.keys()):
    print('  ' + rel + ': ' + str(len(by_rel[rel])) + '条')
