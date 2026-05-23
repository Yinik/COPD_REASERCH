#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整理Neo4j导入文件夹：
1. 从Neo4j导出当前完整数据
2. 按关系类型拆分CSV
3. 生成统一Cypher导入脚本
4. 清理旧文件
"""
import os
import csv
import shutil
import config
from py2neo import Graph

NEO4J_DIR = '关系抽取结果/Neo4j导入_v2'

graph = Graph(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))

print('=== 步骤1: 从Neo4j导出节点 ===')

# 导出所有节点
nodes = graph.run("""
    MATCH (n:Entity)
    RETURN n.name as name, n.type as type, n.label_cn as label_cn
    ORDER BY n.name
""").data()

print(f'节点数: {len(nodes)}')

# 写入 nodes.csv
nodes_path = os.path.join(NEO4J_DIR, 'nodes.csv')
with open(nodes_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['name', 'type', 'label_cn'])
    for n in nodes:
        writer.writerow([n['name'], n.get('type', ''), n.get('label_cn', n['name'])])

print(f'已写入: {nodes_path}')

print()
print('=== 步骤2: 导出所有关系并按类型拆分 ===')

# 导出所有关系
relations = graph.run("""
    MATCH (a:Entity)-[r]->(b:Entity)
    RETURN type(r) as relation, a.name as head, b.name as tail,
           r.source as source, r.doc as doc
    ORDER BY type(r), a.name, b.name
""").data()

print(f'关系数: {len(relations)}')

# 按关系类型分组
from collections import defaultdict
by_type = defaultdict(list)
for r in relations:
    by_type[r['relation']].append(r)

# 创建relations子目录
rel_dir = os.path.join(NEO4J_DIR, 'relations')
os.makedirs(rel_dir, exist_ok=True)

# 写入总关系文件
all_rels_path = os.path.join(NEO4J_DIR, 'relations.csv')
with open(all_rels_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['head', 'tail', 'relation', 'source', 'doc'])
    for r in relations:
        writer.writerow([r['head'], r['tail'], r['relation'], r.get('source', ''), r.get('doc', '')])

print(f'已写入总关系文件: {all_rels_path} ({len(relations)}条)')

# 按类型写入独立文件
for rel_type, items in sorted(by_type.items()):
    # 文件名：关系类型.csv
    safe_name = rel_type.replace('/', '_').replace('\\', '_')
    filepath = os.path.join(rel_dir, f'{safe_name}.csv')
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['head', 'tail', 'source', 'doc'])
        for r in items:
            writer.writerow([r['head'], r['tail'], r.get('source', ''), r.get('doc', '')])
    print(f'  {rel_type}: {len(items)}条 -> relations/{safe_name}.csv')

print()
print('=== 步骤3: 生成Cypher导入脚本 ===')

cyphers = []
cyphers.append('// COPD医学知识图谱 - 完整导入脚本')
cyphers.append(f'// 数据量: {len(nodes)} 个实体, {len(relations)} 条关系')
cyphers.append('')
cyphers.append('CREATE INDEX entity_name_index FOR (n:Entity) ON (n.name);')
cyphers.append('')

# 节点导入
cyphers.append('// ===== 导入节点 =====')
cyphers.append("LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row")
cyphers.append('MERGE (n:Entity {name: row.name})')
cyphers.append('SET n.type = row.type, n.label_cn = row.label_cn;')
cyphers.append('')

# 设置节点标签
cyphers.append('// ===== 设置实体标签 =====')
types = sorted(set(n.get('type', '') for n in nodes if n.get('type')))
for t in types:
    cyphers.append(f"MATCH (n:Entity) WHERE n.type = '{t}' SET n:{t};")
cyphers.append('')

# 按关系类型导入
cyphers.append('// ===== 按关系类型导入 =====')
for rel_type in sorted(by_type.keys()):
    safe_name = rel_type.replace('/', '_').replace('\\', '_')
    cyphers.append(f"// --- {rel_type} ({len(by_type[rel_type])}条) ---")
    cyphers.append(f"LOAD CSV WITH HEADERS FROM 'file:///relations/{safe_name}.csv' AS row")
    cyphers.append(f"MATCH (a:Entity {{name: row.head}})")
    cyphers.append(f"MATCH (b:Entity {{name: row.tail}})")
    cyphers.append(f"MERGE (a)-[r:`{rel_type}`]->(b)")
    cyphers.append(f"SET r.source = row.source, r.doc = row.doc;")
    cyphers.append('')

cyphers.append('// ===== 导入完成 =====')

cypher_path = os.path.join(NEO4J_DIR, 'import.cypher')
with open(cypher_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(cyphers))

print(f'已写入: {cypher_path}')

print()
print('=== 步骤4: 清理旧文件 ===')

# 保留的文件列表
keep_files = {
    'nodes.csv', 'entity_synonyms.csv', 'relations.csv',
    'import.cypher', 'relations'
}

# 删除旧文件
deleted = 0
for item in os.listdir(NEO4J_DIR):
    item_path = os.path.join(NEO4J_DIR, item)
    if item in keep_files:
        continue
    if os.path.isfile(item_path):
        os.remove(item_path)
        print(f'  删除: {item}')
        deleted += 1

print(f'清理完成，删除 {deleted} 个旧文件')

print()
print('=== 整理完成 ===')
print(f'文件夹: {NEO4J_DIR}')
print('文件结构:')
print('  nodes.csv              - 实体节点 (154个)')
print('  entity_synonyms.csv    - 同义词表')
print('  relations.csv          - 全部关系 (846条)')
print('  relations/             - 按类型拆分的关系CSV')
for rel_type in sorted(by_type.keys()):
    safe_name = rel_type.replace('/', '_').replace('\\', '_')
    print(f'    {safe_name}.csv    - {rel_type} ({len(by_type[rel_type])}条)')
print('  import.cypher          - 统一导入脚本')
