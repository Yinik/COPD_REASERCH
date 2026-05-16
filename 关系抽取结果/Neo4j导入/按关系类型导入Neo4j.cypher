// ============================================================
// COPD知识图谱 - 按关系类型独立导入（方案2）
// 说明：删除旧的RELATION标签关系，按13种具体类型重新导入
// 执行前请确认：
//   1. nodes.csv 和 relations_*.csv 已在Neo4j import目录
//   2. 节点（126个Entity）已经导入
//   3. 实体类型标签（Disease/Symptom等）已经设置
// ============================================================

// ---- Step 0: 删除旧的关系（统一RELATION标签）----
MATCH ()-[r:RELATION]->() DELETE r;

// ---- Step 1~13: 按关系类型逐段导入 ----

// 关系类型: 危险因素-疾病
LOAD CSV WITH HEADERS FROM 'file:///relations_危险因素_疾病.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`危险因素-疾病`]->(b)
SET r.context = row.context;

// 关系类型: 检查-筛查-疾病
LOAD CSV WITH HEADERS FROM 'file:///relations_检查_筛查_疾病.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`检查-筛查-疾病`]->(b)
SET r.context = row.context;

// 关系类型: 检查-评估-疾病
LOAD CSV WITH HEADERS FROM 'file:///relations_检查_评估_疾病.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`检查-评估-疾病`]->(b)
SET r.context = row.context;

// 关系类型: 检查-评估-症状
LOAD CSV WITH HEADERS FROM 'file:///relations_检查_评估_症状.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`检查-评估-症状`]->(b)
SET r.context = row.context;

// 关系类型: 检查-辅助诊断-疾病
LOAD CSV WITH HEADERS FROM 'file:///relations_检查_辅助诊断_疾病.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`检查-辅助诊断-疾病`]->(b)
SET r.context = row.context;

// 关系类型: 治疗-改善-症状
LOAD CSV WITH HEADERS FROM 'file:///relations_治疗_改善_症状.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`治疗-改善-症状`]->(b)
SET r.context = row.context;

// 关系类型: 疾病-并发症
LOAD CSV WITH HEADERS FROM 'file:///relations_疾病_并发症.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`疾病-并发症`]->(b)
SET r.context = row.context;

// 关系类型: 疾病-治疗
LOAD CSV WITH HEADERS FROM 'file:///relations_疾病_治疗.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`疾病-治疗`]->(b)
SET r.context = row.context;

// 关系类型: 疾病-症状
LOAD CSV WITH HEADERS FROM 'file:///relations_疾病_症状.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`疾病-症状`]->(b)
SET r.context = row.context;

// 关系类型: 药物-导致-并发症
LOAD CSV WITH HEADERS FROM 'file:///relations_药物_导致_并发症.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`药物-导致-并发症`]->(b)
SET r.context = row.context;

// 关系类型: 药物-治疗-疾病
LOAD CSV WITH HEADERS FROM 'file:///relations_药物_治疗_疾病.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`药物-治疗-疾病`]->(b)
SET r.context = row.context;

// 关系类型: 药物-缓解-症状
LOAD CSV WITH HEADERS FROM 'file:///relations_药物_缓解_症状.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`药物-缓解-症状`]->(b)
SET r.context = row.context;

// 关系类型: 诱发-急性加重
LOAD CSV WITH HEADERS FROM 'file:///relations_诱发_急性加重.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`诱发-急性加重`]->(b)
SET r.context = row.context;
