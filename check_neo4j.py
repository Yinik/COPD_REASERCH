import config
from py2neo import Graph
graph = Graph(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))

# 查看当前关系类型
result = graph.run('MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as cnt ORDER BY cnt DESC').data()
print('当前Neo4j中的关系类型:')
for row in result:
    print('  ' + row['rel_type'] + ': ' + str(row['cnt']) + '条')

print()
# 查看样本关系
sample = graph.run('MATCH ()-[r]->() RETURN type(r) as rel_type, startNode(r).name as head, endNode(r).name as tail LIMIT 5').data()
print('样本关系:')
for row in sample:
    print('  ' + row['head'] + ' -[' + row['rel_type'] + ']-> ' + row['tail'])
