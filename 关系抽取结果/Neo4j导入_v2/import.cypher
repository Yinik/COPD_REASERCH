// COPD医学知识图谱 - BERT修正版
// 数据量: 126 个实体, 675 条关系

CREATE INDEX entity_name_index FOR (n:Entity) ON (n.name);

LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
MERGE (n:Entity {name: row.name})
SET n.type = row.type, n.label_cn = row.label_cn;

MATCH (n:Entity) WHERE n.type = 'Disease' SET n:Disease;
MATCH (n:Entity) WHERE n.type = 'Symptom' SET n:Symptom;
MATCH (n:Entity) WHERE n.type = 'Medication' SET n:Medication;
MATCH (n:Entity) WHERE n.type = 'Treatment' SET n:Treatment;
MATCH (n:Entity) WHERE n.type = 'Examination' SET n:Examination;
MATCH (n:Entity) WHERE n.type = 'RiskFactor' SET n:RiskFactor;
MATCH (n:Entity) WHERE n.type = 'Complication' SET n:Complication;

LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:RELATION {type: row.relation}]->(b)
SET r.source = row.source;
