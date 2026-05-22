# -*- coding: utf-8 -*-
"""
COPD知识图谱评价指标可视化 v2 —— 大图幅、独立成图、突出质变故事
"""
import config  # 统一路径配置

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# 统一学术风格
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 150

OUTPUT_DIR = "assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 数据
versions = ['v1\n原始规则', 'v2\n清洗筛选', 'v3\n改进A', 'v4\n最大覆盖', 'v5\n医学细化', 'v6\nFinal']
triples = [131, 190, 163, 981, 675, 675]
vague_pct = [0, 0, 0, 73.19, 0, 0]
rel_types = [4, 6, 4, 7, 13, 13]
entities = [75, 101, 92, 164, 126, 126]

# ========== 图1：版本演进——数量与质量的博弈 ==========
fig, ax1 = plt.subplots(figsize=(10, 6))

# 柱状图：三元组总数
bars = ax1.bar(versions, triples, color=['#A8D5BA', '#A8D5BA', '#A8D5BA', '#FFB6B9', '#6EC6FF', '#6EC6FF'],
               edgecolor='#333333', linewidth=0.8, zorder=3)
# v4 标红（问题版），v5/v6 标蓝（精品版）
for i, (bar, v) in enumerate(zip(bars, triples)):
    ax1.text(bar.get_x() + bar.get_width()/2., v + 15, f'{v}', 
             ha='center', va='bottom', fontsize=11, fontweight='bold', color='#333')

ax1.set_ylabel('三元组总数', fontsize=12, color='#333')
ax1.set_ylim(0, 1150)
ax1.set_title('COPD知识图谱抽取方案迭代演进：从"量"到"质"的转变', 
              fontsize=14, fontweight='bold', pad=15)
ax1.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
ax1.set_axisbelow(True)

# 折线图：模糊关系占比
ax2 = ax1.twinx()
line = ax2.plot(versions, vague_pct, color='#E63946', marker='o', markersize=10, 
                linewidth=2.5, zorder=5, label='模糊关系占比')
for i, (x, y) in enumerate(zip(versions, vague_pct)):
    if y > 0:
        ax2.annotate(f'{y:.1f}%', xy=(i, y), xytext=(i, y+5),
                    ha='center', fontsize=11, color='#E63946', fontweight='bold')

ax2.set_ylabel('模糊关系占比 (%)', fontsize=12, color='#E63946')
ax2.set_ylim(0, 100)
ax2.tick_params(axis='y', labelcolor='#E63946')

# 关键注释：v4→v5
ax1.annotate('', xy=(4, 675), xytext=(3, 981),
            arrowprops=dict(arrowstyle='->', color='#E63946', lw=2))
ax1.text(3.5, 900, '医学审核\n剔除 718 条', fontsize=10, color='#E63946',
        ha='center', fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFE5E5', edgecolor='#E63946', alpha=0.9))

# 图例
bar_patch = mpatches.Patch(color='#6EC6FF', label='三元组总数')
line_patch = plt.Line2D([0], [0], color='#E63946', marker='o', linewidth=2.5, label='模糊关系占比')
ax1.legend(handles=[bar_patch, line_patch], loc='upper left', fontsize=10)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/fig1_evolution.png', bbox_inches='tight', facecolor='white')
plt.close()

# ========== 图2：v4→v5 质量蜕变（堆叠对比） ==========
fig, ax = plt.subplots(figsize=(8, 6))

categories = ['v4 最大覆盖\n(召回优先)', 'v5 医学细化\n(质量优先)']
precise = [263, 675]  # 精确关系数
vague = [718, 0]      # 模糊关系数

x = np.arange(len(categories))
width = 0.5

bars1 = ax.bar(x, precise, width, label='精确关系', color='#6EC6FF', edgecolor='#333', linewidth=0.8)
bars2 = ax.bar(x, vague, width, bottom=precise, label='模糊/相关关系', color='#FFB6B9', edgecolor='#333', linewidth=0.8)

# 标注
for i, (p, v) in enumerate(zip(precise, vague)):
    total = p + v
    ax.text(i, total + 20, f'共 {total} 条', ha='center', fontsize=12, fontweight='bold')
    if v > 0:
        ax.text(i, p + v/2, f'{v} 条模糊', ha='center', fontsize=10, color='#C0392B')
    ax.text(i, p/2, f'{p} 条精确', ha='center', fontsize=10, color='#1A5276')

ax.set_ylabel('三元组数量', fontsize=12)
ax.set_title('v4 → v5 关键蜕变：从"大而模糊"到"精而明确"', fontsize=14, fontweight='bold', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=11)
ax.legend(fontsize=11, loc='upper right')
ax.set_ylim(0, 1150)
ax.grid(axis='y', linestyle='--', alpha=0.4)
ax.set_axisbelow(True)

# 底部注释
ax.text(0.5, -120, '注：v4 采用最大覆盖策略，大量抽取"相关"等模糊关系；v5 引入医学知识审核，\n'
        '剔除全部模糊关系，同时从 7 种关系类型扩展至 13 种，实现质量跃升。',
        ha='center', fontsize=9, color='#666', transform=ax.transData)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/fig2_quality_leap.png', bbox_inches='tight', facecolor='white')
plt.close()

# ========== 图3：Final版13类关系分布（水平柱状图） ==========
fig, ax = plt.subplots(figsize=(10, 7))

# Final版本的关系分布数据
rel_data = [
    ('药物-治疗-疾病', 129, 19.1),
    ('疾病-症状', 100, 14.8),
    ('诱发-急性加重', 87, 12.9),
    ('药物-缓解-症状', 87, 12.9),
    ('检查-辅助诊断-疾病', 56, 8.3),
    ('治疗-改善-症状', 54, 8.0),
    ('疾病-并发症', 50, 7.4),
    ('危险因素-疾病', 38, 5.6),
    ('疾病-治疗', 34, 5.0),
    ('检查-评估-症状', 24, 3.6),
    ('检查-评估-疾病', 12, 1.8),
    ('药物-导致-并发症', 3, 0.4),
    ('检查-筛查-疾病', 1, 0.1),
]

labels = [d[0] for d in rel_data]
values = [d[1] for d in rel_data]

colors = plt.cm.Spectral(np.linspace(0.15, 0.85, len(labels)))[::-1]

bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1], edgecolor='#333', linewidth=0.6, height=0.65)

# 标注数值和百分比
for bar, (name, count, pct) in zip(bars, rel_data[::-1]):
    width = bar.get_width()
    ax.text(width + 2, bar.get_y() + bar.get_height()/2., 
            f'{count} 条 ({pct}%)', ha='left', va='center', fontsize=9.5, color='#333')

ax.set_xlabel('三元组数量', fontsize=12)
ax.set_title('Final 版本关系类型分布（675 条三元组，13 种关系类型）', fontsize=14, fontweight='bold', pad=15)
ax.set_xlim(0, 160)
ax.grid(axis='x', linestyle='--', alpha=0.4)
ax.set_axisbelow(True)

# 顶部注释
ax.text(80, 13.5, '关系类型从 v1 的 4 种扩展至 13 种，覆盖药物、症状、检查、治疗、并发症、危险因素六大维度',
        ha='center', fontsize=10, color='#555',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='#F0F8FF', edgecolor='#6EC6FF', alpha=0.8))

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/fig3_relation_dist.png', bbox_inches='tight', facecolor='white')
plt.close()

# ========== 图4：综合质量仪表盘 ==========
fig = plt.figure(figsize=(12, 5))

metrics = [
    ('三元组总数', 675, '条', '#6EC6FF'),
    ('唯一实体', 126, '个', '#A8D5BA'),
    ('关系类型', 13, '种', '#FFE082'),
    ('COPD可达率', 91.3, '%', '#CE93D8'),
    ('模糊关系', 0, '%', '#FFB6B9'),
    ('来源文献', 50, '篇', '#B0BEC5'),
]

for i, (name, value, unit, color) in enumerate(metrics):
    ax = fig.add_subplot(1, 6, i+1)
    
    # 画一个圆环
    theta = np.linspace(0, 2*np.pi, 100)
    if name == '模糊关系':
        fill_ratio = 1.0  # 0% 模糊是满分
    elif name == 'COPD可达率':
        fill_ratio = value / 100
    else:
        fill_ratio = 0.85  # 其他用固定填充比例表示"良好"
    
    # 背景圆
    ax.fill(np.cos(theta), np.sin(theta), color='#ECEFF1', edgecolor='none')
    # 填充弧
    theta_fill = np.linspace(-np.pi/2, -np.pi/2 + 2*np.pi*fill_ratio, 100)
    ax.fill(np.cos(theta_fill), np.sin(theta_fill), color=color, edgecolor='none', alpha=0.85)
    # 中心白圆
    ax.fill(np.cos(theta)*0.65, np.sin(theta)*0.65, color='white', edgecolor='none')
    
    ax.text(0, 0.1, f'{value}', ha='center', va='center', fontsize=20, fontweight='bold', color='#333')
    ax.text(0, -0.25, unit, ha='center', va='center', fontsize=10, color='#666')
    ax.text(0, -1.35, name, ha='center', va='center', fontsize=11, fontweight='bold', color='#333')
    
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.6, 1.3)
    ax.axis('off')
    ax.set_aspect('equal')

fig.suptitle('COPD 知识图谱综合质量指标', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/fig4_dashboard.png', bbox_inches='tight', facecolor='white')
plt.close()

print("[OK] 4张新图已生成:")
print(f"  1. {OUTPUT_DIR}/fig1_evolution.png      - 版本演进（数量vs模糊度）")
print(f"  2. {OUTPUT_DIR}/fig2_quality_leap.png   - v4→v5质量蜕变")
print(f"  3. {OUTPUT_DIR}/fig3_relation_dist.png  - 13类关系分布")
print(f"  4. {OUTPUT_DIR}/fig4_dashboard.png      - 综合质量仪表盘")
