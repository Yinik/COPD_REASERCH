import json
import csv

# 读取审核通过的185条新关系
with open('output/new_triples_reviewed.json', 'r', encoding='utf-8') as f:
    triples = json.load(f)

# 导出为Neo4j导入格式 (head,tail,relation,source)
with open('output/new_relations_for_neo4j.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['head', 'tail', 'relation', 'source'])
    for t in triples:
        source = t.get('source', '') + '|' + t.get('doc', '')
        writer.writerow([t['head'], t['tail'], t['relation'], source])

print('已导出: output/new_relations_for_neo4j.csv')
print('行数:', len(triples) + 1, '(含表头)')

# 同时生成追加到原relations.csv的合并版本
with open('关系抽取结果/Neo4j导入_v2/relations.csv', 'r', encoding='utf-8') as f:
    existing = list(csv.reader(f))

with open('output/relations_merged.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    # 写入表头
    writer.writerow(['head', 'tail', 'relation', 'source'])
    # 写入已有关系（跳过原表头）
    for row in existing[1:]:
        writer.writerow(row)
    # 写入新关系
    for t in triples:
        source = t.get('source', '') + '|' + t.get('doc', '')
        writer.writerow([t['head'], t['tail'], t['relation'], source])

print('已导出合并版: output/relations_merged.csv')
print('总行数:', len(existing) + len(triples) + 1, '(含表头)')
