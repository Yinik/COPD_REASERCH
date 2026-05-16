# COPD医学知识图谱 - Neo4j 导入详细教程

## 一、准备工作

### 1.1 确认已生成的文件

在 `I:\101实验专题\关系抽取结果\Neo4j导入\` 目录下，应包含以下文件：

| 文件名 | 说明 | 是否必须 |
|--------|------|----------|
| `nodes.csv` | 126个实体节点 | **必须** |
| `relations.csv` | 675条关系汇总 | **必须** |
| `import.cypher` | Cypher导入脚本 | **推荐** |
| `README.md` | 使用说明 | 参考 |
| `relations_*.csv` | 13个按类型拆分的关系文件 | 可选 |

> **注意**：`relations.csv` 已经包含全部675条关系。新手只需用 `nodes.csv` + `relations.csv` 即可。

### 1.2 安装 Neo4j Desktop

1. 访问官网下载：https://neo4j.com/download/
2. 安装并注册账号（免费）
3. 创建一个新的 Project，然后点击 **"Add" → "Local DBMS"**
4. 设置数据库名称（如 `copd-kg`）和密码（如 `password123`）
5. 点击 **"Start"** 启动数据库
6. 点击 **"Open"** 选择 Neo4j Browser，浏览器会自动打开 `http://localhost:7474`

---

## 二、导入步骤

### 步骤1：将CSV文件复制到Neo4j的import目录

Neo4j出于安全考虑，只允许从特定的 `import` 目录读取文件。

**找到import目录的方法：**

**方法一：通过Neo4j Desktop图形界面（推荐）**
1. 在Neo4j Desktop中，点击你的数据库实例
2. 点击右侧的 **"..."**（三个点）按钮
3. 在下拉菜单中选择 **"Open Folder" → "Import"**
4. 系统会打开一个文件夹窗口，这就是 `import` 目录

**方法二：手动找路径**
```
C:\Users\<你的Windows用户名>\.Neo4jDesktop\relate-data\dbmss\<数据库ID>\import\
```

**复制操作：**
将以下文件复制到上述 `import` 文件夹中：
- `nodes.csv`
- `relations.csv`

> **注意**：此次生成的CSV采用 **UTF-8 无BOM** 编码，可直接被Neo4j读取。如果之前用过旧版文件，请确保覆盖为新版。

---

### 步骤2：打开Neo4j Browser并登录

1. 在浏览器中访问：`http://localhost:7474`
2. 首次登录时：
   - Username（用户名）：`neo4j`
   - Password（密码）：你创建数据库时设置的密码
3. 点击 **"Connect"** 连接

---

### 步骤3：清空旧数据（如果之前导入过）

在Browser顶部的输入框中，粘贴以下命令，然后点击右侧的 **运行按钮**（蓝色三角形）：

```cypher
MATCH (n) DETACH DELETE n;
```

> 这行会删除数据库中所有节点和关系。如果是全新数据库，可以跳过此步。
>
> 执行后下方会显示：`Deleted 0 nodes, Deleted 0 relationships`

---

### 步骤4：创建索引（提高查询速度）

```cypher
CREATE INDEX entity_name_index FOR (n:Entity) ON (n.name);
```

> 执行后显示：`Added 1 index`

---

### 步骤5：导入节点

```cypher
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
MERGE (n:Entity {name: row.name})
SET n.type = row.type,
    n.label_cn = row.label_cn;
```

**预期结果：**
- 显示 `Added 126 labels, created 126 nodes, set 252 properties`
- 左侧节点标签列表中会出现 `Entity(126)`

**验证节点是否导入成功：**

```cypher
MATCH (n) RETURN count(n) as 节点总数;
```

应返回：`126`

---

### 步骤6：为节点添加类型标签

这一步的作用是让不同实体类型拥有独立标签，方便后续按类型查询和着色。

```cypher
MATCH (n:Entity) WHERE n.type = 'Disease' SET n:Disease;
MATCH (n:Entity) WHERE n.type = 'Symptom' SET n:Symptom;
MATCH (n:Entity) WHERE n.type = 'Medication' SET n:Medication;
MATCH (n:Entity) WHERE n.type = 'Treatment' SET n:Treatment;
MATCH (n:Entity) WHERE n.type = 'Examination' SET n:Examination;
MATCH (n:Entity) WHERE n.type = 'RiskFactor' SET n:RiskFactor;
MATCH (n:Entity) WHERE n.type = 'Complication' SET n:Complication;
```

**预期结果：**
- 显示 `Added 126 labels`
- 左侧标签列表会新增：Disease、Symptom、Medication、Treatment、Examination、RiskFactor、Complication

**验证各类型的数量：**

```cypher
MATCH (n:Entity)
RETURN n.type as 类型, count(*) as 数量
ORDER BY 数量 DESC;
```

预期结果：

| 类型 | 数量 |
|------|------|
| Medication | 35 |
| Disease | 27 |
| Symptom | 24 |
| Treatment | 14 |
| Examination | 9 |
| RiskFactor | 12 |
| Complication | 5 |

---

### 步骤7：导入关系

```cypher
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:RELATION {type: row.relation}]->(b)
SET r.context = row.context;
```

**预期结果：**
- 显示 `Created 675 relationships, set 675 properties`

**验证关系总数：**

```cypher
MATCH ()-[r:RELATION]->() RETURN count(r) as 关系总数;
```

应返回：`675`

---

## 三、导入后验证

### 3.1 查看整体统计

```cypher
// 节点数
MATCH (n) RETURN count(n) as 节点数;
```

```cypher
// 关系数
MATCH ()-[r:RELATION]->() RETURN count(r) as 关系数;
```

```cypher
// 关系类型分布
MATCH ()-[r:RELATION]->()
RETURN r.type as 关系类型, count(*) as 数量
ORDER BY 数量 DESC;
```

### 3.2 查看COPD中心辐射图

```cypher
MATCH path = (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION*1..2]->(m)
RETURN path
LIMIT 50;
```

> 执行后右侧会显示一个以"慢性阻塞性肺疾病"为中心的辐射状网络图。

### 3.3 查看各类子图

**药物子图：**
```cypher
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '药物-治疗-疾病'}]->(m)
RETURN n, r, m;
```

**症状子图：**
```cypher
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '疾病-症状'}]->(m)
RETURN n, r, m;
```

**合并症子图：**
```cypher
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '疾病-并发症'}]->(m)
RETURN n, r, m;
```

**危险因素子图：**
```cypher
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '危险因素-疾病'}]->(m)
RETURN n, r, m;
```

---

## 四、可视化美化（可选但强烈推荐）

在Neo4j Browser界面左下角，找到 **"Graph Style Sheet"** 文字，点击后会弹出一个编辑框。

将里面原有的内容全部删除，替换为以下内容：

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

修改后，重新执行任意查询，图中的节点就会按类型显示不同颜色。

> **注意**：Neo4j Browser 不支持 `node[name="..."]` 属性选择器，所以无法通过CSS单独给 COPD 节点设置超大尺寸。如需突出显示，可在查询中手动选中 COPD 节点调整。

---

## 五、常见问题排查

### Q1：报错 `Cannot load file` 或 `File not found`

**原因**：CSV文件没有放在正确的 `import` 目录下。

**解决方法**：
1. 确认文件已复制到正确的 import 目录
2. 确认文件名没有写错（区分大小写）
3. 执行以下查询确认Neo4j的import路径：

```cypher
CALL dbms.listConfig() YIELD name, value
WHERE name='dbms.directories.import'
RETURN value;
```

### Q2：节点导入了，但属性为空（name/type都是null）

**原因**：旧版CSV文件带有UTF-8 BOM头，导致Neo4j把第一列识别为 `name` 而不是 `name`。

**解决方法**：
1. 确认使用的是新版生成的CSV文件（本次已修复为无BOM）
2. 如果仍有问题，可在导入语句中显式处理：

```cypher
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
WITH row, keys(row) as cols
MERGE (n:Entity {name: row.name})
SET n.type = row.type, n.label_cn = row.label_cn;
```

### Q3：节点导入了，但关系导入为0

**原因**：头实体或尾实体名称不匹配。

**排查方法**：
```cypher
// 检查是否有关系引用了不存在的节点
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
MATCH (a:Entity {name: row.head})
OPTIONAL MATCH (b:Entity {name: row.tail})
WHERE b IS NULL
RETURN row.head, row.tail, row.relation
LIMIT 10;
```

正常情况下不应有返回。如果有返回，说明nodes.csv缺少某些实体。

### Q4：查询示例返回空结果

**原因**：查询语句与导入方式不匹配。

**确认**：本教程和 `import.cypher` 中的查询均使用 **RELATION标签 + type属性** 的方式：

```cypher
// 正确写法
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '疾病-症状'}]->(m)
RETURN m.name;
```

如果使用以下写法会返回空结果（因为没有直接创建名为"疾病-症状"的关系类型）：

```cypher
// 错误写法
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:`疾病-症状`]->(m)
RETURN m.name;
```

### Q5：如何重新导入（覆盖旧数据）

```cypher
// 1. 删除所有节点和关系
MATCH (n) DETACH DELETE n;

// 2. 删除索引（可选）
DROP INDEX entity_name_index;

// 3. 从步骤4开始重新执行
```

---

## 六、文件清单总结

导入完成后，你的Neo4j数据库中应有：

| 统计项 | 数量 |
|--------|------|
| Entity节点 | 126 |
| Disease标签 | 27 |
| Symptom标签 | 24 |
| Medication标签 | 35 |
| Treatment标签 | 14 |
| Examination标签 | 9 |
| RiskFactor标签 | 12 |
| Complication标签 | 5 |
| RELATION关系 | 675 |
| 关系类型 | 13种 |

---

## 七、附：一键导入（适合确认无旧数据时）

如果你确定数据库是空的，可以把以下语句一次性粘贴执行：

```cypher
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
SET r.context = row.context;
```

然后验证：

```cypher
MATCH (n) RETURN count(n) as 节点数;
MATCH ()-[r:RELATION]->() RETURN count(r) as 关系数;
```

应返回 **126** 和 **675**。

---

**教程文档位置**：`I:\101实验专题\关系抽取结果\Neo4j导入教程.md`
