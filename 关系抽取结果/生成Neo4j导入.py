#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成Neo4j导入文件（CSV + Cypher脚本）
修复：去掉BOM、修正查询语法、修正数据错误
"""

import csv
import os
from collections import defaultdict

OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'
INPUT_FILE = '方向规范化_疾病统一在头.tsv'
NEO4J_DIR = os.path.join(OUTPUT_DIR, 'Neo4j导入')

os.makedirs(NEO4J_DIR, exist_ok=True)

# 读取TSV
rows = []
with open(os.path.join(OUTPUT_DIR, INPUT_FILE), 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter='\t')
    for r in reader:
        rows.append(r)

print(f"读取 {len(rows)} 条关系")

# ==================== 修正已知数据错误 ====================
# 实体名称 -> 正确类型
TYPE_FIXES = {
    'CT': 'Examination',
    '中成药': 'Medication',
}

def fix_type(name, original_type):
    return TYPE_FIXES.get(name, original_type)

# ==================== 生成节点CSV ====================

# 提取所有唯一实体
entities = {}  # name -> type
for row in rows:
    h, t = row['头实体'], row['尾实体']
    h_type = fix_type(h, row['头类型'])
    t_type = fix_type(t, row['尾类型'])
    if h not in entities:
        entities[h] = h_type
    if t not in entities:
        entities[t] = t_type

# 写入节点CSV（utf-8 无BOM，避免Neo4j LOAD CSV读取问题）
nodes_csv = os.path.join(NEO4J_DIR, 'nodes.csv')
with open(nodes_csv, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['name', 'type', 'label_cn'])
    for name, etype in sorted(entities.items()):
        writer.writerow([name, etype, name])

print(f"节点CSV: {nodes_csv} ({len(entities)} 个实体)")

# ==================== 生成关系CSV ====================

# 按关系类型分组
rel_by_type = defaultdict(list)
for row in rows:
    rel_by_type[row['关系类型']].append({
        'head': row['头实体'],
        'tail': row['尾实体'],
        'context': row.get('精简上下文', '')[:100]
    })

# 写入总关系CSV（utf-8 无BOM）
relations_csv = os.path.join(NEO4J_DIR, 'relations.csv')
with open(relations_csv, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['head', 'tail', 'relation', 'context'])
    for rel_type, rels in rel_by_type.items():
        for r in rels:
            writer.writerow([r['head'], r['tail'], rel_type, r['context']])

print(f"关系CSV: {relations_csv} ({len(rows)} 条关系)")

# 为每种关系类型单独写入CSV（便于分批导入）
for rel_type, rels in rel_by_type.items():
    safe_name = rel_type.replace('-', '_').replace(' ', '_')
    filename = f'relations_{safe_name}.csv'
    filepath = os.path.join(NEO4J_DIR, filename)
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['head', 'tail', 'context'])
        for r in rels:
            writer.writerow([r['head'], r['tail'], r['context']])

print(f"按类型拆分CSV: {len(rel_by_type)} 种关系类型")

# ==================== 生成Cypher导入脚本 ====================

# 收集关系类型列表用于查询示例
rel_type_list = sorted(rel_by_type.keys())

# 统计信息用于文档
entity_type_counts = defaultdict(int)
for etype in entities.values():
    entity_type_counts[etype] += 1

cypher_script = f"""// ============================================================
// COPD医学知识图谱 - Neo4j 导入脚本
// 生成时间: 2026-05-08
// 数据量: {len(entities)} 个实体, {len(rows)} 条关系
// ============================================================

// ---- Step 1: 清理数据库（可选，谨慎使用）----
// MATCH (n) DETACH DELETE n;

// ---- Step 2: 创建索引（提高导入速度）----
CREATE INDEX entity_name_index FOR (n:Entity) ON (n.name);

// ---- Step 3: 导入节点 ----
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
MERGE (n:Entity {{name: row.name}})
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
MATCH (a:Entity {{name: row.head}})
MATCH (b:Entity {{name: row.tail}})
MERGE (a)-[r:RELATION {{type: row.relation}}]->(b)
SET r.context = row.context;
"""

# 添加常用查询示例（使用RELATION标签 + type属性过滤）
cypher_script += """
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
"""

# 添加可视化推荐查询
cypher_script += """
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
"""

# 保存Cypher脚本
cypher_path = os.path.join(NEO4J_DIR, 'import.cypher')
with open(cypher_path, 'w', encoding='utf-8') as f:
    f.write(cypher_script)

print(f"Cypher脚本: {cypher_path}")

# ==================== 生成使用说明 ====================

readme_lines = []
readme_lines.append("# COPD医学知识图谱 - Neo4j 导入指南")
readme_lines.append("")
readme_lines.append("## 文件说明")
readme_lines.append("")
readme_lines.append("| 文件 | 说明 |")
readme_lines.append("|------|------|")
readme_lines.append(f"| `nodes.csv` | {len(entities)} 个实体节点 |")
readme_lines.append(f"| `relations.csv` | {len(rows)} 条关系（汇总） |")
readme_lines.append("| `relations_*.csv` | 按关系类型拆分的关系文件 |")
readme_lines.append("| `import.cypher` | Neo4j Cypher 导入脚本 |")
readme_lines.append("")
readme_lines.append("## 导入步骤")
readme_lines.append("")
readme_lines.append("### 方法1：Neo4j Browser（推荐，适合数据量小）")
readme_lines.append("")
readme_lines.append("1. 启动 Neo4j 数据库（Desktop/Bloom/Browser）")
readme_lines.append("2. 打开 Neo4j Browser（http://localhost:7474）")
readme_lines.append("3. 将 `nodes.csv` 和 `relations.csv` 复制到 Neo4j 的 `import` 目录：")
readme_lines.append("   - Windows: `C:\\Users\\<用户名>\\.Neo4jDesktop\\relate-data\\dbmss\\<dbms-id>\\import\\`")
readme_lines.append("   - 或 Neo4j Desktop 中点击数据库 → Open Folder → Import")
readme_lines.append("4. 在 Browser 中逐段执行 `import.cypher` 中的语句")
readme_lines.append("")
readme_lines.append("### 方法2：Neo4j Admin Import（适合批量导入）")
readme_lines.append("")
readme_lines.append("```bash")
readme_lines.append("# 停止Neo4j")
readme_lines.append("neo4j stop")
readme_lines.append("")
readme_lines.append("# 使用neo4j-admin导入（需要先清空数据库）")
readme_lines.append("neo4j-admin database import full \\")
readme_lines.append("  --nodes=import/nodes.csv \\")
readme_lines.append("  --relationships=import/relations.csv \\")
readme_lines.append("  neo4j")
readme_lines.append("")
readme_lines.append("# 启动Neo4j")
readme_lines.append("neo4j start")
readme_lines.append("```")
readme_lines.append("")
readme_lines.append("### 方法3：Python py2neo（程序化导入）")
readme_lines.append("")
readme_lines.append("```python")
readme_lines.append("from py2neo import Graph, Node, Relationship")
readme_lines.append("")
readme_lines.append('graph = Graph("bolt://localhost:7687", auth=("neo4j", "password"))')
readme_lines.append("")
readme_lines.append("# 导入节点")
readme_lines.append("with open('nodes.csv', 'r', encoding='utf-8') as f:")
readme_lines.append("    reader = csv.DictReader(f)")
readme_lines.append("    for row in reader:")
readme_lines.append('        node = Node("Entity", name=row["name"], type=row["type"])')
readme_lines.append("        graph.create(node)")
readme_lines.append("")
readme_lines.append("# 导入关系")
readme_lines.append("with open('relations.csv', 'r', encoding='utf-8') as f:")
readme_lines.append("    reader = csv.DictReader(f)")
readme_lines.append("    for row in reader:")
readme_lines.append('        a = graph.nodes.match("Entity", name=row["head"]).first()')
readme_lines.append('        b = graph.nodes.match("Entity", name=row["tail"]).first()')
readme_lines.append('        rel = Relationship(a, "RELATION", b, type=row["relation"])')
readme_lines.append("        graph.create(rel)")
readme_lines.append("```")
readme_lines.append("")
readme_lines.append("## 可视化技巧")
readme_lines.append("")
readme_lines.append("### Neo4j Browser 样式配置")
readme_lines.append("")
readme_lines.append("在 Browser 左下角的 **Graph Style Sheet** 面板中，把原有内容替换为以下内容：")
readme_lines.append("")
readme_lines.append("```css")
readme_lines.append("// 疾病节点 - 红色，较大")
readme_lines.append("node.Disease {")
readme_lines.append("  color: #FF6B6B;")
readme_lines.append("  diameter: 60px;")
readme_lines.append("  border-color: #C0392B;")
readme_lines.append("  border-width: 3px;")
readme_lines.append("}")
readme_lines.append("")
readme_lines.append("// 症状节点 - 橙色")
readme_lines.append("node.Symptom {")
readme_lines.append("  color: #FFA500;")
readme_lines.append("  diameter: 40px;")
readme_lines.append("}")
readme_lines.append("")
readme_lines.append("// 药物节点 - 青色")
readme_lines.append("node.Medication {")
readme_lines.append("  color: #4ECDC4;")
readme_lines.append("  diameter: 40px;")
readme_lines.append("}")
readme_lines.append("")
readme_lines.append("// 治疗节点 - 蓝色")
readme_lines.append("node.Treatment {")
readme_lines.append("  color: #45B7D1;")
readme_lines.append("  diameter: 40px;")
readme_lines.append("}")
readme_lines.append("")
readme_lines.append("// 检查节点 - 绿色")
readme_lines.append("node.Examination {")
readme_lines.append("  color: #96CEB4;")
readme_lines.append("  diameter: 40px;")
readme_lines.append("}")
readme_lines.append("")
readme_lines.append("// 危险因素节点 - 黄色")
readme_lines.append("node.RiskFactor {")
readme_lines.append("  color: #FFEAA7;")
readme_lines.append("  diameter: 40px;")
readme_lines.append("}")
readme_lines.append("")
readme_lines.append("// 并发症节点 - 粉色")
readme_lines.append("node.Complication {")
readme_lines.append("  color: #DDA0DD;")
readme_lines.append("  diameter: 40px;")
readme_lines.append("}")
readme_lines.append("")
readme_lines.append("// 关系连线样式")
readme_lines.append("relationship {")
readme_lines.append("  color: #95A5A6;")
readme_lines.append("  shaft-width: 2px;")
readme_lines.append("  font-size: 12px;")
readme_lines.append("  text-color: #2C3E50;")
readme_lines.append("}")
readme_lines.append("```")
readme_lines.append("")
readme_lines.append("> **注意**：Neo4j Browser 不支持 `node[name=\"...\"]` 属性选择器，")
readme_lines.append("> 所以无法单独给 COPD 节点设置超大尺寸。可在查询时手动调整。")
readme_lines.append("")
readme_lines.append("### 推荐查询")
readme_lines.append("")
readme_lines.append("```cypher")
readme_lines.append("// 查看COPD辐射图（完整）")
readme_lines.append("MATCH path = (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION*1..2]->(m)")
readme_lines.append("RETURN path;")
readme_lines.append("")
readme_lines.append("// 查看药物子图")
readme_lines.append("MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '药物-治疗-疾病'}]->(m)")
readme_lines.append("RETURN n, r, m;")
readme_lines.append("")
readme_lines.append("// 查看合并症网络")
readme_lines.append("MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '疾病-并发症'}]->(m)")
readme_lines.append("RETURN n, r, m;")
readme_lines.append("```")
readme_lines.append("")
readme_lines.append("## 数据说明")
readme_lines.append("")
readme_lines.append("- **实体类型**: Disease(疾病), Symptom(症状), Medication(药物), Treatment(治疗), Examination(检查), RiskFactor(危险因素), Complication(并发症)")
readme_lines.append(f"- **关系类型**: {len(rel_by_type)} 种")
readme_lines.append("- **中心实体**: 慢性阻塞性肺疾病（慢阻肺/COPD）")
readme_lines.append("- **图谱结构**: 以COPD为中心的辐射型有向图，所有实体从COPD出发可达")
readme_lines.append("")
readme_lines.append("## 实体类型统计")
readme_lines.append("")
for etype, count in sorted(entity_type_counts.items(), key=lambda x: -x[1]):
    readme_lines.append(f"- {etype}: {count} 个")
readme_lines.append("")
readme_lines.append("## 关系类型统计")
readme_lines.append("")
for rel_type, rels in sorted(rel_by_type.items(), key=lambda x: -len(x[1])):
    readme_lines.append(f"- {rel_type}: {len(rels)} 条")

readme = "\n".join(readme_lines)
readme_path = os.path.join(NEO4J_DIR, 'README.md')
with open(readme_path, 'w', encoding='utf-8') as f:
    f.write(readme)

print(f"使用说明: {readme_path}")
print(f"\n{'='*60}")
print("Neo4j导入文件生成完成！")
print(f"{'='*60}")
print(f"\n文件清单:")
print(f"  {NEO4J_DIR}\\")
print(f"  ├── nodes.csv ({len(entities)} 实体)")
print(f"  ├── relations.csv ({len(rows)} 关系)")
print(f"  ├── relations_*.csv ({len(rel_by_type)} 种关系类型)")
print(f"  ├── import.cypher (导入脚本)")
print(f"  └── README.md (使用说明)")
