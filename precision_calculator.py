# -*- coding: utf-8 -*-
"""
人工抽样准确率（Precision）自动计算脚本

使用方法：
1. 打开 evaluation_sample_100.tsv，在"人工判定"列填入 ✓ / △ / ✗
2. 运行 python precision_calculator.py
3. 结果输出到控制台和 precision_result.txt

评分标准：
- ✓ : 完全正确（计1.0分）
- △ : 基本正确，术语有小差异但不影响语义（计0.5分）
- ✗ : 错误，医学事实不成立或关系颠倒（计0.0分）
"""
import config  # 统一路径配置

import pandas as pd
from collections import Counter
import os

def calculate_precision(filepath="evaluation_sample_100.tsv"):
    if not os.path.exists(filepath):
        print(f"[ERROR] 找不到文件: {filepath}")
        return
    
    try:
        df = pd.read_csv(filepath, sep='\t', encoding='utf-8-sig')
    except Exception as e:
        print(f"[ERROR] 读取文件失败: {e}")
        return
    
    total = len(df)
    if total == 0:
        print("[ERROR] 文件为空")
        return
    
    # 检查是否已打分
    judge_col = '人工判定'
    if judge_col not in df.columns:
        print(f"[ERROR] 找不到'{judge_col}'列，请确认文件格式正确")
        return
    
    scores = df[judge_col].astype(str).str.strip()
    filled = scores[scores != ''].replace('nan', '')
    filled = filled[filled != '']
    
    if len(filled) == 0:
        print("=" * 60)
        print("尚未打分")
        print("=" * 60)
        print(f"请打开 {filepath}，在'{judge_col}'列填入 ✓ / △ / ✗")
        print("填完后再运行此脚本")
        return
    
    # 统计
    count_full = (scores == '✓').sum()
    count_half = (scores == '△').sum()
    count_zero = (scores == '✗').sum()
    count_empty = (scores == '').sum() + scores.isna().sum()
    
    # 严格Precision（只算✓）
    strict_precision = count_full / total * 100
    
    # 宽松Precision（✓ + △）
    loose_precision = (count_full + count_half) / total * 100
    
    # 加权Precision（✓=1.0, △=0.5, ✗=0.0）
    weighted_score = count_full * 1.0 + count_half * 0.5 + count_zero * 0.0
    weighted_precision = weighted_score / total * 100
    
    # 按关系类型统计
    rel_col = '关系类型' if '关系类型' in df.columns else df.columns[0]
    type_stats = []
    for rel_type, group in df.groupby(rel_col):
        g_scores = group[judge_col].astype(str).str.strip()
        g_full = (g_scores == '✓').sum()
        g_half = (g_scores == '△').sum()
        g_zero = (g_scores == '✗').sum()
        g_total = len(group)
        if g_total > 0:
            g_loose = (g_full + g_half) / g_total * 100
            type_stats.append({
                '关系类型': rel_type,
                '样本数': g_total,
                '✓': g_full,
                '△': g_half,
                '✗': g_zero,
                '宽松准确率(%)': round(g_loose, 1)
            })
    type_df = pd.DataFrame(type_stats)
    
    # 输出结果
    lines = []
    lines.append("=" * 60)
    lines.append("人工抽样准确率（Precision）计算结果")
    lines.append("=" * 60)
    lines.append(f"总样本数: {total}")
    lines.append(f"已打分: {int(count_full + count_half + count_zero)} / {total}")
    lines.append(f"未打分: {int(count_empty)}")
    lines.append("")
    lines.append(f"严格Precision（仅✓）: {count_full}/{total} = {strict_precision:.1f}%")
    lines.append(f"宽松Precision（✓+△）: {count_full+count_half}/{total} = {loose_precision:.1f}%")
    lines.append(f"加权Precision（✓=1, △=0.5）: {weighted_precision:.1f}%")
    lines.append("")
    lines.append("=" * 60)
    lines.append("按关系类型统计")
    lines.append("=" * 60)
    lines.append(type_df.to_string(index=False))
    lines.append("")
    lines.append("=" * 60)
    lines.append("评分说明")
    lines.append("=" * 60)
    lines.append("✓ = 完全正确（医学事实准确）")
    lines.append("△ = 基本正确（术语表述有差异但不影响语义）")
    lines.append("✗ = 错误（医学事实不成立或关系颠倒）")
    
    result = "\n".join(lines)
    print(result)
    
    # 保存到文件
    with open("precision_result.txt", "w", encoding="utf-8") as f:
        f.write(result)
    print("\n结果已保存到: precision_result.txt")

if __name__ == "__main__":
    calculate_precision()
