# BERT 关系分类器使用说明

## 文件
- `bert_relation_classifier.py` — 主代码（训练 + 预测）
- `bert_relation_output/` — 训练输出目录（模型、日志、元数据）

## 环境要求
已经装好的依赖：
```bash
torch >= 2.0
transformers >= 4.30
pandas, numpy, sklearn
```

## 训练模型

### 在 PyCharm 终端运行
```bash
# 激活项目虚拟环境
I:\101实验专题\.venv\Scripts\activate

# 开始训练
python bert_relation_classifier.py --mode train
```

### 训练说明
- **数据**: `关系抽取结果/最终三元组_方案B_医学细化版.tsv` (675条, 13类关系)
- **模型**: bert-base-chinese (约400MB，首次运行会自动下载)
- **策略**: 5折交叉验证 + 类别权重平衡 + 早停
- **预计时间**: 
  - CPU: 30~60分钟
  - GPU: 5~10分钟
- **输出**:
  - `bert_relation_output/best_model_fold*.pt` — 各折最佳模型
  - `bert_relation_output/model_meta.json` — 关系映射和配置

## 单条预测

```bash
python bert_relation_classifier.py --mode predict \
  --sentence "吸烟是慢性阻塞性肺疾病的重要危险因素" \
  --head "吸烟" \
  --tail "慢性阻塞性肺疾病"
```

## 批量预测

在代码中调用：
```python
from bert_relation_classifier import RelationPredictor

predictor = RelationPredictor("bert_relation_output/best_model_fold1.pt")
results = predictor.predict_batch([
    {"sentence": "...", "head": "...", "tail": "..."},
    # ...
])
```

## 关系类型（13种）
| 关系 | 样本数 |
|------|--------|
| 药物-治疗-疾病 | 129 |
| 疾病-症状 | 100 |
| 疾病-检查 | 87 |
| 药物-缓解-症状 | 87 |
| 检查-检测-疾病 | 56 |
| 检查-发现-症状 | 54 |
| 疾病-并发症 | 50 |
| 风险因素-疾病 | 38 |
| 疾病-治疗 | 34 |
| 检查-治疗-症状 | 24 |
| 检查-治疗-疾病 | 12 |
| 药物-预防-疾病 | 3 |
| 检查-筛查-疾病 | 1 |

## 注意事项
1. **网络**: 首次训练需下载 bert-base-chinese (~400MB)，请确保网络畅通
2. **内存**: 建议至少 8GB 内存
3. **类别不平衡**: "检查-筛查-疾病"仅1条，模型可能学不好，后续可考虑合并到相近类别
