# -*- coding: utf-8 -*-
"""
生成Precision评估可视化图表
"""
import config  # 统一路径配置
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

df = pd.read_csv('evaluation_sample_100_final.tsv', sep='\t', encoding='utf-8-sig')

# 统计
ok = (df['人工判定'] == '\u2713').sum()
wrong = (df['人工判定'] == '\u2717').sum()

# ===== 图1: 总体Precision饼图 =====
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# 饼图
colors = ['#4CAF50', '#F44336']
wedges, texts, autotexts = axes[0].pie(
    [ok, wrong], labels=['正确 (76%)', '错误 (24%)'],
    autopct='%1.0f条', colors=colors, startangle=90,
    explode=(0.02, 0.02), textprops={'fontsize': 12}
)
axes[0].set_title('100条抽样三元组 Precision 评估', fontsize=14, fontweight='bold')

# 错误类型分布柱状图
wrong_df = df[df['人工判定'] == '\u2717']
wrong_by_rel = wrong_df['关系类型'].value_counts()
axes[1].barh(wrong_by_rel.index, wrong_by_rel.values, color='#F44336', alpha=0.8)
axes[1].set_xlabel('错误条数', fontsize=11)
axes[1].set_title('24条错误按关系类型分布', fontsize=14, fontweight='bold')
for i, v in enumerate(wrong_by_rel.values):
    axes[1].text(v + 0.2, i, str(v), va='center', fontsize=10)

plt.tight_layout()
plt.savefig('assets/precision_evaluation.png', dpi=200, bbox_inches='tight')
print('图表已保存: assets/precision_evaluation.png')

# 统计错误原因分布
print('\n错误统计:')
print(f'  总错误: {wrong} 条')
print('  按关系类型:')
for rel, cnt in wrong_by_rel.items():
    print(f'    {rel}: {cnt} 条')
