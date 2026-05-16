import pdfplumber
import os
import re
import glob
import sys

# ==========================================
# 导入配置
# ==========================================
try:
    import config

    target_path = config.DATA_PATH
except ImportError:
    print("❌ 错误：找不到 config.py 模块，请确保它在当前目录下。")
    sys.exit(1)

# ==========================================
# 配置输出目录 (在这里修改你想保存的文件夹名字)
# ==========================================
OUTPUT_DIR_NAME = "清洗后的文本数据"


# ==========================================
# 核心清洗类
# ==========================================
class MedicalPDFCleaner:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.raw_text = ""
        self.cleaned_text = ""

    def extract_text(self):
        """动作1：提取文字"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        self.raw_text += text + "\n"
            # 打印简短状态，避免刷屏
            # print(f"✅ 提取: {os.path.basename(self.pdf_path)}")
        except Exception as e:
            print(f"❌ 提取失败 {self.pdf_path}: {e}")

    def clean_text(self):
        """动作2 & 3 & 4：去噪、去参考文献、断行合并"""
        if not self.raw_text:
            return

        text = self.raw_text

        # --- 动作2：编写“去噪”规则 ---

        # 1. 去除特定页眉 (根据你的描述定制)
        text = re.sub(r'\n\s*慢性阻塞性肺疾病诊疗指南\s*\n', '\n', text)

        # 2. 去除特定页脚 (匹配 "- 1 -", "- 10 -" 等)
        text = re.sub(r'\n\s*-\s*\d+\s*-\s*\n', '\n', text)

        # 3. 通用去噪
        text = re.sub(r'\n\s*(Page|P\.|第)\.?\s*\d+.*?\n', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)

        # --- 动作3：去参考文献 ---

        ref_keywords = ["References", "参考文献", "Bibliography", "参考书目"]

        cut_index = -1
        for keyword in ref_keywords:
            index = text.find(f"\n{keyword}")
            if index != -1:
                cut_index = index
                break

        if cut_index != -1:
            text = text[:cut_index]

        # --- 动作4：断行合并 ---

        lines = text.split('\n')
        merged_lines = []
        buffer = ""

        end_punctuations = {'.', '!', '?', '。', '！', '？', '：', '；'}

        for line in lines:
            line = line.strip()
            if not line:
                if buffer:
                    merged_lines.append(buffer)
                    buffer = ""
                continue

            if not buffer:
                buffer = line
            else:
                last_char = buffer[-1]
                first_char = line[0]

                need_merge = False

                if last_char not in end_punctuations:
                    if first_char.islower():
                        need_merge = True
                    elif '\u4e00' <= first_char <= '\u9fff':
                        need_merge = True
                    elif last_char == '-':
                        buffer = buffer[:-1]
                        need_merge = True

                if need_merge:
                    buffer += " " + line
                else:
                    merged_lines.append(buffer)
                    buffer = line

        if buffer:
            merged_lines.append(buffer)

        self.cleaned_text = "\n".join([line for line in merged_lines if len(line) > 5])

    def save(self, output_path):
        """动作5：保存文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.cleaned_text)


# ==========================================
# 主程序：智能路径处理 + 新文件夹保存
# ==========================================
def main():
    # 1. 确定输出文件夹的绝对路径
    # 策略：我们在 config.DATA_PATH 所在的目录下创建这个新文件夹
    # 如果 DATA_PATH 是文件，取其目录；如果是文件夹，直接取该目录
    if os.path.isfile(target_path):
        base_dir = os.path.dirname(target_path)
    elif os.path.isdir(target_path):
        base_dir = target_path
    else:
        print(f"❌ 路径无效: {target_path}")
        return

    # 拼接输出文件夹路径
    output_folder = os.path.join(base_dir, OUTPUT_DIR_NAME)

    # 2. 自动创建文件夹 (如果不存在)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"📂 已创建输出文件夹: {output_folder}")
    else:
        print(f"📂 输出文件夹已存在: {output_folder}")

    # 3. 收集待处理的 PDF 文件
    pdf_files = []

    if os.path.isfile(target_path):
        if target_path.lower().endswith('.pdf'):
            pdf_files.append(target_path)
    elif os.path.isdir(target_path):
        search_pattern = os.path.join(target_path, "*.pdf")
        pdf_files = glob.glob(search_pattern)
        if not pdf_files:
            print("⚠️ 该文件夹下没有找到 PDF 文件。")
            return

    print(f"🔍 共找到 {len(pdf_files)} 个文件，开始处理...")

    # 4. 循环处理
    for pdf_file in pdf_files:
        try:
            # 获取文件名（不含路径）
            file_name = os.path.basename(pdf_file)
            # 获取文件名（不含后缀）
            file_name_no_ext = os.path.splitext(file_name)[0]

            # 拼接新的保存路径：输出文件夹 + 新文件名.txt
            output_path = os.path.join(output_folder, f"{file_name_no_ext}_cleaned.txt")

            # 执行清洗
            cleaner = MedicalPDFCleaner(pdf_file)
            cleaner.extract_text()
            cleaner.clean_text()
            cleaner.save(output_path)

            print(f"✅ 处理完成: {file_name}")

        except Exception as e:
            print(f"❌ 处理 {pdf_file} 时出错: {e}")


if __name__ == "__main__":
    main()