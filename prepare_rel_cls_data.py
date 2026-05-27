#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3 数据准备：从三元组TSV构建关系分类数据集
划分训练/验证/测试集，供多模型对比实验使用
"""
import config
import os
import json
import pandas as pd
from sklearn.model_selection import train_test_split

# 数据源路径（自动查找，避免Windows编码问题）
def find_source_tsv():
    for f in os.listdir(config.RELATION_DIR):
        if f.endswith('.tsv') and 'final' in f.lower():
            return config.RELATION_DIR / f
    raise FileNotFoundError("未找到数据源TSV文件")

SOURCE_TSV = find_source_tsv()
OUTPUT_DIR = config.BASE_DIR / "p3_comparison"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SEED = 42


def load_and_clean():
    """加载数据并清洗"""
    df = pd.read_csv(SOURCE_TSV, sep="\t", encoding="utf-8")
    print(f"[数据] 原始条数: {len(df)}")

    # 找到关键列（中文列名）
    rel_col = "关系类型"
    head_col = "头实体"
    tail_col = "尾实体"
    head_type_col = "头类型"
    tail_type_col = "尾类型"
    sent_col = "上下文句子"

    # 检查必要列
    required = [rel_col, head_col, tail_col, head_type_col, tail_type_col, sent_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"[错误] 缺少列: {missing}")
        print(f"[可用列] {list(df.columns)}")
        raise ValueError("列名不匹配")

    # 清洗：去除空句子
    df = df[df[sent_col].notna() & (df[sent_col].astype(str).str.strip() != "")]
    print(f"[数据] 去除空句子后: {len(df)}")

    # 构建标准化数据框
    data = pd.DataFrame({
        "relation": df[rel_col].astype(str).str.strip(),
        "head": df[head_col].astype(str).str.strip(),
        "tail": df[tail_col].astype(str).str.strip(),
        "head_type": df[head_type_col].astype(str).str.strip(),
        "tail_type": df[tail_type_col].astype(str).str.strip(),
        "sentence": df[sent_col].astype(str).str.strip(),
    })

    # 去除关系为空的
    data = data[data["relation"] != ""]
    print(f"[数据] 去除空关系后: {len(data)}")

    # 关系分布
    rel_dist = data["relation"].value_counts()
    print(f"[数据] 关系类型数: {len(rel_dist)}")
    for rel, cnt in rel_dist.items():
        print(f"  {rel}: {cnt}")

    return data, rel_dist


def stratify_split(data):
    """按关系类型分层划分数据集"""
    labels = data["relation"].values

    # 先划分出测试集（20%）
    try:
        train_val, test = train_test_split(
            data, test_size=0.2, random_state=SEED, stratify=labels
        )
    except ValueError:
        print("[警告] 分层抽样失败（某些类别样本过少），改用普通随机划分")
        train_val, test = train_test_split(
            data, test_size=0.2, random_state=SEED
        )

    # 再从train_val中划分验证集（占原始数据的20%，即train_val的25%）
    train_labels = train_val["relation"].values
    try:
        train, val = train_test_split(
            train_val, test_size=0.25, random_state=SEED, stratify=train_labels
        )
    except ValueError:
        print("[警告] 验证集分层抽样失败，改用普通随机划分")
        train, val = train_test_split(
            train_val, test_size=0.25, random_state=SEED
        )

    print(f"\n[划分] 训练集: {len(train)} | 验证集: {len(val)} | 测试集: {len(test)}")

    # 保存
    train_path = OUTPUT_DIR / "train.json"
    val_path = OUTPUT_DIR / "val.json"
    test_path = OUTPUT_DIR / "test.json"

    train.to_json(train_path, orient="records", force_ascii=False, indent=2)
    val.to_json(val_path, orient="records", force_ascii=False, indent=2)
    test.to_json(test_path, orient="records", force_ascii=False, indent=2)

    print(f"[保存] {train_path}")
    print(f"[保存] {val_path}")
    print(f"[保存] {test_path}")

    # 保存元数据
    meta = {
        "seed": SEED,
        "total": len(data),
        "train": len(train),
        "val": len(val),
        "test": len(test),
        "num_relations": data["relation"].nunique(),
        "relations": data["relation"].value_counts().to_dict(),
    }
    meta_path = OUTPUT_DIR / "meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[保存] {meta_path}")

    return train, val, test


def main():
    print("=" * 60)
    print("P3 数据准备 - 关系分类数据集构建")
    print("=" * 60)

    data, rel_dist = load_and_clean()
    train, val, test = stratify_split(data)

    print("\n[完成] 数据准备完毕，输出目录:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
