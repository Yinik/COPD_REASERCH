# -*- coding: utf-8 -*-
"""
种子词典后处理过滤脚本
基于规则自动清洗 PMI+熵 提取结果中的通用词、人名、格式噪声等
"""
import config  # 统一路径配置


import os
import re
import json
from collections import Counter

INPUT_JSON = str(config.BASE_DIR / r"seed_dict_pmi_entropy.json")
OUTPUT_DIR = r"I:\101实验专题"

# 通用中文停用词 + 常见无意义动词/虚词（从Top结果中提炼）
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


def is_noise(word):
    """
    判断一个词是否为噪声，返回 (是否噪声, 原因)
    """
    # 1. 停用词
    if word in STOPWORDS:
        return True, "停用词"

    # 2. 纯数字
    if word.isdigit():
        return True, "纯数字"

    # 3. 字母+数字混合噪声（如 DOI10, 1mmHg0133kPa）
    if re.search(r'\d', word) and re.search(r'[a-zA-Z]', word) and not re.search(r'[\u4e00-\u9fff]', word):
        return True, "字母数字混合噪声"

    # 4. CamelCase 英文人名（如 DransfieldMT, MartinezFJ, HanMK）
    #    模式：首字母大写 + 小写字母 + 再次大写
    if re.match(r'^[A-Z][a-z]+[A-Z][a-zA-Z]*$', word):
        return True, "英文人名"

    # 5. Base64/乱码样式（长度>15，纯字母数字，且同时含大小写和数字，无中文）
    if (len(word) > 15 and re.match(r'^[a-zA-Z0-9]+$', word)
            and re.search(r'[a-z]', word) and re.search(r'[A-Z]', word) and re.search(r'\d', word)):
        return True, "乱码/base64"

    # 6. 文献格式残留（etal, doi 等）
    if word.lower() in {'etal', 'et al', 'doi'}:
        return True, "文献格式噪声"

    return False, ""


def main():
    print("=" * 60)
    print("种子词典后处理过滤")
    print("=" * 60)

    # 读取原始结果
    print(f"\n读取: {INPUT_JSON}")
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"原始候选词数量: {len(data)}")

    # 过滤
    clean = []
    removed = []
    for item in data:
        w = item['word']
        noise, reason = is_noise(w)
        if noise:
            removed.append({**item, 'remove_reason': reason})
        else:
            clean.append(item)

    print(f"清洗后保留: {len(clean)}")
    print(f"删除噪声: {len(removed)}")

    # 删除原因统计
    reason_counter = Counter(r['remove_reason'] for r in removed)
    print("\n删除原因分布:")
    for reason, count in reason_counter.most_common():
        print(f"  - {reason}: {count} 个")

    # 保存清洗结果
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1) JSON
    json_path = os.path.join(OUTPUT_DIR, 'seed_dict_cleaned.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    print(f"\n[已保存] 清洗后JSON: {json_path}")

    # 2) TSV表格（前500）
    tsv_path = os.path.join(OUTPUT_DIR, 'seed_dict_cleaned.tsv')
    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.write("排名\t词语\t频次\tPMI\t左熵\t右熵\t综合得分\n")
        for i, r in enumerate(clean[:500], 1):
            f.write(f"{i}\t{r['word']}\t{r['freq']}\t{r['pmi']}\t{r['left_entropy']}\t{r['right_entropy']}\t{r['score']}\n")
    print(f"[已保存] 清洗后TSV(前500): {tsv_path}")

    # 3) 纯词表
    wordlist_path = os.path.join(OUTPUT_DIR, 'seed_dict_cleaned_wordlist.txt')
    with open(wordlist_path, 'w', encoding='utf-8') as f:
        for r in clean:
            f.write(r['word'] + '\n')
    print(f"[已保存] 清洗后词表: {wordlist_path}")

    # 4) 被删除的词（方便核查）
    removed_path = os.path.join(OUTPUT_DIR, 'seed_dict_removed.tsv')
    with open(removed_path, 'w', encoding='utf-8') as f:

        f.write("词语\t频次\tPMI\t左熵\t右熵\t得分\t删除原因\n")
        for r in removed:
            f.write(f"{r['word']}\t{r['freq']}\t{r['pmi']}\t{r['left_entropy']}\t{r['right_entropy']}\t{r['score']}\t{r['remove_reason']}\n")
    print(f"[已保存] 被删除词表: {removed_path}")

    # 预览Top 30
    print("\n" + "=" * 60)
    print("清洗后 Top 30 种子词预览")
    print("=" * 60)
    print(f"{'排名':<4} {'词语':<25} {'频次':<6} {'PMI':<8} {'左熵':<8} {'右熵':<8} {'得分':<8}")
    print("-" * 60)
    for i, r in enumerate(clean[:30], 1):
        print(f"{i:<4} {r['word']:<25} {r['freq']:<6} {r['pmi']:<8.2f} {r['left_entropy']:<8.2f} {r['right_entropy']:<8.2f} {r['score']:<8.2f}")

    print("\n[完成] 若发现仍有噪声，可修改本脚本中的 STOPWORDS 或 is_noise() 规则后重新运行。")


if __name__ == '__main__':
    main()
