#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空Neo4j后重新导入（使用显式事务）
"""
import os
import csv
import config
from py2neo import Graph

NEO4J_DIR = '关系抽取结果/Neo4j导入_v2'
graph = Graph(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))

print('=== 步骤1: 清空Neo4j ===')
graph.run('MATCH ()-[r]->() DELETE r')
graph.run('MATCH (n) DELETE n')
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

# 使用UNWIND批量导入
graph.run("""
    UNWIND $nodes as node
    MERGE (e:Entity {name: node.name})
    SET e.type = node.type, e.label_cn = node.label_cn
""", parameters={'nodes': nodes})

# 设置标签
for n in nodes:
    t = n.get('type', '')
    if t:
        graph.run(f"MATCH (e:Entity) WHERE e.type = '{t}' SET e:{t}")

node_cnt = graph.run('MATCH (n) RETURN count(n) as c').data()[0]['c']
print(f'导入后节点: {node_cnt} 个')

print()
print('=== 步骤3: 导入关系 ===')
rel_dir = os.path.join(NEO4J_DIR, 'relations')
total = 0

for fname in sorted(os.listdir(rel_dir)):
    if not fname.endswith('.csv'):
        continue
    rel_type = fname[:-4]
    filepath = os.path.join(rel_dir, fname)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # 批量导入
    graph.run(f"""
        UNWIND $rows as row
        MATCH (a:Entity {{name: row.head}})
        MATCH (b:Entity {{name: row.tail}})
        MERGE (a)-[r:`{rel_type}`]->(b)
        SET r.source = row.source, r.doc = row.doc
    """, parameters={'rows': rows})
    
    total += len(rows)
    print(f'  {rel_type}: {len(rows)}条')

print()
print('=== 验证 ===')
node_cnt = graph.run('MATCH (n) RETURN count(n) as c').data()[0]['c']
rel_cnt = graph.run('MATCH ()-[r]->() RETURN count(r) as c').data()[0]['c']
print(f'节点: {node_cnt} 个')
print(f'关系: {rel_cnt} 条')
print(f'关系类型: {len(os.listdir(rel_dir))} 类')
