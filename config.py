# config.py（你自己的，不上传Git）
from pathlib import Path

# 项目根目录（请修改为你的实际路径）
BASE_DIR = Path(r"I:\101实验专题")

# ========== 输入数据路径 ==========
RAW_PDF_DIR = BASE_DIR / "原始文献数据"
CLEANED_TEXT_DIR = BASE_DIR / "data" / "清洗后的文本数据"
RELATION_DIR = BASE_DIR / "关系抽取结果"
SEED_DICT_DIR = BASE_DIR / "种子词典构建结果"
EXTRACTION_DIR = BASE_DIR / "抽取结果"
EXTRACTION_DIR_V2 = BASE_DIR / "抽取结果_v2"

# ========== 输出路径 ==========
OUTPUT_DIR = BASE_DIR / "output"
RESULT_DIR = BASE_DIR / "result"
BERT_OUTPUT_DIR = BASE_DIR / "bert_relation_output"

# 自动创建输出文件夹
OUTPUT_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)
BERT_OUTPUT_DIR.mkdir(exist_ok=True)

# ========== Neo4j 配置 ==========
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "19950824"
