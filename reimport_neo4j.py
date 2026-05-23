#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空Neo4j后，用规范化CSV重新导入
"""
import os
import csv
import config
from py2neo import Graph

NEO4J_DIR = '关系抽取结果/Neo4j导入_v2'
graph = Graph(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))

print('=== 步骤1: 清空Neo4j ===')

# 删除所有关系和节点
graph.run('MATCH ()-[r]->() DELETE r')
graph.run('MATCH (n) DELETE n')
print('已清空所有节点和关系')

# 验证清空
node_cnt = graph.run('MATCH (n) RETURN count(n) as c').data()[0]['c']
rel_cnt = graph.run('MATCH ()-[r]->() RETURN count(r) as c').data()[0]['c']
print(f'清空后: 节点 {node_cnt} 个, 关系 {rel_cnt} 条')

print()
print('=== 步骤2: 导入节点 ===')

nodes_path = os.path.join(NEO4J_DIR, 'nodes.csv')
with open(nodes_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    nodes = list(reader)

print(f'读取节点: {len(nodes)} 个')

for n in nodes:
    graph.run("""
        MERGE (e:Entity {name: $name})
        SET e.type = $type, e.label_cn = $label_cn
    """, parameters={'name': n['name'], 'type': n.get('type', ''), 'label_cn': n.get('label_cn', n['name'])})

# 设置标签
types = set(n.get('type', '') for n in nodes if n.get('type'))
for t in types:
    graph.run(f"MATCH (n:Entity) WHERE n.type = '{t}' SET n:{t}")
    print(f'  设置标签: {t}')

node_cnt = graph.run('MATCH (n) RETURN count(n) as c').data()[0]['c']
print(f'导入后节点: {node_cnt} 个')

print()
print('=== 步骤3: 按关系类型导入 ===')

rel_dir = os.path.join(NEO4J_DIR, 'relations')
total_rels = 0

for fname in sorted(os.listdir(rel_dir)):
    if not fname.endswith('.csv'):
        continue
    
    rel_type = fname[:-4]  # 去掉.csv
    filepath = os.path.join(rel_dir, fname)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    count = 0
    for row in rows:
        try:
            cypher = f"""
                MATCH (a:Entity {{name: $head}})
                MATCH (b:Entity {{name: $tail}})
                MERGE (a)-[r:`{rel_type}`]->(b)
                SET r.source = $source, r.doc = $doc
            """
            graph.run(cypher, parameters={
                'head': row['head'], 'tail': row['tail'],
                'source': row.get('source', ''), 'doc': row.get('doc', '')
            })
            count += 1
        except Exception as e:
            print(f'  [警告] {rel_type}: {row["head"]} -> {row["tail"]}: {e}')
    
    total_rels += count
    print(f'  {rel_type}: {count}条')

print()
print('=== 导入完成 ===')
node_cnt = graph.run('MATCH (n) RETURN count(n) as c').data()[0]['c']
rel_cnt = graph.run('MATCH ()-[r]->() RETURN count(r) as c').data()[0]['c']
print(f'节点: {node_cnt} 个')
print(f'关系: {rel_cnt} 条')
print(f'关系类型数: {len(os.listdir(rel_dir))} 类')
