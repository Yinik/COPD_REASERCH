#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COPD知识图谱可视化生成脚本

功能：从三元组数据生成知识图谱可视化图片（PNG格式）
用于：中期汇报PPT、README展示、评审材料

运行方式:
    python generate_kg_viz.py

产出:
    assets/kg_full.png      - 完整知识图谱（126节点+675关系）
    assets/kg_copd_core.png - COPD中心辐射图（1-2跳邻居）
    assets/kg_drug.png      - 药物子图
    assets/kg_symptom.png   - 症状子图
"""

import csv
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TRIPLES_FILE = os.path.join(PROJECT_DIR, '关系抽取结果', '方向规范化_疾病统一在头.tsv')
ASSETS_DIR = os.path.join(PROJECT_DIR, 'assets')
os.makedirs(ASSETS_DIR, exist_ok=True)

# 实体类型颜色映射
TYPE_COLORS = {
    'Disease': '#FF6B6B',
    'Symptom': '#FFA500',
    'Medication': '#4ECDC4',
    'Treatment': '#45B7D1',
    'Examination': '#96CEB4',
    'RiskFactor': '#FFEAA7',
    'Complication': '#DDA0DD',
}

TYPE_LABELS = {
    'Disease': '疾病',
    'Symptom': '症状',
    'Medication': '药物',
    'Treatment': '治疗',
    'Examination': '检查',
    'RiskFactor': '危险因素',
    'Complication': '并发症',
}


def load_data():
    """加载三元组数据"""
    rows = []
    with open(TRIPLES_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for r in reader:
            rows.append(r)
    
    # 构建实体信息
    entities = {}
    for r in rows:
        h, t = r['头实体'], r['尾实体']
        if h not in entities:
            entities[h] = r['头类型']
        if t not in entities:
            entities[t] = r['尾类型']
    
    return rows, entities


def draw_full_kg(rows, entities, max_nodes=80):
    """绘制完整知识图谱（限制节点数以避免过密）"""
    try:
        import networkx as nx
    except ImportError:
        print("[跳过] 未安装networkx，跳过完整图谱绘制")
        print("       安装命令: pip install networkx")
        return
    
    # 按关系数量选取核心节点
    node_degree = defaultdict(int)
    for r in rows:
        node_degree[r['头实体']] += 1
        node_degree[r['尾实体']] += 1
    
    # 保留COPD + 高度数节点
    copd = '慢性阻塞性肺疾病'
    core_nodes = set([copd])
    for node, deg in sorted(node_degree.items(), key=lambda x: -x[1])[:max_nodes-1]:
        core_nodes.add(node)
    
    # 过滤关系
    filtered_rows = [r for r in rows if r['头实体'] in core_nodes and r['尾实体'] in core_nodes]
    
    G = nx.DiGraph()
    for r in filtered_rows:
        G.add_edge(r['头实体'], r['尾实体'], relation=r['关系类型'])
    
    # 设置节点颜色
    node_colors = []
    node_sizes = []
    for node in G.nodes():
        etype = entities.get(node, 'Disease')
        node_colors.append(TYPE_COLORS.get(etype, '#CCCCCC'))
        if node == copd:
            node_sizes.append(800)
        else:
            node_sizes.append(300)
    
    plt.figure(figsize=(20, 16))
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.9)
    nx.draw_networkx_edges(G, pos, alpha=0.3, arrows=True, arrowsize=10, width=0.5)
    
    # 只显示部分标签避免重叠
    labels = {n: n if len(n) <= 6 else n[:5]+'...' for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=6)
    
    plt.title(f'COPD知识图谱核心子图 ({len(G.nodes())}节点 / {len(G.edges())}关系)', fontsize=16)
    plt.axis('off')
    
    # 图例
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=TYPE_LABELS.get(t, t)) 
                       for t, c in TYPE_COLORS.items()]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    output = os.path.join(ASSETS_DIR, 'kg_full.png')
    plt.savefig(output, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"[产出] {output}")


def draw_copd_radiation(rows, entities, max_hops=2):
    """绘制COPD中心辐射图"""
    try:
        import networkx as nx
    except ImportError:
        print("[跳过] 未安装networkx")
        return
    
    copd = '慢性阻塞性肺疾病'
    
    # BFS收集N跳内的节点
    adj = defaultdict(set)
    for r in rows:
        adj[r['头实体']].add(r['尾实体'])
    
    visited = {copd: 0}
    queue = [copd]
    while queue:
        node = queue.pop(0)
        if visited[node] >= max_hops:
            continue
        for neighbor in adj[node]:
            if neighbor not in visited:
                visited[neighbor] = visited[node] + 1
                queue.append(neighbor)
    
    # 过滤关系
    sub_rows = [r for r in rows 
                if r['头实体'] in visited and r['尾实体'] in visited]
    
    G = nx.DiGraph()
    for r in sub_rows:
        G.add_edge(r['头实体'], r['尾实体'], relation=r['关系类型'])
    
    node_colors = []
    node_sizes = []
    for node in G.nodes():
        etype = entities.get(node, 'Disease')
        node_colors.append(TYPE_COLORS.get(etype, '#CCCCCC'))
        if node == copd:
            node_sizes.append(1200)
        elif visited.get(node, 0) == 1:
            node_sizes.append(500)
        else:
            node_sizes.append(300)
    
    plt.figure(figsize=(18, 14))
    pos = nx.spring_layout(G, k=2.5, iterations=50, seed=42)
    
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.9)
    nx.draw_networkx_edges(G, pos, alpha=0.35, arrows=True, arrowsize=12, width=0.6)
    
    labels = {n: n if len(n) <= 8 else n[:7]+'...' for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=7)
    
    plt.title(f'COPD中心辐射图（{max_hops}跳内共{len(G.nodes())}个实体）', fontsize=16)
    plt.axis('off')
    
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=TYPE_LABELS.get(t, t)) 
                       for t, c in TYPE_COLORS.items()]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    output = os.path.join(ASSETS_DIR, 'kg_copd_core.png')
    plt.savefig(output, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"[产出] {output}")


def draw_relation_subtype(rows, entities, relation_filter, title, filename):
    """绘制特定关系类型的子图"""
    try:
        import networkx as nx
    except ImportError:
        return
    
    sub_rows = [r for r in rows if relation_filter in r['关系类型']]
    if len(sub_rows) < 3:
        print(f"[跳过] {title} 关系数量太少({len(sub_rows)})")
        return
    
    G = nx.DiGraph()
    for r in sub_rows:
        G.add_edge(r['头实体'], r['尾实体'])
    
    node_colors = []
    node_sizes = []
    for node in G.nodes():
        etype = entities.get(node, 'Disease')
        node_colors.append(TYPE_COLORS.get(etype, '#CCCCCC'))
        node_sizes.append(400 if '慢性阻塞性肺疾病' in node else 250)
    
    plt.figure(figsize=(14, 10))
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.9)
    nx.draw_networkx_edges(G, pos, alpha=0.4, arrows=True, arrowsize=10, width=0.6)
    
    labels = {n: n if len(n) <= 8 else n[:7]+'...' for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8)
    
    plt.title(f'{title}（{len(G.nodes())}实体 / {len(G.edges())}关系）', fontsize=14)
    plt.axis('off')
    
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=TYPE_LABELS.get(t, t)) 
                       for t, c in TYPE_COLORS.items()]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=9)
    
    output = os.path.join(ASSETS_DIR, filename)
    plt.savefig(output, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"[产出] {output}")


def draw_stats_bar(rows, entities):
    """绘制关系类型统计柱状图"""
    rel_counts = defaultdict(int)
    for r in rows:
        rel_counts[r['关系类型']] += 1
    
    rels = sorted(rel_counts.items(), key=lambda x: -x[1])
    names = [r[0] for r in rels]
    counts = [r[1] for r in rels]
    
    plt.figure(figsize=(14, 8))
    bars = plt.barh(range(len(names)), counts, color='#45B7D1')
    plt.yticks(range(len(names)), names, fontsize=10)
    plt.xlabel('关系数量', fontsize=12)
    plt.title('COPD知识图谱 - 13类关系分布统计', fontsize=14)
    plt.gca().invert_yaxis()
    
    # 在柱子上标注数值
    for i, (bar, count) in enumerate(zip(bars, counts)):
        plt.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                str(count), va='center', fontsize=9)
    
    plt.tight_layout()
    output = os.path.join(ASSETS_DIR, 'relation_stats.png')
    plt.savefig(output, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"[产出] {output}")


def draw_entity_pie(entities):
    """绘制实体类型饼图"""
    type_counts = defaultdict(int)
    for etype in entities.values():
        type_counts[etype] += 1
    
    labels = [TYPE_LABELS.get(t, t) for t in type_counts.keys()]
    sizes = list(type_counts.values())
    colors = [TYPE_COLORS.get(t, '#CCCCCC') for t in type_counts.keys()]
    
    plt.figure(figsize=(10, 8))
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', 
            startangle=90, textprops={'fontsize': 11})
    plt.title(f'COPD知识图谱 - 实体类型分布（共{sum(sizes)}个实体）', fontsize=14)
    plt.axis('equal')
    
    output = os.path.join(ASSETS_DIR, 'entity_pie.png')
    plt.savefig(output, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"[产出] {output}")


def main():
    print("=" * 60)
    print("  COPD知识图谱可视化生成")
    print("=" * 60)
    
    rows, entities = load_data()
    print(f"[数据] 加载 {len(rows)} 条关系，{len(entities)} 个实体")
    
    draw_stats_bar(rows, entities)
    draw_entity_pie(entities)
    draw_full_kg(rows, entities, max_nodes=60)
    draw_copd_radiation(rows, entities, max_hops=2)
    draw_relation_subtype(rows, entities, '药物-治疗', '药物治疗子图', 'kg_drug.png')
    draw_relation_subtype(rows, entities, '疾病-症状', '疾病症状子图', 'kg_symptom.png')
    
    print(f"\n[完成] 所有图片已保存到: {ASSETS_DIR}")
    for f in sorted(os.listdir(ASSETS_DIR)):
        fpath = os.path.join(ASSETS_DIR, f)
        size = os.path.getsize(fpath)
        print(f"  - {f} ({size//1024} KB)")


if __name__ == '__main__':
    main()
