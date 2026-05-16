# COPD医学知识图谱 - Neo4j 详细导入教程

---

## 第一部分：安装和配置Neo4j Desktop

### 1.1 下载安装

1. 打开浏览器，访问 https://neo4j.com/download/
2. 点击下载 **"Neo4j Desktop"**（Windows版）
3. 下载完成后双击安装包，按提示完成安装
4. 安装完成后打开 Neo4j Desktop，首次打开需要注册账号（邮箱+密码），点击 **"Register"** 注册

### 1.2 创建数据库

打开 Neo4j Desktop 后：

**第一步：创建项目**
1. 左侧栏点击 **"Projects"**
2. 点击右上角的 **"New"** 按钮
3. 输入项目名称：`COPD知识图谱`
4. 点击 **"Create"**

**第二步：添加数据库**
1. 点击刚创建的 **"COPD知识图谱"** 项目
2. 在右侧找到 **"Add"** 按钮，点击后选择 **"Local DBMS"**
3. 在弹出的窗口中：
   - Name（数据库名称）：输入 `copd-db`
   - Password（密码）：输入你自己记得住的密码，例如 `password123`
   - Version（版本）：保持默认即可
4. 点击 **"Create"**
5. 等待创建完成（约30秒）

**第三步：启动数据库**
1. 找到刚创建的 `copd-db`
2. 点击 **"Start"** 按钮（绿色三角形）
3. 等待状态变成 **"Active"**（绿色圆点）

---

## 第二部分：准备CSV文件

### 2.1 确认文件位置

你不需要手动创建任何文件，所有文件已经生成好了，位于：

```
I:\101实验专题\关系抽取结果\Neo4j导入\
```

你需要复制以下 **2个文件**：
- `nodes.csv` （126个实体节点）
- `relations.csv` （675条关系）

### 2.2 找到Neo4j的import目录

**方法：通过Neo4j Desktop打开**

1. 确保数据库状态是 **"Active"**（绿色）
2. 点击数据库名称 `copd-db`
3. 在右侧找到 **"..."**（三个点）按钮，点击它
4. 在弹出的菜单中，鼠标悬停到 **"Open folder"**
5. 在子菜单中点击 **"Import"**
6. 系统会自动打开一个文件夹，路径类似：
   ```
   C:\Users\你的用户名\.Neo4jDesktop\relate-data\dbmss\dbms-xxxxxxxx\import\
   ```

**打开后的import文件夹应该是空的，或者只有几个系统文件。**

### 2.3 复制CSV文件

1. 在文件资源管理器中，打开 `I:\101实验专题\关系抽取结果\Neo4j导入\`
2. 选中 `nodes.csv` 和 `relations.csv` 这两个文件
3. **复制**（Ctrl+C）
4. 切换到刚才打开的 Neo4j import 文件夹窗口
5. **粘贴**（Ctrl+V）
6. 确认 import 文件夹里现在有这两个文件

> **重要**：只复制 `nodes.csv` 和 `relations.csv` 两个文件，其他文件不需要复制。

---

## 第三部分：打开Neo4j Browser

### 3.1 启动Browser

1. 回到 Neo4j Desktop
2. 点击数据库 `copd-db`
3. 点击右侧的 **"Open"** 按钮
4. 在弹出的下拉菜单中选择 **"Neo4j Browser"**
5. 系统会自动在浏览器中打开：`http://localhost:7474`

### 3.2 登录

1. 首次打开时，页面会要求输入用户名和密码
2. **Username（用户名）**：输入 `neo4j`
3. **Password（密码）**：输入你创建数据库时设置的密码（例如 `password123`）
4. 点击 **"Connect"**

登录成功后，页面会显示一个美元符号 `$` 的输入框，这就是Cypher查询输入框。

---

## 第四部分：执行导入脚本

在Neo4j Browser中，**逐段**执行以下Cypher语句。**每执行完一段，确认下方显示成功信息后，再执行下一段。**

### 步骤1：清空旧数据（可选）

如果你是**全新数据库**，跳过这一步。

如果你**之前导入过数据**，或者不确定是否干净，执行：

```cypher
MATCH (n) DETACH DELETE n;
```

**预期结果**：下方显示 `Deleted 0 nodes, Deleted 0 relationships`（如果是全新的）或删除的实际数量。

> 如果显示错误（如数据库为空时的提示），没关系，继续下一步。

---

### 步骤2：创建索引

```cypher
CREATE INDEX entity_name_index FOR (n:Entity) ON (n.name);
```

**预期结果**：下方显示 `Added 1 index`

---

### 步骤3：导入节点

```cypher
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
MERGE (n:Entity {name: row.name})
SET n.type = row.type,
    n.label_cn = row.label_cn;
```

**预期结果**：
- 下方显示：`Added 126 labels, created 126 nodes, set 252 properties`
- 页面左侧的 "Node Labels" 区域出现 `Entity(126)`

**如果显示 0 nodes created**：
- 说明CSV文件没有放到正确的import目录
- 返回第二部分，重新确认CSV文件位置

---

### 步骤4：为节点添加类型标签

```cypher
MATCH (n:Entity) WHERE n.type = 'Disease' SET n:Disease;
MATCH (n:Entity) WHERE n.type = 'Symptom' SET n:Symptom;
MATCH (n:Entity) WHERE n.type = 'Medication' SET n:Medication;
MATCH (n:Entity) WHERE n.type = 'Treatment' SET n:Treatment;
MATCH (n:Entity) WHERE n.type = 'Examination' SET n:Examination;
MATCH (n:Entity) WHERE n.type = 'RiskFactor' SET n:RiskFactor;
MATCH (n:Entity) WHERE n.type = 'Complication' SET n:Complication;
```

**预期结果**：
- 下方显示：`Added 126 labels`
- 页面左侧的 "Node Labels" 区域新增：
  - `Disease(27)`
  - `Symptom(24)`
  - `Medication(35)`
  - `Treatment(14)`
  - `Examination(9)`
  - `RiskFactor(12)`
  - `Complication(5)`

---

### 步骤5：导入关系

```cypher
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:RELATION {type: row.relation}]->(b)
SET r.context = row.context;
```

**预期结果**：
- 下方显示：`Created 675 relationships, set 675 properties`
- 页面左侧的 "Relationship Types" 区域出现 `RELATION(675)`

**如果显示 0 relationships**：
- 说明 `relations.csv` 文件不在import目录
- 或者节点导入失败导致没有匹配到实体

---

## 第五部分：验证导入结果

### 5.1 基础统计

**查询节点总数**：
```cypher
MATCH (n) RETURN count(n) as 节点总数;
```

**预期结果**：返回 `126`

**查询关系总数**：
```cypher
MATCH ()-[r:RELATION]->() RETURN count(r) as 关系总数;
```

**预期结果**：返回 `675`

**查询关系类型分布**：
```cypher
MATCH ()-[r:RELATION]->()
RETURN r.type as 关系类型, count(*) as 数量
ORDER BY 数量 DESC;
```

**预期结果**：显示13种关系类型及其数量

### 5.2 查看COPD辐射图

```cypher
MATCH path = (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION*1..2]->(m)
RETURN path
LIMIT 50;
```

**预期结果**：
- 右侧出现一张网络图
- 中心是一个大节点"慢性阻塞性肺疾病"
- 周围有多个小节点通过箭头连接到中心

---

## 第六部分：可视化美化

### 6.1 打开样式面板

1. 在Neo4j Browser界面的**左下角**，找到 **"Graph Style Sheet"** 这几个字
2. 点击它，会弹出一个文本编辑框
3. 把里面原来的内容**全部删除**
4. 粘贴下面的CSS代码

### 6.2 粘贴样式代码

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

### 6.3 应用样式

粘贴完成后，**关闭样式面板**（点击面板右上角的 X），然后重新执行查询：

```cypher
MATCH path = (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION*1..2]->(m)
RETURN path LIMIT 50;
```

现在不同颜色的节点代表不同类型：
- 红色 = 疾病
- 橙色 = 症状
- 青色 = 药物
- 蓝色 = 治疗
- 绿色 = 检查
- 黄色 = 危险因素
- 粉色 = 并发症

---

## 第七部分：查看各类子图

### 7.1 药物子图
```cypher
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '药物-治疗-疾病'}]->(m)
RETURN n, r, m;
```

### 7.2 症状子图
```cypher
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '疾病-症状'}]->(m)
RETURN n, r, m;
```

### 7.3 合并症子图
```cypher
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '疾病-并发症'}]->(m)
RETURN n, r, m;
```

### 7.4 危险因素子图
```cypher
MATCH (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION {type: '危险因素-疾病'}]->(m)
RETURN n, r, m;
```

---

## 第八部分：常见问题排查

### 问题1：执行LOAD CSV时提示 `Cannot load file`

**原因**：CSV文件没有放在Neo4j的import目录下。

**排查步骤**：
1. 在Neo4j Desktop中，点击数据库的 **"..." → "Open folder" → "Import"**
2. 确认 `nodes.csv` 和 `relations.csv` 在这个文件夹里
3. 如果不在，重新复制过去

### 问题2：节点导入显示0 created

**原因**：CSV编码问题或文件路径问题。

**排查步骤**：
1. 确认使用的是新生成的文件（无BOM）
2. 确认文件名是 `nodes.csv` 不是 `nodes.csv.txt`（Windows可能隐藏扩展名）
3. 在Neo4j Browser中执行：
   ```cypher
   CALL dbms.listConfig() YIELD name, value
   WHERE name='dbms.directories.import'
   RETURN value;
   ```
   返回的路径就是你应该放CSV文件的目录

### 问题3：关系导入显示0 created

**原因**：节点导入失败，或者头/尾实体名称不匹配。

**排查步骤**：
1. 先确认节点导入成功（`MATCH (n) RETURN count(n)` 返回126）
2. 执行以下查询检查是否有缺失的实体：
   ```cypher
   LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
   MATCH (a:Entity {name: row.head})
   OPTIONAL MATCH (b:Entity {name: row.tail})
   WHERE b IS NULL
   RETURN row.head, row.tail, row.relation
   LIMIT 10;
   ```
   如果返回结果，说明 `row.tail` 中的实体在nodes.csv中不存在。

### 问题4：查询COPD辐射图时返回空

**原因**：查询语句写错了，或者数据没导入成功。

**正确查询**：
```cypher
MATCH path = (n:Entity {name: '慢性阻塞性肺疾病'})-[r:RELATION*1..2]->(m)
RETURN path LIMIT 50;
```

**注意**：
- 必须使用 `RELATION` 标签
- 必须使用 `{name: '慢性阻塞性肺疾病'}`（注意是单引号）
- 必须使用 `[r:RELATION*1..2]` 而不是 `[*1..2]`

### 问题5：样式不生效

**原因**：样式语法写错，或者没有关闭面板重新查询。

**解决**：
1. 检查样式面板中的代码是否完整粘贴
2. 关闭样式面板
3. 重新执行查询

---

## 第九部分：一键导入（高级用户）

如果你确定数据库是空的，可以一次性粘贴执行所有导入语句：

```cypher
// 清空旧数据
MATCH (n) DETACH DELETE n;

// 创建索引
CREATE INDEX entity_name_index FOR (n:Entity) ON (n.name);

// 导入节点
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
MERGE (n:Entity {name: row.name})
SET n.type = row.type, n.label_cn = row.label_cn;

// 添加类型标签
MATCH (n:Entity) WHERE n.type = 'Disease' SET n:Disease;
MATCH (n:Entity) WHERE n.type = 'Symptom' SET n:Symptom;
MATCH (n:Entity) WHERE n.type = 'Medication' SET n:Medication;
MATCH (n:Entity) WHERE n.type = 'Treatment' SET n:Treatment;
MATCH (n:Entity) WHERE n.type = 'Examination' SET n:Examination;
MATCH (n:Entity) WHERE n.type = 'RiskFactor' SET n:RiskFactor;
MATCH (n:Entity) WHERE n.type = 'Complication' SET n:Complication;

// 导入关系
LOAD CSV WITH HEADERS FROM 'file:///relations.csv' AS row
MATCH (a:Entity {name: row.head})
MATCH (b:Entity {name: row.tail})
MERGE (a)-[r:RELATION {type: row.relation}]->(b)
SET r.context = row.context;
```

**验证**：
```cypher
MATCH (n) RETURN count(n) as 节点数;
MATCH ()-[r:RELATION]->() RETURN count(r) as 关系数;
```

---

## 附录：数据说明

| 实体类型 | 数量 | 说明 |
|---------|------|------|
| Disease | 27 | 疾病 |
| Symptom | 24 | 症状 |
| Medication | 35 | 药物 |
| Treatment | 14 | 治疗方式 |
| Examination | 9 | 检查 |
| RiskFactor | 12 | 危险因素 |
| Complication | 5 | 并发症 |

| 关系类型 | 数量 |
|---------|------|
| 药物-治疗-疾病 | 129 |
| 疾病-症状 | 100 |
| 诱发-急性加重 | 87 |
| 药物-缓解-症状 | 87 |
| 检查-辅助诊断-疾病 | 56 |
| 治疗-改善-症状 | 54 |
| 疾病-并发症 | 50 |
| 危险因素-疾病 | 38 |
| 疾病-治疗 | 34 |
| 检查-评估-症状 | 24 |
| 检查-评估-疾病 | 12 |
| 药物-导致-并发症 | 3 |
| 检查-筛查-疾病 | 1 |

---

**文档位置**：`I:\101实验专题\关系抽取结果\Neo4j导入详细教程.md`
