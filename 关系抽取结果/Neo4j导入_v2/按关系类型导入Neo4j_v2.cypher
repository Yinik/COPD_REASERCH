// ============================================================
// COPD知识图谱 - BERT修正版 - 按关系类型独立导入
// 数据量: 675 条关系, 13 种关系类型
// ============================================================

// ---- Step 0: 清空旧数据 ----
MATCH (n) DETACH DELETE n;

// ---- Step 1: 创建索引 ----
CREATE INDEX entity_name_index IF NOT EXISTS FOR (n:Entity) ON (n.name);

// ---- Step 2: 导入节点 ----
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
MERGE (n:Entity {name: row.name})
SET n.type = row.type,
    n.label_cn = row.label_cn;

// ---- Step 3: 为不同类型创建分类标签 ----
MATCH (n:Entity) WHERE n.type = 'Disease' SET n:Disease;
MATCH (n:Entity) WHERE n.type = 'Symptom' SET n:Symptom;
MATCH (n:Entity) WHERE n.type = 'Medication' SET n:Medication;
MATCH (n:Entity) WHERE n.type = 'Treatment' SET n:Treatment;
MATCH (n:Entity) WHERE n.type = 'Examination' SET n:Examination;
MATCH (n:Entity) WHERE n.type = 'RiskFactor' SET n:RiskFactor;
MATCH (n:Entity) WHERE n.type = 'Complication' SET n:Complication;

// ---- Step 4: 按关系类型逐段导入关系 ----

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
