// ============================================================
// COPD医学知识图谱 - Neo4j 导入脚本
// 生成时间: 2026-05-08
// 数据量: 126 个实体, 675 条关系
// ============================================================

// ---- Step 1: 清理数据库（可选，谨慎使用）----
// MATCH (n) DETACH DELETE n;

// ---- Step 2: 创建索引（提高导入速度）----
CREATE INDEX entity_name_index FOR (n:Entity) ON (n.name);

// ---- Step 3: 导入节点 ----
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
MERGE (n:Entity {name: row.name})
SET n.type = row.type,
    n.label_cn = row.label_cn;

// 为不同类型创建标签（便于按类型查询和可视化）
MATCH (n:Entity) WHERE n.type = 'Disease' SET n:Disease;
MATCH (n:Entity) WHERE n.type = 'Symptom' SET n:Symptom;
MATCH (n:Entity) WHERE n.type = 'Medication' SET n:Medication;
MATCH (n:Entity) WHERE n.type = 'Treatment' SET n:Treatment;
MATCH (n:Entity) WHERE n.type = 'Examination' SET n:Examination;
MATCH (n:Entity) WHERE n.type = 'RiskFactor' SET n:RiskFactor;
MATCH (n:Entity) WHERE n.type = 'Complication' SET n:Complication;

// ---- Step 4: 导入关系（统一使用RELATION标签，属性type区分具体类型）----
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:RELATION {type: row.relation}]->(b)
SET r.context = row.context;

// ============================================================
// 常用查询示例（基于RELATION标签 + r.type属性过滤）
// ============================================================

// 1. 查看COPD为中心的所有关系（辐射图）
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION]->(m)
RETURN n.name, r.type, m.name, m.type
LIMIT 50;

// 2. 查看所有Disease节点
MATCH (n:Disease)
RETURN n.name, n.type
ORDER BY n.name;

// 3. 查看关系类型统计
MATCH ()-[r:RELATION]->()
RETURN r.type as relation_type, count(*) as count
ORDER BY count DESC;

// 4. 查找COPD的所有症状
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '疾病-症状'}]->(m)
RETURN m.name as symptom;

// 5. 查找COPD的治疗药物
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '药物-治疗-疾病'}]->(m)
RETURN m.name as medication;

// 6. 查找COPD的危险因素
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '危险因素-疾病'}]->(m)
RETURN m.name as risk_factor;

// 7. 查找COPD的常见合并症
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '疾病-并发症'}]->(m)
RETURN m.name as complication;

// 8. 查找COPD的治疗方式
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '疾病-治疗'}]->(m)
RETURN m.name as treatment;

// 9. 查找诱发COPD急性加重的因素
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '诱发-急性加重'}]->(m)
RETURN m.name as trigger;

// 10. 路径查询：从COPD到特定实体的路径
MATCH path = (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION*1..3]->(m:Entity {name: '心血管疾病'})
RETURN [node in nodes(path) | node.name] as path_nodes,
       [rel in relationships(path) | rel.type] as path_relations;

// 11. 查找与COPD有2跳关系的所有实体
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION*2]->(m)
RETURN m.name, m.type, count(*) as path_count
ORDER BY path_count DESC;

// 12. 统计每个实体的出度（连接数）
MATCH (n:Entity)-[r:RELATION]->()
RETURN n.name, n.type, count(r) as out_degree
ORDER BY out_degree DESC
LIMIT 20;

// 13. 查看药物-缓解-症状网络
MATCH (n)-[r:RELATION {type: '药物-缓解-症状'}]->(m)
RETURN n.name, m.name
LIMIT 30;

// ============================================================
// 可视化推荐Cypher（Neo4j Browser中使用）
// ============================================================

// 查看COPD辐射图（限制50个节点避免过载）
MATCH path = (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION*1..2]->(m)
RETURN path LIMIT 50;

// 查看药物子图
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '药物-治疗-疾病'}]->(m)
RETURN n, r, m;

// 查看症状子图
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '疾病-症状'}]->(m)
RETURN n, r, m;

// 查看合并症网络
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '疾病-并发症'}]->(m)
RETURN n, r, m;
