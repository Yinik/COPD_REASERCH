#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3 结果可视化：生成消融实验对比图表
"""
import config
import os
import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 150

RESULTS_DIR = config.BASE_DIR / "p3_comparison" / "results"
OUTPUT_DIR = config.BASE_DIR / "assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CONFIG_NAMES = {
    "baseline": "基线（实体标记+类别权重）",
    "no_entity_markers": "无实体标记",
    "no_class_weights": "无类别权重",
    "high_dropout": "高dropout=0.3",
}

COLORS = ["#6EC6FF", "#A8D5BA", "#FFE082", "#FFB6B9"]


def load_results():
    """加载所有配置的结果"""
    results = {}
    for cfg_name in CONFIG_NAMES.keys():
        path = RESULTS_DIR / f"{cfg_name}_result.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                results[cfg_name] = json.load(f)
    return results


def plot_macro_f1_comparison(results):
    """图1：各配置Macro-F1对比柱状图"""
    if not results:
        print("[WARN] 无结果数据")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    names = list(results.keys())
    labels = [CONFIG_NAMES.get(n, n) for n in names]
    f1_scores = [results[n]["test_metrics"]["f1_macro"] for n in names]
    acc_scores = [results[n]["test_metrics"]["accuracy"] for n in names]

    x = np.arange(len(names))
    width = 0.35

    bars1 = ax.bar(x - width/2, f1_scores, width, label="Macro-F1", color="#6EC6FF", edgecolor="#333", linewidth=0.8)
    bars2 = ax.bar(x + width/2, acc_scores, width, label="Accuracy", color="#A8D5BA", edgecolor="#333", linewidth=0.8)

    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.01,
                f'{bar.get_height():.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.01,
                f'{bar.get_height():.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_ylabel("Score", fontsize=12)
    ax.set_title("P3 消融实验：不同配置下的BERT关系分类性能", fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.legend(fontsize=11)
    ax.set_ylim(0, 1.1)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    out_path = OUTPUT_DIR / "p3_ablation_macro_f1.png"
    plt.savefig(out_path, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"[保存] {out_path}")


def plot_training_curves(results):
    """图2：各配置训练曲线对比"""
    if not results:
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Val F1 curve
    ax1 = axes[0]
    for cfg_name, res in results.items():
        hist = res["history"]
        epochs = [h["epoch"] for h in hist]
        f1_macros = [h["val_f1_macro"] for h in hist]
        ax1.plot(epochs, f1_macros, marker='o', label=CONFIG_NAMES.get(cfg_name, cfg_name), linewidth=2)
    ax1.set_xlabel("Epoch", fontsize=12)
    ax1.set_ylabel("Val Macro-F1", fontsize=12)
    ax1.set_title("验证集Macro-F1随epoch变化", fontsize=13, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(linestyle='--', alpha=0.4)
    ax1.set_axisbelow(True)

    # Val Loss curve
    ax2 = axes[1]
    for cfg_name, res in results.items():
        hist = res["history"]
        epochs = [h["epoch"] for h in hist]
        losses = [h["val_loss"] for h in hist]
        ax2.plot(epochs, losses, marker='s', label=CONFIG_NAMES.get(cfg_name, cfg_name), linewidth=2)
    ax2.set_xlabel("Epoch", fontsize=12)
    ax2.set_ylabel("Val Loss", fontsize=12)
    ax2.set_title("验证集Loss随epoch变化", fontsize=13, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.grid(linestyle='--', alpha=0.4)
    ax2.set_axisbelow(True)

    plt.tight_layout()
    out_path = OUTPUT_DIR / "p3_training_curves.png"
    plt.savefig(out_path, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"[保存] {out_path}")


def plot_per_class_f1(results):
    """图3：基线配置的每类F1热力图"""
    if "baseline" not in results:
        return

    baseline = results["baseline"]
    per_class = baseline["test_metrics"]["per_class"]
    rels = sorted(per_class.keys())
    f1s = [per_class[r]["f1"] for r in rels]
    supports = [per_class[r]["support"] for r in rels]

    fig, ax = plt.subplots(figsize=(10, 7))
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(rels)))[::-1]
    bars = ax.barh(rels[::-1], f1s[::-1], color=colors, edgecolor='#333', linewidth=0.6, height=0.65)

    for bar, f1, sup in zip(bars, f1s[::-1], supports[::-1]):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2.,
                f'{f1:.3f} (n={sup})', ha='left', va='center', fontsize=9, color='#333')

    ax.set_xlabel("F1 Score", fontsize=12)
    ax.set_title("基线配置 - 每类关系F1分数", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlim(0, 1.15)
    ax.grid(axis='x', linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    out_path = OUTPUT_DIR / "p3_per_class_f1.png"
    plt.savefig(out_path, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"[保存] {out_path}")


def generate_markdown_table(results):
    """生成Markdown对比表"""
    lines = []
    lines.append("| 配置 | 描述 | Test Acc | Macro-F1 | Weighted-F1 | 训练时间(min) |")
    lines.append("|------|------|----------|----------|-------------|--------------|")
    for cfg_name, res in results.items():
        desc = CONFIG_NAMES.get(cfg_name, cfg_name)
        tm = res["elapsed_seconds"] / 60
        tm_str = f"{tm:.1f}"
        lines.append(
            f"| {cfg_name} | {desc} | "
            f"{res['test_metrics']['accuracy']:.4f} | "
            f"{res['test_metrics']['f1_macro']:.4f} | "
            f"{res['test_metrics']['f1_weighted']:.4f} | {tm_str} |"
        )
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("P3 结果可视化")
    print("=" * 60)

    results = load_results()
    if not results:
        print("[错误] 未找到任何结果文件，请先运行 p3_train_compare.py")
        return

    print(f"[加载] {len(results)} 个配置的结果")

    plot_macro_f1_comparison(results)
    plot_training_curves(results)
    plot_per_class_f1(results)

    print("\n[Markdown对比表]")
    print(generate_markdown_table(results))

    # 保存Markdown
    md_path = RESULTS_DIR / "comparison_table.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# P3 消融实验结果\n\n")
        f.write(generate_markdown_table(results))
        f.write("\n")
    print(f"\n[保存] {md_path}")


if __name__ == "__main__":
    main()
