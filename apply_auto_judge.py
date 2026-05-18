# -*- coding: utf-8 -*-
"""
将自动预审结果应用到抽样表中，并计算Precision

用法:
    1. 先运行 auto_judge.py 生成 evaluation_sample_100_auto.tsv
    2. 运行本脚本：python apply_auto_judge.py
    3. 人工复核 evaluation_sample_100.tsv 中的"人工判定"列
    4. 确认无误后运行本脚本计算 Precision：python apply_auto_judge.py --calc

注意：自动预审不等于人工审核，务必逐条复核 △ 标记的条目！
"""

import pandas as pd
import argparse
import os
import sys

def apply_judgment():
    """将自动判定结果填入人工判定列"""
    auto_file = "evaluation_sample_100_auto.tsv"
    target_file = "evaluation_sample_100.tsv"
    output_file = "evaluation_sample_100_filled.tsv"
    
    if not os.path.exists(auto_file):
        print(f"[ERROR] 找不到自动预审结果文件: {auto_file}")
        print("请先运行: python auto_judge.py")
        return False
    
    df = pd.read_csv(target_file, sep='\t', encoding='utf-8-sig')
    df_auto = pd.read_csv(auto_file, sep='\t', encoding='utf-8-sig')
    
    # 将自动判定复制到人工判定列
    df['人工判定'] = df_auto['自动判定']
    df['问题说明'] = df_auto['判定理由']
    df['置信度'] = df_auto['置信度']
    
    # 保存到新文件（避免WPS占用原文件）
    df.to_csv(output_file, sep='\t', index=False, encoding='utf-8-sig')
    
    # 统计
    counts = df['人工判定'].value_counts()
    correct = counts.get('✓', 0)
    partial = counts.get('△', 0)
    wrong = counts.get('✗', 0)
    total = len(df)
    
    print("=" * 60)
    print("自动判定结果已填入 evaluation_sample_100_filled.tsv")
    print("=" * 60)
    print(f"总样本: {total}")
    print(f"[正确] : {correct} 条 ({correct/total*100:.1f}%)")
    print(f"[存疑] : {partial} 条 ({partial/total*100:.1f}%)")
    print(f"[错误] : {wrong} 条 ({wrong/total*100:.1f}%)")
    print("\n重要提示：")
    print("   以上结果为系统自动预审，不等同于人工审核！")
    print(f"   请务必重点复核标记为 [存疑] 的 {partial} 条记录。")
    print("   复核完成后，保存文件再运行: python apply_auto_judge.py --calc")
    return True

def calculate_precision():
    """基于人工判定结果计算Precision"""
    target_file = "evaluation_sample_100.tsv"
    
    if not os.path.exists(target_file):
        print(f"[ERROR] 找不到文件: {target_file}")
        return False
    
    df = pd.read_csv(target_file, sep='\t', encoding='utf-8-sig')
    
    # 检查是否有未填写的
    empty = df['人工判定'].isna().sum()
    if empty > 0:
        print(f"[WARNING] 还有 {empty} 条记录的'人工判定'列为空，请先完成复核！")
        print("空记录索引:", df[df['人工判定'].isna()].index.tolist())
        return False
    
    counts = df['人工判定'].value_counts()
    correct = counts.get('✓', 0)
    partial = counts.get('△', 0)
    wrong = counts.get('✗', 0)
    total = len(df)
    
    strict_precision = correct / total * 100          # 严格：只算✓
    loose_precision = (correct + partial) / total * 100  # 宽松：✓+△都算对
    
    print("=" * 60)
    print("Precision 计算结果")
    print("=" * 60)
    print(f"总样本数:        {total}")
    print(f"正确:        {correct} 条")
    print(f"部分正确:    {partial} 条")
    print(f"错误:        {wrong} 条")
    print()
    print(f"严格Precision (仅✓):     {strict_precision:.2f}%")
    print(f"宽松Precision (✓+△):    {loose_precision:.2f}%")
    print("=" * 60)
    
    # 写入报告
    report_file = "PRECISION_RESULT.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("知识图谱关系抽取 Precision 评估报告\n")
        f.write("=" * 60 + "\n")
        f.write(f"评估日期: 2026-05-18\n")
        f.write(f"样本规模: 100条（从675条总体中随机抽取，seed=42）\n")
        f.write(f"评估方法: 基于COPD医学知识库的自动预审 + 人工复核\n\n")
        f.write("统计结果:\n")
        f.write(f"  正确 (✓):     {correct} 条\n")
        f.write(f"  部分正确 (△): {partial} 条\n")
        f.write(f"  错误 (✗):     {wrong} 条\n")
        f.write(f"  总计:         {total} 条\n\n")
        f.write(f"严格Precision (仅✓):    {strict_precision:.2f}%\n")
        f.write(f"宽松Precision (✓+△):   {loose_precision:.2f}%\n")
        f.write("=" * 60 + "\n")
        f.write("说明: 本评估基于抽样推断总体质量，置信水平95%。\n")
    
    print(f"\n结果已保存到: {report_file}")
    return True

def main():
    parser = argparse.ArgumentParser(description="自动预审结果应用与Precision计算")
    parser.add_argument('--calc', action='store_true', help='仅计算Precision（需先完成人工复核）')
    args = parser.parse_args()
    
    if args.calc:
        calculate_precision()
    else:
        apply_judgment()

if __name__ == "__main__":
    main()
