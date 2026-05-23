import os, sys, json, csv
sys.path.insert(0, '.')
from COPD图谱端到端抽取系统_v2 import COPDKGPipeline
from collections import Counter

# 获取58篇文献目录
best_dir = None
best_count = 0
for name in os.listdir('.'):
    full = os.path.join('.', name)
    if os.path.isdir(full):
        for sub in os.listdir(full):
            subfull = os.path.join(full, sub)
            if os.path.isdir(subfull):
                files = [f for f in os.listdir(subfull) if f.endswith('.txt')]
                if len(files) > best_count:
                    best_count = len(files)
                    best_dir = subfull

txt_files = [os.path.join(best_dir, f) for f in os.listdir(best_dir) if f.endswith('.txt')]
print('处理文献数:', len(txt_files))

pipeline = COPDKGPipeline()
all_triples = []
all_new = []
stats_per_doc = []

for i, f in enumerate(txt_files):
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            text = fh.read()
        result = pipeline.process(text, update_neo4j=False)
        doc_name = os.path.basename(f)
        stats_per_doc.append({
            'doc': doc_name,
            'entities': len(result['entities']),
            'candidates': len(result['triples']),
            'verified': len(result['verified_triples']),
            'new': len(result['new_triples'])
        })
        for t in result['verified_triples']:
            all_triples.append({
                'head': t['head'], 'relation': t['relation'], 'tail': t['tail'],
                'head_type': t['head_type'], 'tail_type': t['tail_type'],
                'source': t.get('source', '?'), 'doc': doc_name
            })
        for t in result['new_triples']:
            all_new.append({
                'head': t['head'], 'relation': t['relation'], 'tail': t['tail'],
                'head_type': t['head_type'], 'tail_type': t['tail_type'],
                'source': t.get('source', '?'), 'doc': doc_name
            })
        print('[%d/%d] %s: %d实体 %d候选 %d通过 %d新' % (
            i+1, len(txt_files), doc_name,
            len(result['entities']), len(result['triples']),
            len(result['verified_triples']), len(result['new_triples'])
        ))
    except Exception as e:
        print('ERROR in %s: %s' % (os.path.basename(f), e))

# 全局去重
seen = set()
unique_triples = []
for t in all_triples:
    key = (t['head'], t['relation'], t['tail'])
    if key not in seen:
        seen.add(key)
        unique_triples.append(t)

seen_new = set()
unique_new = []
for t in all_new:
    key = (t['head'], t['relation'], t['tail'])
    if key not in seen_new:
        seen_new.add(key)
        unique_new.append(t)

print()
print('===== 58篇文献全量抽取结果 =====')
print('总候选三元组:', len(all_triples))
print('去重后验证三元组:', len(unique_triples))
print('总新关系:', len(all_new))
print('去重后新关系:', len(unique_new))

rel_counts = Counter(t['relation'] for t in unique_new)
print()
print('新关系类型分布:')
for rel, cnt in rel_counts.most_common():
    print('  %s: %d' % (rel, cnt))

# 导出
os.makedirs('output', exist_ok=True)
with open('output/all_verified_triples.json', 'w', encoding='utf-8') as f:
    json.dump(unique_triples, f, ensure_ascii=False, indent=2)
with open('output/new_triples.json', 'w', encoding='utf-8') as f:
    json.dump(unique_new, f, ensure_ascii=False, indent=2)
with open('output/new_triples.tsv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(['head', 'relation', 'tail', 'head_type', 'tail_type', 'source', 'doc'])
    for t in unique_new:
        writer.writerow([t['head'], t['relation'], t['tail'], t['head_type'], t['tail_type'], t['source'], t['doc']])
with open('output/extraction_report.json', 'w', encoding='utf-8') as f:
    json.dump({
        'total_docs': len(txt_files),
        'total_candidates': len(all_triples),
        'unique_verified': len(unique_triples),
        'total_new': len(all_new),
        'unique_new': len(unique_new),
        'relation_distribution': dict(rel_counts),
        'per_doc': stats_per_doc
    }, f, ensure_ascii=False, indent=2)

print()
print('文件已导出:')
print('  output/all_verified_triples.json')
print('  output/new_triples.json')
print('  output/new_triples.tsv')
print('  output/extraction_report.json')
