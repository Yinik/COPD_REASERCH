# COPD医学知识图谱 - Neo4j 导入指南

## 文件说明

| 文件 | 说明 |
|------|------|
| `nodes.csv` | 126 个实体节点 |
| `relations.csv` | 675 条关系（汇总） |
| `relations_*.csv` | 按关系类型拆分的关系文件 |
| `import.cypher` | Neo4j Cypher 导入脚本 |

## 导入步骤

### 方法1：Neo4j Browser（推荐，适合数据量小）

1. 启动 Neo4j 数据库（Desktop/Bloom/Browser）
2. 打开 Neo4j Browser（http://localhost:7474）
3. 将 `nodes.csv` 和 `relations.csv` 复制到 Neo4j 的 `import` 目录：
   - Windows: `C:\Users\<用户名>\.Neo4jDesktop\relate-data\dbmss\<dbms-id>\import\`
   - 或 Neo4j Desktop 中点击数据库 → Open Folder → Import
4. 在 Browser 中逐段执行 `import.cypher` 中的语句

### 方法2：Neo4j Admin Import（适合批量导入）

```bash
# 停止Neo4j
neo4j stop

# 使用neo4j-admin导入（需要先清空数据库）
neo4j-admin database import full \
  --nodes=import/nodes.csv \
  --relationships=import/relations.csv \
  neo4j

# 启动Neo4j
neo4j start
```

### 方法3：Python py2neo（程序化导入）

```python
from py2neo import Graph, Node, Relationship

graph = Graph("bolt://localhost:7687", auth=("neo4j", "password"))

# 导入节点
with open('nodes.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        node = Node("Entity", name=row["name"], type=row["type"])
        graph.create(node)

# 导入关系
with open('relations.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        a = graph.nodes.match("Entity", name=row["head"]).first()
        b = graph.nodes.match("Entity", name=row["tail"]).first()
        rel = Relationship(a, "RELATION", b, type=row["relation"])
        graph.create(rel)
```

## 可视化技巧

### Neo4j Browser 样式配置

在 Browser 左下角的 **Graph Style Sheet** 面板中，把原有内容替换为以下内容：

```css
// 疾病节点 - 红色，较大
node.Disease {
  color: #FF6B6B;
  diameter: 60px;
  border-color: #C0392B;
  border-width: 3px;
}

// 症状节点 - 橙色
node.Symptom {
  color: #FFA500;
  diameter: 40px;
}

// 药物节点 - 青色
node.Medication {
  color: #4ECDC4;
  diameter: 40px;
}

// 治疗节点 - 蓝色
node.Treatment {
  color: #45B7D1;
  diameter: 40px;
}

// 检查节点 - 绿色
node.Examination {
  color: #96CEB4;
  diameter: 40px;
}

// 危险因素节点 - 黄色
node.RiskFactor {
  color: #FFEAA7;
  diameter: 40px;
}

// 并发症节点 - 粉色
node.Complication {
  color: #DDA0DD;
  diameter: 40px;
}

// 关系连线样式
relationship {
  color: #95A5A6;
  shaft-width: 2px;
  font-size: 12px;
  text-color: #2C3E50;
}
```

> **注意**：Neo4j Browser 不支持 `node[name="..."]` 属性选择器，
> 所以无法单独给 COPD 节点设置超大尺寸。可在查询时手动调整。

### 推荐查询

```cypher
// 查看COPD辐射图（完整）
MATCH path = (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION*1..2]->(m)
RETURN path;

// 查看药物子图
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '药物-治疗-疾病'}]->(m)
RETURN n, r, m;

// 查看合并症网络
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '疾病-并发症'}]->(m)
RETURN n, r, m;
```

## 数据说明

- **实体类型**: Disease(疾病), Symptom(症状), Medication(药物), Treatment(治疗), Examination(检查), RiskFactor(危险因素), Complication(并发症)
- **关系类型**: 13 种
- **中心实体**: 慢性阻塞性肺疾病（慢阻肺/COPD）
- **图谱结构**: 以COPD为中心的辐射型有向图，所有实体从COPD出发可达

## 实体类型统计

- Medication: 35 个
- Disease: 27 个
- Symptom: 24 个
- Treatment: 14 个
- RiskFactor: 12 个
- Examination: 9 个
- Complication: 5 个

## 关系类型统计

- 药物-治疗-疾病: 129 条
- 疾病-症状: 100 条
- 诱发-急性加重: 87 条
- 药物-缓解-症状: 87 条
- 检查-辅助诊断-疾病: 56 条
- 治疗-改善-症状: 54 条
- 疾病-并发症: 50 条
- 危险因素-疾病: 38 条
- 疾病-治疗: 34 条
- 检查-评估-症状: 24 条
- 检查-评估-疾病: 12 条
- 药物-导致-并发症: 3 条
- 检查-筛查-疾病: 1 条