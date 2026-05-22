#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BERT 关系分类批量预测脚本
用法：对已有三元组数据用 BERT 模型重新预测关系，对比规则方法的结果
"""

import os
import sys
import json
import argparse
from pathlib import Path

import pandas as pd
import numpy as np

import config  # 统一路径配置
from bert_relation_classifier import RelationPredictor


def load_triples(path: str):
    """加载三元组数据，支持 JSON 和 TSV 格式"""
    path = Path(path)
    if path.suffix.lower() == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 统一字段名
        records = []
        for item in data:
            records.append({
                'head': item.get('head', item.get('头实体', '')),
                'tail': item.get('tail', item.get('尾实体', '')),
                'relation': item.get('relation', item.get('关系类型', '')),
                'sentence': item.get('sentence', item.get('上下文句子', '')),
                'head_type': item.get('head_type', item.get('头类型', '')),
                'tail_type': item.get('tail_type', item.get('尾类型', '')),
            })
        return pd.DataFrame(records)
    
    elif path.suffix.lower() in ('.tsv', '.txt'):
        df = pd.read_csv(path, sep='\t', encoding='utf-8')
        # 中文字段名转英文
        col_map = {
            '头实体': 'head',
            '尾实体': 'tail',
            '关系类型': 'relation',
            '上下文句子': 'sentence',
            '头类型': 'head_type',
            '尾类型': 'tail_type',
        }
        for cn, en in col_map.items():
            if cn in df.columns:
                df[en] = df[cn]
        return df
    
    else:
        raise ValueError(f"不支持的文件格式: {path.suffix}")


def batch_predict(df: pd.DataFrame, model_path: str, output_path: str):
    """批量预测并保存结果"""
    device = getattr(config, 'DEVICE', None)
    predictor = RelationPredictor(model_path, device)
    
    results = []
    total = len(df)
    
    print(f"\n[批量预测] 共 {total} 条三元组")
    print(f"模型: {model_path}")
    print("=" * 60)
    
    for idx, row in df.iterrows():
        sentence = str(row.get('sentence', '')) if pd.notna(row.get('sentence')) else ''
        head = str(row.get('head', '')) if pd.notna(row.get('head')) else ''
        tail = str(row.get('tail', '')) if pd.notna(row.get('tail')) else ''
        original_relation = str(row.get('relation', '')) if pd.notna(row.get('relation')) else ''
        
        # BERT 预测
        pred = predictor.predict(sentence, head, tail)
        
        results.append({
            'head': head,
            'tail': tail,
            'head_type': row.get('head_type', ''),
            'tail_type': row.get('tail_type', ''),
            'sentence': sentence[:200] + '...' if len(sentence) > 200 else sentence,
            'original_relation': original_relation,
            'bert_relation': pred['predicted_relation'],
            'bert_confidence': round(pred['confidence'], 4),
            'bert_top2': pred['top3'][1]['relation'] if len(pred['top3']) > 1 else '',
            'bert_top2_conf': round(pred['top3'][1]['probability'], 4) if len(pred['top3']) > 1 else 0,
            'bert_top3': pred['top3'][2]['relation'] if len(pred['top3']) > 2 else '',
            'bert_top3_conf': round(pred['top3'][2]['probability'], 4) if len(pred['top3']) > 2 else 0,
            'is_consistent': pred['predicted_relation'] == original_relation,
        })
        
        if (idx + 1) % 50 == 0 or idx == total - 1:
            print(f"  进度: {idx + 1}/{total} ({(idx+1)/total*100:.1f}%)")
    
    # 保存结果
    out_df = pd.DataFrame(results)
    out_df.to_csv(output_path, sep='\t', index=False, encoding='utf-8')
    
    # 统计
    consistent = out_df['is_consistent'].sum()
    inconsistent = len(out_df) - consistent
    
    print(f"\n{'=' * 60}")
    print("预测完成")
    print(f"结果保存: {output_path}")
    print(f"{'=' * 60}")
    print(f"总条数: {len(out_df)}")
    print(f"BERT 与规则方法一致: {consistent} ({consistent/len(out_df)*100:.1f}%)")
    print(f"BERT 与规则方法不一致: {inconsistent} ({inconsistent/len(out_df)*100:.1f}%)")
    
    # 不一致的详细分析
    if inconsistent > 0:
        print(f"\n不一致样本分析:")
        diff_df = out_df[~out_df['is_consistent']]
        cross = pd.crosstab(diff_df['original_relation'], diff_df['bert_relation'])
        print(cross.to_string())
    
    return out_df


def compare_with_final(gold_path: str, pred_path: str):
    """与人工审核的最终版对比，计算准确率"""
    gold = load_triples(gold_path)
    pred = pd.read_csv(pred_path, sep='\t', encoding='utf-8')
    
    # 合并对比
    merged = pred.merge(
        gold[['head', 'tail', 'relation']].rename(columns={'relation': 'gold_relation'}),
        on=['head', 'tail'],
        how='inner'
    )
    
    if len(merged) == 0:
        print("未找到匹配的三元组用于对比")
        return
    
    correct = (merged['bert_relation'] == merged['gold_relation']).sum()
    print(f"\n与人工审核版对比 ({len(merged)} 条共同三元组):")
    print(f"BERT 预测正确: {correct}/{len(merged)} ({correct/len(merged)*100:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BERT 关系分类批量预测")
    parser.add_argument("--input", "-i", type=str,
                        default=str(config.RELATION_DIR / "v4_最大覆盖版_原始三元组_带溯源.json"),
                        help="输入三元组文件 (JSON 或 TSV)")
    parser.add_argument("--model", "-m", type=str,
                        default=str(config.BERT_OUTPUT_DIR / "best_model.pt"),
                        help="BERT 模型路径")
    parser.add_argument("--output", "-o", type=str,
                        default=str(config.BERT_OUTPUT_DIR / "bert_predictions.tsv"),
                        help="输出预测结果路径")
    parser.add_argument("--compare", "-c", type=str, default="",
                        help="与人工审核的最终版对比 (TSV/JSON)")
    
    args = parser.parse_args()
    
    # 加载数据
    df = load_triples(args.input)
    print(f"[加载] {args.input} | {len(df)} 条")
    
    # 批量预测
    result_df = batch_predict(df, args.model, args.output)
    
    # 可选：与最终版对比
    if args.compare:
        compare_with_final(args.compare, args.output)
