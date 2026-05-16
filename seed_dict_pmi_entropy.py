# -*- coding: utf-8 -*-
"""
种子词典构建 - 第一步：互信息(PMI) + 左右熵
基于4篇COPD清洗文本，提取候选医学术语/种子词
"""

import os
import math
import json
from collections import defaultdict, Counter

# ================== 配置区域 ==================
FILE_PATHS = [
    r"I:\101实验专题\data\清洗后的文本数据\21_慢性阻塞性肺疾病诊治指南（2021年修订版）-主要参考_cleaned.txt",
    r"I:\101实验专题\data\清洗后的文本数据\11_【参考】慢性阻塞性肺病（COPD）治疗药物临床研究指导原则-EMA_cleaned.txt",
    r"I:\101实验专题\data\清洗后的文本数据\23_面向全科医生的《慢性阻塞性肺疾病诊治指南（2021年修订版）》解读_cleaned.txt",
    r"I:\101实验专题\data\清洗结果\cleaned_texts\5_2025年GOLD慢性阻塞性肺疾病诊断、治疗、管理及预防全球策略更新要点解读.txt",
]

OUTPUT_DIR = r"I:\101实验专题"

# 算法参数（可根据输出结果调整）
MIN_LEN = 2          # 候选词最小token长度
MAX_LEN = 6          # 候选词最大token长度（医学术语较长，设为6）
MIN_FREQ = 3         # 最低出现频次
PMI_THRESHOLD = 3.0  # PMI阈值，高于此值认为内部凝固度足够
LE_THRESHOLD = 0.5   # 左熵阈值
RE_THRESHOLD = 0.5   # 右熵阈值
# =============================================


def read_texts(file_paths):
    """读取所有文本文件"""
    texts = []
    for fp in file_paths:
        if not os.path.exists(fp):
            print(f"[警告] 文件不存在，已跳过: {fp}")
            continue
        with open(fp, 'r', encoding='utf-8') as f:
            texts.append(f.read())
    return '\n'.join(texts)


def tokenize(text):
    """
    将文本切分为token序列：
    - 中文字符：每个字单独成一个token
    - 连续英文/数字：合并为一个token（保留医学缩写如FEV1、COPD、GOLD等）
    - 其他字符（标点、空格、换行等）：过滤掉
    """
    tokens = []
    i = 0
    L = len(text)
    while i < L:
        c = text[i]
        # 中文字符
        if '\u4e00' <= c <= '\u9fff':
            tokens.append(c)
            i += 1
        # 连续英文或数字
        elif c.isalpha() or c.isdigit():
            j = i
            while j < L and (text[j].isalpha() or text[j].isdigit()):
                j += 1
            tokens.append(text[i:j])
            i = j
        # 其他字符跳过
        else:
            i += 1
    return tokens


def calculate_entropy(counter):
    """根据邻接计数计算信息熵"""
    total = sum(counter.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counter.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


def main():
    print("=" * 60)
    print("种子词典构建：互信息(PMI) + 左右熵")
    print("=" * 60)

    # ---------- 步骤1：读取与预处理 ----------
    print("\n[1/4] 读取文本并Token化...")
    raw_text = read_texts(FILE_PATHS)
    print(f"      原始文本总字符数: {len(raw_text):,}")

    tokens = tokenize(raw_text)
    L = len(tokens)
    print(f"      Token化后总token数: {L:,}")
    if L == 0:
        print("[错误] 文本为空或未能正确读取，请检查文件路径。")
        return

    # ---------- 步骤2：统计频率 ----------
    print("\n[2/4] 统计N-gram频率与邻接信息...")

    # 频率统计：1-token 到 MAX_LEN-token 的所有子串
    freq = Counter()
    for i in range(L):
        max_n = min(MAX_LEN, L - i)
        w = ''
        for n in range(1, max_n + 1):
            w += tokens[i + n - 1]
            freq[w] += 1

    # 邻接信息 + PMI 计算
    left_neighbors = defaultdict(Counter)   # word -> {neighbor_token: count}
    right_neighbors = defaultdict(Counter)  # word -> {neighbor_token: count}
    candidate_pmi = {}                      # word -> min_pmi

    for i in range(L - MIN_LEN + 1):
        max_n = min(MAX_LEN, L - i)
        w = ''
        token_seq = []
        for n in range(1, max_n + 1):
            token_seq.append(tokens[i + n - 1])
            w += tokens[i + n - 1]

            if n >= MIN_LEN:
                # 记录左右邻接（使用 '^' 和 '$' 标记文本边界）
                if i > 0:
                    left_neighbors[w][tokens[i - 1]] += 1
                else:
                    left_neighbors[w]['^'] += 1

                if i + n < L:
                    right_neighbors[w][tokens[i + n]] += 1
                else:
                    right_neighbors[w]['$'] += 1

                # 计算PMI（对所有token级一分为二的分割取最小值）
                if w not in candidate_pmi:
                    min_pmi = float('inf')
                    for k in range(1, n):
                        left = ''.join(token_seq[:k])
                        right = ''.join(token_seq[k:])
                        fl = freq[left]
                        fr = freq[right]
                        fw = freq[w]
                        if fl == 0 or fr == 0:
                            continue
                        # 简化PMI公式：log2( fw * L / (fl * fr) )
                        pmi = math.log2(fw * L / (fl * fr))
                        if pmi < min_pmi:
                            min_pmi = pmi
                    candidate_pmi[w] = min_pmi if min_pmi != float('inf') else -999

    print(f"      候选词总数: {len(candidate_pmi):,}")

    # ---------- 步骤3：筛选种子词 ----------
    print("\n[3/4] 根据PMI和左右熵筛选种子词...")
    results = []

    for w, pmi in candidate_pmi.items():
        fw = freq[w]
        if fw < MIN_FREQ:
            continue
        if pmi < PMI_THRESHOLD:
            continue

        le = calculate_entropy(left_neighbors[w])
        re = calculate_entropy(right_neighbors[w])

        # 左右熵同时满足阈值
        if le < LE_THRESHOLD or re < RE_THRESHOLD:
            continue

        # 综合得分 = PMI + 左熵 + 右熵（可根据需求调整加权）
        score = pmi + le + re
        results.append({
            'word': w,
            'freq': fw,
            'pmi': round(pmi, 4),
            'left_entropy': round(le, 4),
            'right_entropy': round(re, 4),
            'score': round(score, 4)
        })

    # 按综合得分降序排列
    results.sort(key=lambda x: x['score'], reverse=True)
    print(f"      通过筛选的种子词数量: {len(results):,}")

    # ---------- 步骤4：保存结果 ----------
    print("\n[4/4] 保存结果...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1) JSON完整结果
    json_path = os.path.join(OUTPUT_DIR, 'seed_dict_pmi_entropy.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"      JSON完整结果: {json_path}")

    # 2) TSV表格（前500条，便于Excel查看）
    tsv_path = os.path.join(OUTPUT_DIR, 'seed_dict_pmi_entropy.tsv')
    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.write("排名\t词语\t频次\tPMI\t左熵\t右熵\t综合得分\n")
        for i, r in enumerate(results[:500], 1):
            f.write(f"{i}\t{r['word']}\t{r['freq']}\t{r['pmi']}\t{r['left_entropy']}\t{r['right_entropy']}\t{r['score']}\n")
    print(f"      TSV表格(前500): {tsv_path}")

    # 3) 纯词表（每行一个词，方便后续步骤直接使用）
    wordlist_path = os.path.join(OUTPUT_DIR, 'seed_dict_wordlist.txt')
    with open(wordlist_path, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(r['word'] + '\n')
    print(f"      纯词表: {wordlist_path}")

    # ---------- 预览 ----------
    print("\n" + "=" * 60)
    print("Top 30 种子词预览")
    print("=" * 60)
    print(f"{'排名':<4} {'词语':<25} {'频次':<6} {'PMI':<8} {'左熵':<8} {'右熵':<8} {'得分':<8}")
    print("-" * 60)
    for i, r in enumerate(results[:30], 1):
        print(f"{i:<4} {r['word']:<25} {r['freq']:<6} {r['pmi']:<8.2f} {r['left_entropy']:<8.2f} {r['right_entropy']:<8.2f} {r['score']:<8.2f}")

    print("\n[完成] 请查看输出文件，若结果过多/过少可调整脚本顶部的阈值参数后重新运行。")


if __name__ == '__main__':
    main()
