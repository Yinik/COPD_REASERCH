// COPD医学知识图谱 - 完整导入脚本
// 数据量: 154 个实体, 846 条关系

CREATE INDEX entity_name_index FOR (n:Entity) ON (n.name);

// ===== 导入节点 =====
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
MERGE (n:Entity {name: row.name})
SET n.type = row.type, n.label_cn = row.label_cn;

// ===== 设置实体标签 =====
MATCH (n:Entity) WHERE n.type = 'Complication' SET n:Complication;
MATCH (n:Entity) WHERE n.type = 'Disease' SET n:Disease;
MATCH (n:Entity) WHERE n.type = 'Examination' SET n:Examination;
MATCH (n:Entity) WHERE n.type = 'Medication' SET n:Medication;
MATCH (n:Entity) WHERE n.type = 'RiskFactor' SET n:RiskFactor;
MATCH (n:Entity) WHERE n.type = 'Symptom' SET n:Symptom;
MATCH (n:Entity) WHERE n.type = 'Treatment' SET n:Treatment;

// ===== 按关系类型导入 =====
// --- 危险因素-疾病 (75条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/危险因素-疾病.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`危险因素-疾病`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 检查-筛查-疾病 (1条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/检查-筛查-疾病.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`检查-筛查-疾病`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 检查-评估-疾病 (12条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/检查-评估-疾病.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`检查-评估-疾病`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 检查-评估-症状 (28条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/检查-评估-症状.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`检查-评估-症状`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 检查-辅助诊断-疾病 (69条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/检查-辅助诊断-疾病.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`检查-辅助诊断-疾病`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 治疗-改善-疾病 (17条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/治疗-改善-疾病.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`治疗-改善-疾病`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 治疗-改善-症状 (63条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/治疗-改善-症状.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`治疗-改善-症状`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 疾病-共病 (57条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/疾病-共病.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`疾病-共病`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 疾病-并发症 (59条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/疾病-并发症.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`疾病-并发症`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 疾病-治疗 (34条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/疾病-治疗.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`疾病-治疗`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 疾病-症状 (119条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/疾病-症状.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`疾病-症状`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 药物-导致-并发症 (7条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/药物-导致-并发症.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`药物-导致-并发症`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 药物-治疗-疾病 (149条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/药物-治疗-疾病.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`药物-治疗-疾病`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 药物-缓解-症状 (95条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/药物-缓解-症状.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`药物-缓解-症状`]->(b)
SET r.source = row.source, r.doc = row.doc;

// --- 诱发-急性加重 (61条) ---
LOAD CSV WITH HEADERS FROM 'file:///relations/诱发-急性加重.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:`诱发-急性加重`]->(b)
SET r.source = row.source, r.doc = row.doc;

// ===== 导入完成 =====