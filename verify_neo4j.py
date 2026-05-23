import config
from py2neo import Graph
graph = Graph(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))

print('=== Neo4j数据验证 ===')
print()

# 节点统计
nodes = graph.run('MATCH (n) RETURN labels(n) as labels, count(n) as cnt ORDER BY cnt DESC').data()
print('节点统计:')
total_nodes = 0
for row in nodes:
    label = row['labels'][0] if row['labels'] else 'Entity'
    print('  ' + label + ': ' + str(row['cnt']) + '个')
    total_nodes += row['cnt']
print('  总计: ' + str(total_nodes) + '个')
print()

# 关系统计
rels = graph.run('MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as cnt ORDER BY cnt DESC').data()
print('关系统计:')
total_rels = 0
for row in rels:
    print('  ' + row['rel_type'] + ': ' + str(row['cnt']) + '条')
    total_rels += row['cnt']
print('  总计: ' + str(total_rels) + '条')
print()

# 样本数据
print('样本关系（前5条）:')
sample = graph.run('MATCH (a)-[r]->(b) RETURN type(r) as rel, a.name as head, b.name as tail LIMIT 5').data()
for row in sample:
    print('  ' + row['head'] + ' -[' + row['rel'] + ']-> ' + row['tail'])
