#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将审核通过的185条新关系导入Neo4j
"""
import json
import config
from py2neo import Graph

# 连接Neo4j
graph = Graph(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))

# 读取审核通过的新关系
with open('output/new_triples_reviewed.json', 'r', encoding='utf-8') as f:
    triples = json.load(f)

print(f'准备导入 {len(triples)} 条新关系')

# 统计导入前
before_nodes = graph.run("MATCH (n) RETURN count(n) as c").data()[0]['c']
before_rels = graph.run("MATCH ()-[r]->() RETURN count(r) as c").data()[0]['c']
print(f'导入前: 节点 {before_nodes} 个, 关系 {before_rels} 条')

# 导入
imported = 0
skipped = 0
errors = 0

for t in triples:
    try:
        rel_type = t['relation']
        head = t['head']
        tail = t['tail']
        head_type = t.get('head_type', '')
        tail_type = t.get('tail_type', '')
        source = t.get('source', '')
        doc = t.get('doc', '')
        context = f"source={source}, doc={doc}"
        
        # 检查是否已存在
        check = graph.run(f"""
            MATCH (a:Entity {{name: $head}})-[r:`{rel_type}`]->(b:Entity {{name: $tail}})
            RETURN count(r) as cnt
        """, parameters={'head': head, 'tail': tail}).data()[0]['cnt']
        
        if check > 0:
            skipped += 1
            continue
        
        # MERGE节点和关系
        cypher = f"""
            MERGE (a:Entity {{name: $head}})
            SET a.type = $head_type
            MERGE (b:Entity {{name: $tail}})
            SET b.type = $tail_type
            MERGE (a)-[r:`{rel_type}`]->(b)
            SET r.source = $source, r.doc = $doc
        """
        graph.run(cypher, parameters={
            'head': head, 'head_type': head_type,
            'tail': tail, 'tail_type': tail_type,
            'source': source, 'doc': doc
        })
        imported += 1
        
    except Exception as e:
        errors += 1
        print(f'[错误] {t.get("head", "?")} -> {t.get("tail", "?")}: {e}')

# 统计导入后
after_nodes = graph.run("MATCH (n) RETURN count(n) as c").data()[0]['c']
after_rels = graph.run("MATCH ()-[r]->() RETURN count(r) as c").data()[0]['c']

print()
print('===== 导入结果 =====')
print(f'成功导入: {imported} 条')
print(f'已存在跳过: {skipped} 条')
print(f'失败: {errors} 条')
print()
print(f'导入前: 节点 {before_nodes} 个, 关系 {before_rels} 条')
print(f'导入后: 节点 {after_nodes} 个, 关系 {after_rels} 条')
print(f'新增节点: {after_nodes - before_nodes} 个')
print(f'新增关系: {after_rels - before_rels} 条')
