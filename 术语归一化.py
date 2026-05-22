# -*- coding: utf-8 -*-
"""
种子词典术语归一化
解决：同义词/缩写/别称合并 + 过长非术语过滤
"""
import config  # 统一路径配置


import os
import json

INPUT_WORDLIST = str(config.BASE_DIR / r"种子词典构建结果\13_核心4篇_合并版_高置信度加待审核_wordlist.txt")
INPUT_JSON = str(config.BASE_DIR / r"种子词典构建结果\09_核心4篇_PDF版式提取_全部术语.json")
OUTPUT_DIR = str(config.BASE_DIR / r"种子词典构建结果")

# ================== 同义词映射表（COPD领域） ==================
# key: 标准形式（归一化后的术语）
# value: list of 同义词/缩写/别称（会被合并到标准形式）
SYNONYM_MAP = {
    # === 核心疾病 ===
    '慢性阻塞性肺疾病': ['慢阻肺', '慢阻肺病', '慢性阻塞性肺病', 'COPD', 'chronic obstructive pulmonary disease'],
    '慢性阻塞性肺疾病急性加重': ['急性加重', '急性加重期', 'AECOPD', '慢阻肺急性加重', '慢阻肺病急性加重'],
    '慢性阻塞性肺疾病全球倡议': ['GOLD', 'GOLD 2025', 'GOLD 2024', 'GOLD 2023', 'GOLD 2026'],

    # === 药物类别 ===
    '吸入性糖皮质激素': ['ICS', '吸入糖皮质激素', '糖皮质激素'],
    '长效β2受体激动剂': ['LABA', '长效β2受体激动剂', '长效β受体激动剂'],
    '长效毒蕈碱拮抗剂': ['LAMA', '长效抗胆碱能药物'],
    '短效β2受体激动剂': ['SABA', '短效β2受体激动剂', '短效β受体激动剂'],
    '短效毒蕈碱拮抗剂': ['SAMA', '短效抗胆碱能药物'],
    '磷酸二酯酶4抑制剂': ['PDE-4抑制剂', 'PDE4抑制剂', 'PDE-4', 'PDE4'],
    '茶碱类药物': ['茶碱', '氨茶碱', '多索茶碱'],
    '抗胆碱能药物': ['抗胆碱药', '胆碱能受体拮抗剂'],
    '支气管舒张剂': ['支气管扩张剂', '支气管扩张药', '支气管舒张药'],
    '黏液溶解剂': ['祛痰药', '化痰药'],

    # === 具体药物 ===
    '度普利尤单抗': ['Dupilumab', '达必妥'],
    '恩塞芬汀': ['Ensifentrine', 'Ohtuvayre'],
    '罗氟司特': ['Roflumilast'],
    '阿奇霉素': ['Azithromycin'],
    '卡泊芬净': ['Carbocisteine', '羧甲司坦'],
    'N-乙酰半胱氨酸': ['NAC', '乙酰半胱氨酸'],

    # === 检查指标 ===
    '第一秒用力呼气容积': ['FEV', 'FEV1', '一秒量'],
    '用力肺活量': ['FVC'],
    '一秒率': ['FEV1/FVC', 'FEV/FVC'],
    '肺总量': ['TLC'],
    '残气量': ['RV'],
    '功能残气量': ['FRC'],
    '肺一氧化碳弥散量': ['DLCO'],
    '吸气峰流速': ['PIFR', '峰值吸气流速'],
    '动脉血氧分压': ['PaO2'],
    '动脉血二氧化碳分压': ['PaCO2'],
    '血氧饱和度': ['SpO2', 'SaO2'],
    '血氧分压': ['PO2'],
    'C反应蛋白': ['CRP', 'hs-CRP', '高敏C反应蛋白'],
    '降钙素原': ['PCT'],
    '血沉': ['ESR', '红细胞沉降率'],
    'B型钠尿肽': ['BNP', 'NT-proBNP'],
    'D-二聚体': ['D-Dimer'],

    # === 症状/体征 ===
    '呼吸困难': ['呼吸急促', '气短', '气促', '气喘', '呼吸窘迫', 'dyspnea'],
    '慢性咳嗽': ['咳嗽', '干咳', '湿咳'],
    '咳痰': ['痰液', '痰多', '排痰'],
    '气流受限': ['气道阻塞', '气流阻塞', '通气障碍'],
    '喘息': ['哮鸣', '喘鸣'],
    '胸闷': ['胸部憋闷', '胸憋'],
    '发绀': ['紫绀', '青紫'],
    '杵状指': ['鼓槌指'],
    '水肿': ['浮肿', '肿胀'],
    '意识障碍': ['神志不清', '昏迷', '嗜睡', '谵妄'],
    '发热': ['发烧', '高热', '低热'],
    '乏力': ['疲倦', '疲劳', '无力', '虚弱'],
    '消瘦': ['体重下降', '体重减轻', '营养不良'],
    '失眠': ['睡眠障碍', '入睡困难'],
    '头痛': ['头疼'],
    '头晕': ['眩晕', '头昏'],
    '恶心': ['作呕', '想吐'],
    '呕吐': ['呕吐', '吐'],
    '腹泻': ['拉肚子', '泄泻'],
    '便秘': ['大便干结'],
    '腹胀': ['腹部胀满', '腹膨隆'],
    '腹痛': ['肚子疼', '腹部疼痛'],

    # === 并发症/合并症 ===
    '肺动脉高压': ['肺高压', 'PH'],
    '肺心病': ['慢性肺源性心脏病', '肺源性心脏病'],
    '呼吸衰竭': ['呼衰', '呼吸功能衰竭', 'Ⅰ型呼吸衰竭', 'Ⅱ型呼吸衰竭'],
    '心力衰竭': ['心衰', '心功能衰竭', '心功能不全', '充血性心力衰竭'],
    '心律失常': ['心律不齐', '心律紊乱'],
    '心肌梗死': ['心梗', '心肌梗塞', 'MI'],
    '心绞痛': ['胸痛', '心前区疼痛'],
    '高血压': ['血压升高', 'HTN'],
    '糖尿病': ['DM', '血糖升高'],
    '代谢综合征': ['MetS'],
    '骨质疏松': ['骨量减少', '骨质稀疏'],
    '骨质疏松症': ['骨质疏松'],
    '抑郁症': ['抑郁', '抑郁障碍', '抑郁发作'],
    '焦虑症': ['焦虑', '焦虑障碍'],
    '胃食管反流病': ['GERD', '胃食管反流', '反流'],
    '睡眠呼吸暂停综合征': ['OSA', 'OSAS', '阻塞性睡眠呼吸暂停'],
    '肺癌': ['支气管肺癌', '肺恶性肿瘤'],
    '肺炎': ['肺部感染', '肺感染'],
    '自发性气胸': ['气胸'],
    '胸腔积液': ['胸水', '胸膜腔积液'],
    '肺栓塞': ['PE', '肺血栓栓塞'],
    '深静脉血栓': ['DVT'],
    '贫血': ['低血红蛋白血症'],
    '营养不良': ['营养缺乏', '营养不足'],
    '肌少症': ['肌肉减少症', '骨骼肌减少'],

    # === 治疗方法 ===
    '戒烟': ['禁烟', '停止吸烟', '戒除吸烟'],
    '氧疗': ['吸氧', '氧气治疗', '长期氧疗', 'LTOT'],
    '无创通气': ['NPPV', 'NIPPV', '无创正压通气', 'BiPAP', 'CPAP'],
    '机械通气': ['有创通气', '呼吸机辅助通气', '插管通气'],
    '肺康复': ['呼吸康复', '肺康复治疗', '呼吸训练'],
    '肺减容手术': ['LVRS', '肺减容术'],
    '肺移植': ['肺移植术', '换肺'],
    '支气管镜肺减容术': ['BLVR', '支气管镜肺减容'],
    '疫苗接种': ['预防接种', '打疫苗'],
    '营养支持': ['营养治疗', '肠内营养', '肠外营养'],

    # === 致病因素 ===
    '吸烟': ['烟草使用', '主动吸烟', ' cigarette smoking'],
    '被动吸烟': ['二手烟', '环境烟草烟雾'],
    '烟草烟雾': ['香烟烟雾', '烟草烟气'],
    '空气污染': ['大气污染', '环境空气污染'],
    '职业粉尘': ['职业暴露', '粉尘暴露', '硅尘', '煤尘'],
    '生物燃料烟雾': ['柴火烟雾', '厨房烟雾'],
    '感染': ['呼吸道感染', '细菌感杂', '病毒感染'],
    '遗传因素': ['基因因素', '家族遗传', '先天因素'],
    '年龄因素': ['老龄化', '年龄增长'],
    '性别因素': ['男性', '女性', '性别差异'],

    # === 其他重要概念 ===
    '合并症': ['共病', '伴随疾病', '合并疾病'],
    '病死率': ['死亡率', '死亡风险'],
    '生活质量': ['生命质量', '生存质量', 'QoL', '健康相关生活质量'],
    '肺功能': ['肺通气功能', '肺换气功能', '呼吸功能'],
    '肺功能检查': ['肺量计检查', ' spirometry', '通气功能检查'],
    '支气管哮喘': ['哮喘', 'bronchial asthma'],
    '气道高反应性': ['AHR', '气道反应性增高'],
    '黏液高分泌': ['痰液过多', '黏液分泌过多'],
    '系统性炎症': ['全身炎症', '系统性炎性反应'],
    '氧化应激': ['氧化损伤'],
    '蛋白酶-抗蛋白酶失衡': ['弹性蛋白酶失衡'],
}

# 反向映射：从别名查到标准形式
ALIAS_TO_STANDARD = {}
for standard, aliases in SYNONYM_MAP.items():
    for alias in aliases:
        ALIAS_TO_STANDARD[alias] = standard
    # 标准形式也映射到自身
    ALIAS_TO_STANDARD[standard] = standard

# ================== 过长非术语过滤 ==================
# 这些模式表示该词不是一个单一医学术语，而是短语/标题/句子
NON_TERM_PATTERNS = [
    '指南', '原则', '标准', '规范', '共识', '要点', '解读', '建议', '意见',
    '要点解读', '更新要点', '诊治指南', '临床指南', '实践指南',
    '提高', '改善', '降低', '减少', '增加', '促进', '防止', '避免',
    '调查', '研究', '分析', '探讨', '观察', '报告', '结果显示',
    '危险因素', '危险度', '患病率', '发病率', '死亡率', '生存率',
    '患者的', '患者的管理', '患者的教育', '患者的随访',
    '总体来说', '修订版指出', '调查结果显示',
    '的定义', '的诊断', '的治疗', '的管理', '的预防', '的评估',
    '应注意', '应注意的', '注意事项', '需要注意',
]

def is_non_term(word):
    """判断是否为非术语短语"""
    # 超过10个字且不含标准医学缩写，大概率不是单一术语
    if len(word) > 10:
        # 例外：如果包含已知的标准术语，可能是复合术语
        has_known_term = any(term in word for term in SYNONYM_MAP.keys())
        if not has_known_term:
            return True
    # 匹配非术语模式
    for pattern in NON_TERM_PATTERNS:
        if pattern in word and len(word) > 6:
            return True
    return False


def normalize_term(word):
    """术语归一化"""
    # 1. 直接查同义词表
    if word in ALIAS_TO_STANDARD:
        return ALIAS_TO_STANDARD[word]

    # 2. 子串匹配：如果某个别名是当前词的子串，也归一化
    for alias, standard in ALIAS_TO_STANDARD.items():
        if alias in word and len(alias) >= 4:
            # 但避免错误匹配：如"肺炎"是"肺癌"的子串
            if word == alias or word.startswith(alias) or word.endswith(alias):
                return standard

    return word


def main():
    print("=" * 70)
    print("种子词典术语归一化")
    print("=" * 70)

    # 读取原始词表
    with open(INPUT_WORDLIST, 'r', encoding='utf-8') as f:
        raw_words = [line.strip() for line in f if line.strip()]

    print(f"\n输入词表: {len(raw_words)} 条")

    # 读取完整JSON（用于保留频次信息）
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    word_info = {item['word']: item for item in raw_data}

    # 步骤1：归一化 + 过滤非术语
    normalized_map = {}  # 标准形式 -> {同义词列表, 总频次, 最佳来源}
    discarded = []

    for word in raw_words:
        # 过滤非术语
        if is_non_term(word):
            discarded.append((word, '非术语短语'))
            continue

        # 归一化
        standard = normalize_term(word)

        if standard not in normalized_map:
            normalized_map[standard] = {
                'aliases': set(),
                'freq': 0,
                'score': 0,
                'sources': []
            }

        info = word_info.get(word, {})
        entry = normalized_map[standard]

        if word != standard:
            entry['aliases'].add(word)

        entry['freq'] += info.get('freq', 1)
        entry['score'] += info.get('score', 0)
        entry['sources'].append({
            'word': word,
            'freq': info.get('freq', 0),
            'title_freq': info.get('title_freq', 0),
            'bold_freq': info.get('bold_freq', 0),
            'table_freq': info.get('table_freq', 0),
        })

    # 步骤2：整理结果
    results = []
    for standard, data in normalized_map.items():
        # 合并来源统计
        total_title = sum(s['title_freq'] for s in data['sources'])
        total_bold = sum(s['bold_freq'] for s in data['sources'])
        total_table = sum(s['table_freq'] for s in data['sources'])

        # 如果有同义词，生成备注
        alias_str = '、'.join(sorted(data['aliases'])) if data['aliases'] else ''

        results.append({
            'standard': standard,
            'aliases': sorted(data['aliases']),
            'alias_str': alias_str,
            'freq': data['freq'],
            'score': round(data['score'], 1),
            'title_freq': total_title,
            'bold_freq': total_bold,
            'table_freq': total_table,
        })

    # 按得分排序
    results.sort(key=lambda x: x['score'], reverse=True)

    print(f"归一化后: {len(results)} 条标准术语")
    print(f"过滤非术语: {len(discarded)} 条")
    print(f"合并同义词: {sum(len(r['aliases']) for r in results)} 个别名被合并")

    # 保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1) 归一化词表（标准形式 + 同义词）
    tsv_path = os.path.join(OUTPUT_DIR, '14_核心4篇_归一化种子词典.tsv')
    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.write("排名\t标准术语\t同义词\t总频次\t标题\t加粗\t表格\t得分\n")
        for i, r in enumerate(results, 1):
            alias_display = r['alias_str'] if r['alias_str'] else '-'
            f.write(f"{i}\t{r['standard']}\t{alias_display}\t{r['freq']}\t{r['title_freq']}\t{r['bold_freq']}\t{r['table_freq']}\t{r['score']}\n")

    # 2) 纯标准词表
    wordlist_path = os.path.join(OUTPUT_DIR, '14_核心4篇_归一化种子词典_标准词表.txt')
    with open(wordlist_path, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(r['standard'] + '\n')

    # 3) 含同义词的完整词表（用于后续实体识别）
    full_wordlist_path = os.path.join(OUTPUT_DIR, '14_核心4篇_归一化种子词典_含同义词.txt')
    with open(full_wordlist_path, 'w', encoding='utf-8') as f:
        for r in results:
            line = r['standard']
            if r['aliases']:
                line += ' | ' + ' | '.join(r['aliases'])
            f.write(line + '\n')

    # 4) 被丢弃的词
    discard_path = os.path.join(OUTPUT_DIR, '14_核心4篇_归一化_被过滤的非术语.txt')
    with open(discard_path, 'w', encoding='utf-8') as f:

        for word, reason in discarded:
            f.write(f"{word}\t{reason}\n")

    print(f"\n[已保存]")
    print(f"  归一化TSV: {tsv_path}")
    print(f"  标准词表: {wordlist_path}")
    print(f"  含同义词词表: {full_wordlist_path}")
    print(f"  被过滤词: {discard_path}")

    # 预览
    print("\n" + "=" * 70)
    print("Top 30 归一化种子词典")
    print("=" * 70)
    print(f"{'排名':<4} {'标准术语':<22} {'同义词':<30} {'频次':<5} {'得分':<8}")
    print("-" * 75)
    for i, r in enumerate(results[:30], 1):
        alias_short = r['alias_str'][:28] if r['alias_str'] else '-'
        print(f"{i:<4} {r['standard']:<22} {alias_short:<30} {r['freq']:<5} {r['score']:<8.1f}")

    # 显示同义词合并示例
    print("\n" + "=" * 70)
    print("同义词合并示例")
    print("=" * 70)
    merged_examples = [r for r in results if len(r['aliases']) >= 2]
    print(f"共有 {len(merged_examples)} 个术语完成了同义词合并：\n")
    for r in merged_examples[:15]:
        print(f"  【{r['standard']}】 ← {', '.join(r['aliases'])}")


if __name__ == '__main__':
    main()
