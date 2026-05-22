# -*- coding: utf-8 -*-
"""
种子词典术语扩展（Bootstrapping）- 优化版
基于核心种子词上下文共现，自动发现新的候选术语
改进点：
  1. 只用Top-K核心种子词做锚点，避免通用词污染
  2. 过滤已知种子词的截断子串片段
  3. 再次过滤停用词与字母数字噪声
"""
import config  # 统一路径配置


import os
import math
import json
import re
from collections import defaultdict, Counter

# ================== 配置区域 ==================
SEED_JSON = str(config.BASE_DIR / r"seed_dict_cleaned.json")

RAW_TEXT_FILES = [
    str(config.BASE_DIR / r"data\清洗后的文本数据\21_慢性阻塞性肺疾病诊治指南（2021年修订版）-主要参考_cleaned.txt"),
    str(config.BASE_DIR / r"data\清洗后的文本数据\11_【参考】慢性阻塞性肺病（COPD）治疗药物临床研究指导原则-EMA_cleaned.txt"),
    str(config.BASE_DIR / r"data\清洗后的文本数据\23_面向全科医生的《慢性阻塞性肺疾病诊治指南（2021年修订版）》解读_cleaned.txt"),
    str(config.BASE_DIR / r"data\清洗结果\cleaned_texts\5_2025年GOLD慢性阻塞性肺疾病诊断、治疗、管理及预防全球策略更新要点解读.txt"),
]

OUTPUT_DIR = r"I:\101实验专题"

WINDOW_SIZE = 5          # 共现窗口半径
MIN_FREQ = 3             # 候选词最低全局频次
MIN_CO_SEED_TYPES = 4    # 至少与多少种不同核心种子词共现（提高以减少噪声）
MAX_LEN = 6              # 候选词最大长度
CORE_SEED_TOP_K = 800    # 只用得分最高的前800个种子词作为锚点
# =============================================

# 停用词表（复用）
STOPWORDS = {
    '包括', '评估', '使用', '建议', '进行', '影响', '研究', '改善', '相关', '推荐',
    '考虑', '根据', '必须', '记录', '标准', '观察', '这些', '策略', '存在', '需要',
    '目前', '情况', '减少', '鼓励', '选择', '训练', '探索', '破坏', '导致', '降低',
    '措施', '可以', '应该', '可能', '通过', '对于', '以及', '及其', '由于', '因此',
    '从而', '但是', '虽然', '因为', '所以', '如果', '或者', '并且', '同时', '此外',
    '另外', '然后', '之后', '之前', '以上', '以下', '之中', '之间', '关于', '基于',
    '按照', '随着', '除了', '尽管', '即使', '只要', '只有', '无论', '还是', '要么',
    '能否', '是否', '不能', '不会', '不得', '不可', '不宜', '不应', '不该', '不需',
    '不必', '无须', '无需', '没有', '已有', '已经', '正在', '仍然', '继续', '逐渐',
    '明显', '显著', '有效', '合理', '适当', '相应', '具体', '详细', '明确', '充分',
    '必要', '重要', '主要', '基本', '初步', '进一步', '不断', '大量', '许多', '部分',
    '一些', '某些', '各种', '多种', '各类', '各个', '各项', '其一', '其二', '首先',
    '其次', '再次', '最后', '最终', '总的', '整体', '全面', '系统', '深入', '长期',
    '短期', '近期', '远期', '平时', '常常', '经常', '通常', '一般', '普通', '特殊',
    '特别', '尤其', '十分', '非常', '极其', '比较', '相对', '绝对', '完全', '彻底',
    '总体', '大概', '大约', '具有', '发生', '出现', '形成', '成为', '作为', '列为',
    '定为', '视为', '认为', '称为', '命名', '分为', '未见', '一致', '相似', '相同',
    '不同', '差异', '区别', '分别', '各自', '依次', '逐步', '相继', '陆续', '连续',
    '反复', '多次', '数次', '初次', '首次', '每次', '历次', '期次', '批次', '例次',
    '人次', '例数', '人数', '次数', '频率', '比例', '构成', '分布', '结构', '特点',
    '特征', '特性', '性质', '属性', '状态', '状况', '情形', '形势', '局面', '情景',
    '场景', '场合', '场所', '地点', '位置', '方位', '方向', '趋势', '动向', '动态',
    '态势', '格局', '模式', '形式', '方式', '方法', '手段', '途径', '渠道', '路线',
    '路径', '过程', '历程', '进程', '流程', '程序', '步骤', '环节', '阶段', '时期',
    '期间', '时候', '时刻', '时间', '时机', '时限', '年代', '年度', '年份', '年月',
    '月份', '日期', '日子', '当天', '当日', '次日', '隔天', '连日', '以往', '过去',
    '曾经', '历来', '向来', '从来', '始终', '一直', '一贯', '一向', '根本', '压根',
    '简直', '几乎', '差不多', '约莫', '估计', '推测', '猜测', '猜想', '预计', '预期',
    '预料', '预见', '预测', '打算', '计划', '准备', '安排', '部署', '布置', '配置',
    '设置', '设定', '确定', '决定', '规定', '制定', '制订', '拟定', '拟订', '起草',
    '草拟', '编制', '编撰', '编纂', '编写', '撰写', '写作', '创作', '创造', '创立',
    '创建', '建立', '建设', '设立', '成立', '建成', '组合', '整合', '综合', '集合',
    '聚集', '汇集', '汇总', '收集', '搜集', '采集', '摄取', '吸收', '吸取', '汲取',
    '提取', '筛选', '挑选', '选取', '选用', '采用', '采纳', '接受', '接收', '受到',
    '获得', '得到', '取得', '赢得', '博得', '赚得', '挣得', '摘得', '夺得', '抢占',
    '占领', '占据', '占有', '拥有', '具备', '附有', '带有', '含有', '包含', '囊括',
    '涵盖', '涉及', '牵涉', '牵扯', '关联', '联系', '关系', '有关', '相应', '对应',
    '对照', '对比', '比拟', '类比', '类似', '相近', '相仿', '相当', '等于', '等价',
    '等同', '一样', '同样', '统一', '单一', '单纯', '纯粹', '简单', '简便', '简易',
    '简洁', '简明', '简略', '简要', '概括', '归纳', '总结', '统筹', '协调', '协同',
    '协作', '合作', '配合', '搭配', '配套', '匹配', '符合', '适合', '适宜', '适应',
    '适用', '恰当', '妥当', '妥善', '合适', '相宜', '适中', '适度', '适量', '适时',
    '适地', '适龄', '得当', '得体', '得法', '得力', '得宜', '得益', '得利', '得势',
    '得手', '得逞', '得胜', '得闲', '得空', '得便', '得暇',
}


def read_texts(file_paths):
    texts = []
    for fp in file_paths:
        if not os.path.exists(fp):
            print(f"[警告] 跳过不存在的文件: {fp}")
            continue
        with open(fp, 'r', encoding='utf-8') as f:
            texts.append(f.read())
    return '\n'.join(texts)


def tokenize(text):
    tokens = []
    i = 0
    L = len(text)
    while i < L:
        c = text[i]
        if '\u4e00' <= c <= '\u9fff':
            tokens.append(c)
            i += 1
        elif c.isalpha() or c.isdigit():
            j = i
            while j < L and (text[j].isalpha() or text[j].isdigit()):
                j += 1
            tokens.append(text[i:j])
            i = j
        else:
            i += 1
    return tokens


def build_fragment_set(seed_set):
    """
    构建所有种子词的真子串集合，用于过滤截断片段。
    例如 "慢阻肺" -> {"慢阻", "阻肺"}
    """
    fragments = set()
    for s in seed_set:
        if len(s) < 3:
            continue
        for n in range(2, len(s)):
            for i in range(len(s) - n + 1):
                frag = s[i:i+n]
                # 只收录纯中文片段（避免误伤英文缩写）
                if all('\u4e00' <= c <= '\u9fff' for c in frag):
                    fragments.add(frag)
    return fragments


def is_noise(word):
    """判断扩展候选是否为噪声"""
    if word in STOPWORDS:
        return True, "停用词"
    if word.isdigit():
        return True, "纯数字"
    if re.search(r'\d', word) and re.search(r'[a-zA-Z]', word) and not re.search(r'[\u4e00-\u9fff]', word):
        return True, "字母数字混合噪声"
    if re.match(r'^[A-Z][a-z]+[A-Z][a-zA-Z]*$', word):
        return True, "英文人名"
    if len(word) > 15 and re.match(r'^[a-zA-Z0-9]+$', word) and re.search(r'[a-z]', word) and re.search(r'[A-Z]', word) and re.search(r'\d', word):
        return True, "乱码/base64"
    if word.lower() in {'etal', 'et al', 'doi'}:
        return True, "文献格式噪声"
    return False, ""


def main():
    print("=" * 70)
    print("种子词典术语扩展（Bootstrapping 优化版）")
    print("=" * 70)

    # ---------- 1. 读取种子词典，提取核心种子 ----------
    print("\n[1/5] 读取种子词典并提取核心种子...")
    with open(SEED_JSON, 'r', encoding='utf-8') as f:
        seed_data = json.load(f)

    # seed_data 已经是按得分降序排列的，取Top-K作为核心种子
    core_seed_data = seed_data[:CORE_SEED_TOP_K]
    core_seed_dict = set(item['word'] for item in core_seed_data)
    core_seed_weights = {item['word']: max(1.0, item.get('pmi', 1.0)) for item in core_seed_data}

    # 全部种子词集合（用于子串过滤）
    full_seed_dict = set(item['word'] for item in seed_data)

    print(f"      原始种子词总数: {len(seed_data)}")
    print(f"      核心种子词(Top {CORE_SEED_TOP_K}): {len(core_seed_dict)}")

    # 构建截断片段过滤集合
    print("      构建子串片段过滤集...")
    fragment_set = build_fragment_set(full_seed_dict)
    print(f"      已收录片段模式: {len(fragment_set):,} 个")

    # ---------- 2. 读取原文 ----------
    print("\n[2/5] 读取原文并Token化...")
    raw_text = read_texts(RAW_TEXT_FILES)
    tokens = tokenize(raw_text)
    L = len(tokens)
    print(f"      文本总token数: {L:,}")

    # ---------- 3. 标记核心种子词位置 ----------
    print("\n[3/5] 标记核心种子词位置...")
    seed_spans = []
    i = 0
    while i < L:
        matched = False
        for n in range(min(MAX_LEN, L - i), 0, -1):
            w = ''.join(tokens[i:i + n])
            if w in core_seed_dict:
                seed_spans.append((i, i + n, w))
                i += n
                matched = True
                break
        if not matched:
            i += 1

    print(f"      核心种子词出现次数: {len(seed_spans):,}")

    # ---------- 4. 统计全局频次 + 共现 ----------
    print("\n[4/5] 统计全局频次与核心种子共现...")

    candidate_freq = Counter()
    for i in range(L):
        max_n = min(MAX_LEN, L - i)
        w = ''
        for n in range(1, max_n + 1):
            w += tokens[i + n - 1]
            if n >= 2 and w not in full_seed_dict:
                candidate_freq[w] += 1

    co_occurrence = defaultdict(Counter)

    for start, end, seed_word in seed_spans:
        weight = core_seed_weights.get(seed_word, 1.0)

        # 左窗口
        left_begin = max(0, start - WINDOW_SIZE)
        for pos in range(left_begin, start):
            max_n = min(MAX_LEN, start - pos)
            w = ''
            for n in range(1, max_n + 1):
                w += tokens[pos + n - 1]
                if n >= 2 and w not in full_seed_dict:
                    co_occurrence[w][seed_word] += weight

        # 右窗口
        right_end = min(L, end + WINDOW_SIZE)
        for pos in range(end, right_end):
            max_n = min(MAX_LEN, right_end - pos)
            w = ''
            for n in range(1, max_n + 1):
                w += tokens[pos + n - 1]
                if n >= 2 and w not in full_seed_dict:
                    co_occurrence[w][seed_word] += weight

    print(f"      共现候选词种类: {len(co_occurrence):,}")

    # ---------- 5. 筛选扩展术语 ----------
    print("\n[5/5] 筛选扩展术语（含停用词/片段/噪声过滤）...")
    results = []

    for w, seed_counter in co_occurrence.items():
        # 停用词与噪声过滤
        noise, reason = is_noise(w)
        if noise:
            continue

        # 截断片段过滤：如果是已知种子词的纯中文子串，大概率是片段
        if w in fragment_set:
            continue

        freq = candidate_freq[w]
        if freq < MIN_FREQ:
            continue

        co_seed_types = len(seed_counter)
        co_seed_total = sum(seed_counter.values())
        if co_seed_types < MIN_CO_SEED_TYPES:
            continue

        score = co_seed_types * math.log1p(co_seed_total)
        top_seeds = seed_counter.most_common(5)

        results.append({
            'word': w,
            'freq': freq,
            'co_seed_types': co_seed_types,
            'co_seed_total': round(co_seed_total, 2),
            'score': round(score, 4),
            'top_co_seeds': [(s, round(c, 1)) for s, c in top_seeds]
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    print(f"      通过筛选的扩展术语: {len(results)}")

    # ---------- 6. 保存 ----------
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ext_json = os.path.join(OUTPUT_DIR, 'seed_dict_extended.json')
    with open(ext_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ext_tsv = os.path.join(OUTPUT_DIR, 'seed_dict_extended.tsv')
    with open(ext_tsv, 'w', encoding='utf-8') as f:
        f.write("排名\t词语\t全局频次\t共现种子种类\t共现总权重\t得分\t主要共现种子\n")
        for i, r in enumerate(results[:500], 1):
            seeds_str = ', '.join(f"{s}({c})" for s, c in r['top_co_seeds'])
            f.write(f"{i}\t{r['word']}\t{r['freq']}\t{r['co_seed_types']}\t{r['co_seed_total']}\t{r['score']}\t{seeds_str}\n")

    ext_wordlist = os.path.join(OUTPUT_DIR, 'seed_dict_extended_wordlist.txt')
    with open(ext_wordlist, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(r['word'] + '\n')

    merged_wordlist = os.path.join(OUTPUT_DIR, 'seed_dict_merged.txt')
    with open(merged_wordlist, 'w', encoding='utf-8') as f:

        for item in seed_data:
            f.write(item['word'] + '\n')
        for r in results:
            if r['word'] not in full_seed_dict:
                f.write(r['word'] + '\n')

    print(f"\n[已保存] 扩展术语JSON: {ext_json}")
    print(f"[已保存] 扩展术语TSV: {ext_tsv}")
    print(f"[已保存] 扩展术语词表: {ext_wordlist}")
    print(f"[已保存] 合并词表(原始+扩展): {merged_wordlist}")

    # 预览
    print("\n" + "=" * 70)
    print("Top 30 扩展术语预览")
    print("=" * 70)
    print(f"{'排名':<4} {'词语':<22} {'频次':<6} {'种类':<6} {'得分':<8} {'主要共现种子'}")
    print("-" * 75)
    for i, r in enumerate(results[:30], 1):
        seeds_str = ', '.join(f"{s}({c})" for s, c in r['top_co_seeds'][:3])
        print(f"{i:<4} {r['word']:<22} {r['freq']:<6} {r['co_seed_types']:<6} {r['score']:<8.2f} {seeds_str}")

    print("\n[完成] Bootstrapping扩展结束。")


if __name__ == '__main__':
    main()
