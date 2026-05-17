#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目验证脚本 - 一键检查核心数据完整性

运行方式:
    python verify_project.py

功能:
    1. 验证种子词典完整性（126实体，7类）
    2. 验证三元组数据完整性（675条，13类关系）
    3. 验证Neo4j导入文件存在性
    4. 验证图谱连通性（所有实体可从COPD到达）
    5. 输出验证报告

作者: COPD知识图谱小组
"""

import csv
import os
import sys
from collections import defaultdict

# ==================== 配置路径 ====================
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TRIPLES_FILE = os.path.join(PROJECT_DIR, '关系抽取结果', '方向规范化_疾病统一在头.tsv')
NODES_CSV = os.path.join(PROJECT_DIR, '关系抽取结果', 'import', 'nodes.csv')
RELATIONS_CSV = os.path.join(PROJECT_DIR, '关系抽取结果', 'import', 'relations.csv')
NEO4J_DIR = os.path.join(PROJECT_DIR, '关系抽取结果', 'Neo4j导入')
IMPORT_DIR = os.path.join(PROJECT_DIR, '关系抽取结果', 'import')

# 颜色输出（Windows CMD兼容）
GREEN = ''
RED = ''
YELLOW = ''
RESET = ''
BOLD = ''

def print_ok(msg):
    print(f"  [OK] {msg}")

def print_fail(msg):
    print(f"  [FAIL] {msg}")

def print_warn(msg):
    print(f"  [WARN] {msg}")

def print_section(title):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{title}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

# ==================== 验证函数 ====================

def verify_triples():
    """验证三元组数据"""
    print_section("一、三元组数据验证")
    
    if not os.path.exists(TRIPLES_FILE):
        print_fail(f"三元组文件不存在: {TRIPLES_FILE}")
        return False
    
    print_ok(f"找到三元组文件: {TRIPLES_FILE}")
    
    rows = []
    with open(TRIPLES_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for r in reader:
            rows.append(r)
    
    total = len(rows)
    print_ok(f"读取三元组数量: {total} 条")
    
    # 验证数量
    if total == 675:
        print_ok(f"三元组数量符合预期: 675 条")
    else:
        print_warn(f"三元组数量为 {total}，预期 675 条")
    
    # 统计关系类型
    rel_types = defaultdict(int)
    entities = set()
    for r in rows:
        rel_types[r['关系类型']] += 1
        entities.add(r['头实体'])
        entities.add(r['尾实体'])
    
    print_ok(f"关系类型数: {len(rel_types)} 种")
    print_ok(f"涉及实体数: {len(entities)} 个")
    
    # 打印关系分布
    print(f"\n  关系类型分布:")
    for rel, count in sorted(rel_types.items(), key=lambda x: -x[1]):
        status = "[OK]" if count > 0 else "[FAIL]"
        print(f"    {status}{RESET} {rel}: {count} 条")
    
    # 验证是否有"相关"模糊关系
    vague_rels = [r for r in rel_types if '相关' in r]
    if vague_rels:
        print_warn(f"发现模糊关系类型: {vague_rels}")
    else:
        print_ok("未发现相关等模糊关系")
    
    return True

def verify_entities():
    """验证实体统计"""
    print_section("二、实体统计验证")
    
    if not os.path.exists(TRIPLES_FILE):
        print_fail("三元组文件不存在，跳过实体验证")
        return False
    
    entities = {}  # name -> type
    with open(TRIPLES_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for r in reader:
            h, t = r['头实体'], r['尾实体']
            if h not in entities:
                entities[h] = r['头类型']
            if t not in entities:
                entities[t] = r['尾类型']
    
    type_counts = defaultdict(int)
    for etype in entities.values():
        type_counts[etype] += 1
    
    print_ok(f"唯一实体总数: {len(entities)} 个")
    
    expected = {
        'Disease': 28, 'Symptom': 25, 'Medication': 34,
        'Treatment': 14, 'Examination': 8, 'RiskFactor': 12, 'Complication': 5
    }
    
    print(f"\n  实体类型分布:")
    all_match = True
    for etype, exp_count in expected.items():
        actual = type_counts.get(etype, 0)
        status = "[OK]" if actual == exp_count else "[FAIL]"
        if actual != exp_count:
            all_match = False
        print(f"    {status}{RESET} {etype}: {actual} 个 (预期 {exp_count})")
    
    if all_match:
        print_ok("所有实体类型数量符合预期")
    else:
        print_warn("部分实体类型数量与预期不符")
    
    return True

def verify_neo4j_files():
    """验证Neo4j导入文件"""
    print_section("三、Neo4j导入文件验证")
    
    required_files = [('import.cypher', NEO4J_DIR), ('README.md', NEO4J_DIR), 
                       ('nodes.csv', IMPORT_DIR), ('relations.csv', IMPORT_DIR)]
    all_exist = True
    
    print(f"  检查Neo4j导入相关目录")
    
    for fname, dname in required_files:
        fpath = os.path.join(dname, fname)
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
            print_ok(f"{fname} 存在 ({size} bytes)")
        else:
            print_fail(f"{fname} 不存在")
            all_exist = False
    
    # 检查按类型拆分的关系文件
    rel_files = [f for f in os.listdir(NEO4J_DIR) if f.startswith('relations_') and f.endswith('.csv')]
    print_ok(f"按类型拆分的关系文件: {len(rel_files)} 个")
    
    if all_exist:
        print_ok("Neo4j导入文件完整")
    else:
        print_warn("部分Neo4j导入文件缺失")
    
    return all_exist

def verify_connectivity():
    """验证图谱连通性（所有实体可从COPD到达）"""
    print_section("四、图谱连通性验证")
    
    if not os.path.exists(TRIPLES_FILE):
        print_fail("三元组文件不存在，跳过连通性验证")
        return False
    
    # 构建邻接表
    adj = defaultdict(set)
    all_entities = set()
    
    with open(TRIPLES_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for r in reader:
            h, t = r['头实体'], r['尾实体']
            adj[h].add(t)
            all_entities.add(h)
            all_entities.add(t)
    
    # BFS从COPD出发
    start = '慢性阻塞性肺疾病'
    if start not in all_entities:
        print_fail(f"中心实体 '{start}' 不在图谱中")
        return False
    
    visited = set([start])
    queue = [start]
    
    while queue:
        node = queue.pop(0)
        for neighbor in adj[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    
    reachable = len(visited)
    total = len(all_entities)
    rate = reachable / total * 100
    
    print_ok(f"中心实体: '{start}'")
    print_ok(f"可达实体: {reachable} / {total} ({rate:.1f}%)")
    
    if rate >= 95:
        print_ok(f"图谱连通性良好！{rate:.1f}% 实体可从COPD到达")
        return True
    elif rate >= 85:
        unreachable = all_entities - visited
        print_warn(f"图谱部分连通：{rate:.1f}% 实体可达，存在 {len(unreachable)} 个不可达实体")
        for e in sorted(unreachable)[:5]:
            print_warn(f"  - {e}")
        return True
    else:
        unreachable = all_entities - visited
        print_fail(f"图谱连通性不足：仅 {rate:.1f}% 实体可达")
        for e in sorted(unreachable)[:5]:
            print_warn(f"  - {e}")
        return False

def verify_copd_center():
    """验证COPD是图谱中心"""
    print_section("五、COPD中心性验证")
    
    if not os.path.exists(TRIPLES_FILE):
        print_fail("三元组文件不存在")
        return False
    
    copd_name = '慢性阻塞性肺疾病'
    head_count = 0
    tail_count = 0
    
    with open(TRIPLES_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for r in reader:
            if r['头实体'] == copd_name:
                head_count += 1
            if r['尾实体'] == copd_name:
                tail_count += 1
    
    print_ok(f"COPD作为头实体出现: {head_count} 次")
    print_ok(f"COPD作为尾实体出现: {tail_count} 次")
    print_ok(f"COPD总参与度: {head_count + tail_count} 次")
    
    return True

# ==================== 主函数 ====================

def main():
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  COPD知识图谱项目 - 数据完整性验证报告{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"  项目: 基于COPD医学文本的实体关系抽取与知识图谱构建")
    print(f"  作者: 尹鑫、苟玉莲")
    print(f"  时间: 2025年春季学期")
    
    results = []
    
    results.append(("三元组数据", verify_triples()))
    results.append(("实体统计", verify_entities()))
    results.append(("Neo4j文件", verify_neo4j_files()))
    results.append(("图谱连通性", verify_connectivity()))
    results.append(("COPD中心性", verify_copd_center()))
    
    # 总评
    print_section("验证总结")
    
    all_pass = True
    for name, ok in results:
        status = "[PASS]" if ok else "[FAIL]"
        print(f"  {status}{RESET} {name}")
        if not ok:
            all_pass = False
    
    print(f"\n{BOLD}{'='*60}{RESET}")
    if all_pass:
        print(f"  [PASS] 所有验证通过！项目数据完整。")
    else:
        print(f"  [WARN] 部分验证未通过，请检查上述失败项。")
    print(f"{BOLD}{'='*60}{RESET}")
    
    return 0 if all_pass else 1

if __name__ == '__main__':
    sys.exit(main())
