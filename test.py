import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COPD文献PDF提取与清洗系统 v2.0 - 保守清洗，保留英文与结构
"""

import os
import re
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("错误：缺少 pdfplumber，请执行：pip install pdfplumber")
    sys.exit(1)

# ==================== 路径配置 ====================
INPUT_FOLDER = r"I:\101实验专题\原始文献数据"
OUTPUT_FOLDER = r"I:\101实验专题\抽取结果_v2"  # 新路径，不覆盖旧结果
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ==================== PDF提取 ====================
def extract_pdf_raw(pdf_path):
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text and text.strip():
                pages_text.append(text.strip())
            else:
                pages_text.append(f"[PAGE_{i}_NO_TEXT]")
    return "\n".join(pages_text), len(pages_text)


# ==================== 保守文本清洗器 ====================
class ConservativeMedicalCleaner:
    def __init__(self):
        # 1. 明确的页眉模式（只删整行匹配期刊名/版权的）
        self.re_journal_header = re.compile(
            r'^\s*(?:'
            r'中国中西医结合杂志|中华结核和呼吸杂志|中华内科杂志|中国中药杂志|中医杂志|'
            r'世界中医药|中国中医急症|临床肺科杂志|中国实用医药|实用临床医学|'
            r'中国慢性病预防与控制|中国误诊学杂志|中国医药导报|中国医药指南|'
            r'中国城乡企业卫生|中国美容医学|中国医疗前沿|中国中医药现代远程教育|'
            r'中国继续医学教育|中国生化药物杂志|辽宁中医杂志|山东中医杂志|'
            r'陕西中医|四川中医|湖南中医杂志|浙江中西医结合杂志|天津中医药|'
            r'天津中医药大学学报|北京中医药大学学报|上海中医药杂志|'
            r'广西中医药大学学报|贵阳中医学院学报|河南中医|河北中医|山西中医|'
            r'新中医|中医药导报|中医药学报|中药材|中药药理与临床|亚太传统医药|'
            r'北方药学|海峡药学|当代医学|医学信息|中国社区医师|基层医学论坛|'
            r'养生保健指南|心理医生杂志|右江医学|淮海医药|宁夏医科大学学报|'
            r'延安大学学报|河南医学研究|川北医学院学报|大家健康|世界临床医学|'
            r'中华[^，。]*?杂志|中国[^，。]*?杂志|'
            r'Journal of [^，。]+?|Lancet|Chest|BMJ|CMAJ|Int J Chronic Obstr|'
            r'Lancet Respir Med|J Clin Epidemiol|Global Burden of Disease|'
            r'Am J Respir|Eur Respir|Respir Med|Thorax|'
            r'©\s*\d{4}.*?(?:Ltd|Inc|Press|Group|Association)\s*$'
            r')\s*$',
            re.IGNORECASE
        )

        # 2. 明确的页脚元数据（只删独立成行）
        self.re_footer_meta = re.compile(
            r'^\s*(?:'
            r'基金项目[：:].*?|'
            r'通讯作者[：:].*?|'
            r'责任作者[：:].*?|'
            r'DOI[：:]\s*\S+|'
            r'收稿日期?[：:].*?|'
            r'在线发表?[：:].*?|'
            r'修回日期?[：:].*?|'
            r'录用日期?[：:].*?|'
            r'责任编辑[：:].*?|'
            r'编辑[：:].*?|'
            r'英文编辑[：:].*?|'
            r'出版日期?[：:].*?|'
            r'文章编号[：:].*?|'
            r'中图分类号[：:].*?|'
            r'文献标识码[：:].*?|'
            r'网络出版时间[：:].*?|'
            r'网络出版地址[：:].*?|'
            r'Responsibility[：:].*?|'
            r'Correspondence[：:].*?|'
            r'Accepted[：:].*?|'
            r'Received[：:].*?|'
            r'Published[：:].*?|'
            r'All rights reserved.*?'  # 必须单独成行
            r')\s*$',
            re.IGNORECASE
        )

        # 3. 参考文献截断（更保守：要求标题单独成行且后面紧跟参考文献格式）
        self.re_ref_start = re.compile(
            r'^\s*(?:'
            r'参\s*考\s*文\s*献|'
            r'References?\s*$|'
            r'Bibliography\s*$|'
            r'【参考文献】|'
            r'［参考文献］|'
            r'References?\s+and\s+Notes?'
            r')',
            re.IGNORECASE
        )

        # 4. 网址（行内替换为空格，不删整行）
        self.re_url = re.compile(r'https?://\S+|www\.\S+')

        # 5. 孤立的页码行（整行只有数字和少量符号）
        self.re_isolated_page_num = re.compile(r'^\s*[•·‥\-—\s]*\d+[•·‥\-—\s]*\s*$')

        # 6. 纯垃圾符号行（无字母汉字数字，且很短）
        self.re_garbage_line = re.compile(r'^[^\w一-龥\u4e00-\u9fff]+\s*$')

    def clean(self, raw_text):
        if not raw_text or not raw_text.strip():
            return ""

        text = raw_text

        # 阶段1：逐行清洗（保留结构）
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.rstrip()
            if not line.strip():
                cleaned_lines.append('')
                continue

            # 删明确的页眉（整行匹配期刊名）
            if self.re_journal_header.match(line):
                continue

            # 删明确的页脚元数据（整行匹配）
            if self.re_footer_meta.match(line):
                continue

            # 删孤立页码行
            if self.re_isolated_page_num.match(line):
                continue

            # 删纯符号垃圾行（很短才删）
            if self.re_garbage_line.match(line) and len(line) < 30:
                continue

            # 行内去网址（替换为空格）
            line = self.re_url.sub(' ', line)

            cleaned_lines.append(line)

        text = '\n'.join(cleaned_lines)

        # 阶段2：保守截断参考文献
        text = self._truncate_references(text)

        # 阶段3：智能合并断行（区分中英文，保护表格/列表）
        text = self._smart_merge_lines(text)

        # 阶段4：规范化空白
        text = self._normalize_whitespace(text)

        return text.strip()

    def _truncate_references(self, text):
        """保守截断：只匹配单独成行的参考文献标题，且下一行像参考文献"""
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if self.re_ref_start.match(line):
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # 下一行像参考文献：数字编号[1]或作者姓开头
                    if re.match(r'^\s*\[\d+\]|^\s*\d+\.|^\s*[A-Z][a-z]+', next_line):
                        return '\n'.join(lines[:i])
        return text

    def _smart_merge_lines(self, text):
        """智能合并：区分中英文断行，保护列表/表格/标题"""
        lines = text.split('\n')
        merged = []

        for line in lines:
            line = line.rstrip()
            if not line:
                if merged and merged[-1] != '':
                    merged.append('')
                continue

            if not merged:
                merged.append(line)
                continue

            last = merged[-1]
            if not last:
                merged.append(line)
                continue

            # 判断是否应该合并
            should_merge = False

            # 规则A：上一行以连字符（单词断行）结尾 → 必须合并
            if re.search(r'[a-zA-Z]-\s*$', last):
                should_merge = True

            # 规则B：判断下一行是否是"新段落开头"
            is_new_para = (
                    re.match(r'^\s*\d+[\.\s]', line) or  # 数字列表 1. 2.
                    re.match(r'^\s*[一二三四五六七八九十][、\.]', line) or  # 中文数字
                    re.match(r'^\s*(?:Abstract|Introduction|Methods|Results|Discussion|'
                             r'Conclusion|Background|Objectives|Keywords|Key words)', line, re.I) or
                    re.match(r'^\s*(?:摘要|关键词|目的|方法|结果|结论|背景|引言)', line) or
                    re.match(r'^\s*(?:Table|Figure|Fig\.|表|图)\s*\d+', line, re.I) or
                    re.match(r'^\s*[-•·※■□◆◇○●★☆]', line)  # 项目符号
            )

            # 规则C：上一行结束标点判断
            has_zh_ending = bool(re.search(r'[。！？；，、]\s*$', last))  # 中文结束
            has_en_ending = bool(re.search(r'[\.!\?;:,]\s*$', last))  # 英文结束

            # 规则D：英文段落续行（下一行小写开头，大概率同一段）
            is_en_continue = bool(re.match(r'^[a-z]', line))

            if not is_new_para:
                # 中文：无结束标点 → 合并
                if not has_zh_ending and not has_en_ending:
                    should_merge = True
                # 英文：无结束标点 + 下一行小写 → 合并
                elif is_en_continue and not has_en_ending:
                    should_merge = True

            if should_merge:
                # 处理单词断行（去掉连字符）
                if re.search(r'[a-zA-Z]-\s*$', last):
                    merged[-1] = last.rstrip('-') + line.lstrip()
                else:
                    # 合并时加空格（如果上一行末尾没有空格）
                    sep = '' if last.endswith(' ') else ' '
                    merged[-1] = last + sep + line.lstrip()
            else:
                merged.append(line)

        return '\n'.join(merged)

    def _normalize_whitespace(self, text):
        """规范化空白：保留段落结构，清理行内多余空格"""
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                cleaned.append('')
                continue
            # 保留行首缩进（可能是表格/列表对齐）
            indent = len(line) - len(line.lstrip())
            indent_str = line[:indent] if indent >= 2 else ''
            # 清理行内多余空格
            content = ' '.join(stripped.split())
            cleaned.append(indent_str + content)

        # 合并连续空行（最多保留一个）
        result = []
        prev_empty = False
        for line in cleaned:
            is_empty = not line.strip()
            if is_empty and prev_empty:
                continue
            result.append(line)
            prev_empty = is_empty

        return '\n'.join(result)


# ==================== 批量处理 ====================
def batch_process(pdf_folder, output_folder):
    cleaner = ConservativeMedicalCleaner()
    pdf_files = sorted([f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')])

    print("=" * 70)
    print(" COPD文献PDF提取与清洗系统 v2.0（保守清洗）")
    print(f" 输入: {pdf_folder}")
    print(f" 输出: {output_folder}")
    print(f" 文献: {len(pdf_files)} 篇")
    print("=" * 70)

    results = []
    success_count = 0
    fail_count = 0

    for idx, fname in enumerate(pdf_files, 1):
        fpath = os.path.join(pdf_folder, fname)
        print(f"\n[{idx}/{len(pdf_files)}] {fname}")

        try:
            raw_text, page_count = extract_pdf_raw(fpath)
            raw_chars = len(raw_text)
            cleaned_text = cleaner.clean(raw_text)
            cleaned_chars = len(cleaned_text)

            result = {
                "filename": fname,
                "status": "success",
                "pages": page_count,
                "raw_chars": raw_chars,
                "cleaned_chars": cleaned_chars,
                "reduction_rate": round((1 - cleaned_chars / raw_chars) * 100, 2) if raw_chars else 0,
                "cleaned_text": cleaned_text
            }
            results.append(result)
            success_count += 1
            print(
                f"   ✓ {page_count}页 | 原文{raw_chars:,}字 | 清洗后{cleaned_chars:,}字 | 压缩{result['reduction_rate']}%")

        except Exception as e:
            fail_count += 1
            results.append({"filename": fname, "status": "failed", "error": str(e)})
            print(f"   ✗ 失败: {e}")

    # 保存JSON
    json_path = os.path.join(output_folder, "step1_cleaned_papers.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 保存纯文本
    txt_folder = os.path.join(output_folder, "cleaned_texts")
    os.makedirs(txt_folder, exist_ok=True)
    for r in results:
        if r.get("status") == "success":
            txt_name = Path(r["filename"]).stem + ".txt"
            with open(os.path.join(txt_folder, txt_name), 'w', encoding='utf-8') as f:
                f.write(r["cleaned_text"])

    # 报告
    report = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(pdf_files),
        "success": success_count,
        "failed": fail_count,
        "rate": f"{success_count / len(pdf_files) * 100:.1f}%" if pdf_files else "N/A"
    }
    with open(os.path.join(output_folder, "extraction_report.json"), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print(f" 完成 | 成功:{success_count} | 失败:{fail_count} | 成功率:{report['rate']}")
    print(f" 输出: {json_path}")
    print(f" 文本: {txt_folder}/")
    print("=" * 70)


if __name__ == "__main__":
    if not os.path.exists(INPUT_FOLDER):
        print(f"错误：路径不存在 {INPUT_FOLDER}")
        sys.exit(1)
    batch_process(INPUT_FOLDER, OUTPUT_FOLDER)