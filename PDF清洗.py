#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COPD文献PDF提取与清洗系统 v1.0
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
OUTPUT_FOLDER = r"I:\101实验专题\抽取结果"
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


# ==================== 文本清洗器 ====================
class MedicalTextCleaner:
    def __init__(self):
        # 中文期刊页眉
        self.re_header_cn = re.compile(
            r'(?:中国中西医结合杂志|中华结核和呼吸杂志|中华内科杂志|中国中药杂志|中医杂志|'
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
            r'Journal of .+?|Lancet|Chest|BMJ|CMAJ|Int J Chronic Obstr|'
            r'Lancet Respir Med|J Clin Epidemiol|Global Burden of Disease|'
            r'中华.+?杂志|中国.+?杂志)'
            r'.*?(?:\d{4}年.+?卷.+?期|Vol\.\d+.*?,No\.\d+|\d{4},\d+\(\d+\):\d+-\d+)',
            re.IGNORECASE
        )
        # 页码标记
        self.re_page_markers = re.compile(r'[•·‥\s]*\d+[•·‥\s]*')
        # 页脚元数据
        self.re_footer_meta = re.compile(
            r'(?:基金项目[：:].*?(?:\n|$)|通讯作者[：:].*?(?:\n|$)|'
            r'责任作者[：:].*?(?:\n|$)|Responsibility[：:].*?(?:\n|$)|'
            r'DOI[：:]\s*\S+|收稿[：:].*?(?:\n|$)|在线[：:].*?(?:\n|$)|'
            r'修回日期[：:].*?(?:\n|$)|录用日期[：:].*?(?:\n|$)|'
            r'责任编辑[：:].*?(?:\n|$)|编辑[：:].*?(?:\n|$)|'
            r'英文编辑[：:].*?(?:\n|$)|出版日期[：:].*?(?:\n|$)|'
            r'文章编号[：:].*?(?:\n|$)|中图分类号[：:].*?(?:\n|$)|'
            r'文献标识码[：:].*?(?:\n|$)|网络出版时间[：:].*?(?:\n|$)|'
            r'网络出版地址[：:].*?(?:\n|$))',
            re.IGNORECASE | re.MULTILINE
        )
        # 参考文献截断
        self.re_ref_start = re.compile(
            r'(?:参\s*考\s*文\s*献|References?\s*(?:\n|$)|Bibliography\s*(?:\n|$)|'
            r'【参考文献】|［参考文献］)',
            re.IGNORECASE
        )
        # 网址
        self.re_url = re.compile(r'https?://\S+|www\.\S+')
        # 多余空白
        self.re_multi_space = re.compile(r'[ \t]+')
        self.re_multi_newline = re.compile(r'\n{3,}')
        # 英文期刊页眉
        self.re_header_en = re.compile(
            r'(?:CJITWM,.*?\d{4},Vol\.\d+,No\.\d+|Chin J Integr Med.*?\d{4}|'
            r'©\s*\d{4}.*?(?:Ltd|Inc|Press)|All rights reserved.*?(?:\n|$))',
            re.IGNORECASE
        )

    def clean(self, raw_text):
        if not raw_text or not raw_text.strip():
            return ""

        text = raw_text

        # 逐行去除页眉页脚
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            if self._is_header_or_footer_line(line):
                continue
            cleaned_lines.append(line)
        text = '\n'.join(cleaned_lines)

        # 去除页码标记
        text = self.re_page_markers.sub('', text)
        # 去除页脚元数据
        text = self.re_footer_meta.sub('', text)
        # 去除网址
        text = self.re_url.sub('', text)
        # 截断参考文献
        text = self._truncate_references(text)
        # 合并断行
        text = self._merge_broken_lines(text)
        # 去除多余空白
        text = self.re_multi_space.sub(' ', text)
        text = self.re_multi_newline.sub('\n\n', text)
        # 去除垃圾行
        text = self._remove_garbage_lines(text)

        return text.strip()

    def _is_header_or_footer_line(self, line):
        line = line.strip()
        if not line:
            return False
        if re.match(r'^\s*\d+\s*$', line):
            return True
        if self.re_header_cn.search(line):
            return True
        if self.re_header_en.search(line):
            return True
        if self.re_footer_meta.match(line):
            return True
        if len(line) < 4 and not re.search(r'[一-龥a-zA-Z]{2,}', line):
            return True
        return False

    def _truncate_references(self, text):
        match = self.re_ref_start.search(text)
        if match:
            return text[:match.start()]
        return text

    def _merge_broken_lines(self, text):
        lines = text.split('\n')
        merged = []
        for line in lines:
            line = line.strip()
            if not line:
                merged.append('')
                continue
            if not merged:
                merged.append(line)
                continue

            last_line = merged[-1]
            if not last_line:
                merged.append(line)
                continue

            ends_with_punct = bool(re.search(r'[。！？；.!?]\s*$', last_line))
            is_new_paragraph = bool(re.match(r'^\s+', line)) or bool(re.match(r'^\d+[\.．、]', line))

            if not ends_with_punct and not is_new_paragraph:
                merged[-1] = last_line + line
            else:
                merged.append(line)

        return '\n'.join(merged)

    def _remove_garbage_lines(self, text):
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            line_stripped = line.strip()
            if re.match(r'^[^\w一-龥]+$', line_stripped) and len(line_stripped) < 10:
                continue
            if len(line_stripped) > 0 and len(re.findall(r'[一-龥a-zA-Z0-9]', line_stripped)) / len(
                    line_stripped) < 0.3:
                if len(line_stripped) < 20:
                    continue
            cleaned.append(line)
        return '\n'.join(cleaned)


# ==================== 批量处理 ====================
def batch_process(pdf_folder, output_folder):
    cleaner = MedicalTextCleaner()

    pdf_files = sorted([f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')])

    print("=" * 70)
    print(" COPD文献PDF提取与清洗系统")
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
            line_count = cleaned_text.count('\n') + 1 if cleaned_text else 0

            result = {
                "filename": fname,
                "status": "success",
                "pages": page_count,
                "raw_chars": raw_chars,
                "cleaned_chars": cleaned_chars,
                "lines": line_count,
                "reduction_rate": round((1 - cleaned_chars / raw_chars) * 100, 2) if raw_chars else 0,
                "raw_text_preview": raw_text[:500],
                "cleaned_text": cleaned_text
            }
            results.append(result)
            success_count += 1
            print(
                f"   ✓ {page_count}页 | 原文{raw_chars}字 | 清洗后{cleaned_chars}字 | 压缩{result['reduction_rate']}%")

        except Exception as e:
            fail_count += 1
            results.append({
                "filename": fname,
                "status": "failed",
                "error": str(e)
            })
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