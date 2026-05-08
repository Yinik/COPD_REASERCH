# config_template.py
# 这是模板，每个人复制一份改名为 config.py，然后填自己的真实路径
# config.py 已经被 .gitignore 忽略，不会上传到 Git

# ================== 输入数据路径（每个人自己改） ==================
# Windows 路径建议用 r"..." 防止转义问题
# 示例：
# DATA_PATH = r"I:\101实验专题\data"

# 如果有多个数据文件夹，继续加：
# RAW_PDF_PATH = r"I:\101实验专题\原始PDF"
# CLEANED_PATH = r"I:\101实验专题\清洗结果"


# ================== 输出路径（一般不用改） ==================
from pathlib import Path

# 项目根目录（当前文件的上级）
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
RESULT_DIR = BASE_DIR / "result"

# 自动创建输出文件夹
OUTPUT_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)
