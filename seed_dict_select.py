# -*- coding: utf-8 -*-
"""
种子词典半自动精选辅助工具
将第一步 PMI+熵 的候选词自动分为：高置信度 / 待审核 / 建议丢弃
减少人工筛选工作量
"""
import config  # 统一路径配置


import os
import json

INPUT_JSON = str(config.BASE_DIR / r"seed_dict_cleaned.json")
OUTPUT_DIR = r"I:\101实验专题"

# ================== 规则配置 ==================

# 医学特征词根（用于正向匹配）
MEDICAL_KEYWORDS = [
    # 疾病/病理
    '病', '症状', '炎', '癌', '瘤', '感染', '综合征', '综合征', '并发症', '合并症',
    '梗阻', '梗死', '梗塞', '出血', '坏死', '溃疡', '糜烂', '结节', '息肉', '囊肿',
    '脓肿', '积液', '积脓', '纤维化', '钙化', '硬化', '肥大', '增生', '萎缩', '变性',
    '狭窄', '扩张', '阻塞', '闭塞', '穿孔', '破裂', '脱垂', '疝', '瘘', '畸形',
    # 药物
    '药', '素', '剂', '胶囊', '片', '注射', '口服液', '丸', '散', '膏', '丹', '颗粒',
    '冲剂', '喷雾', '吸入', '雾化', '贴剂', '滴眼', '滴鼻', '滴耳', '栓剂',
    # 症状/体征
    '痛', '咳', '喘', '闷', '烧', '晕', '吐', '泻', '肿', '胀', '麻', '痿', '瘫',
    '红', '疹', '斑', '瘀', '黄', '白', '绀', '湿', '干', '冷', '热',
    # 检查/操作
    '镜', '超声', '造影', '活检', '穿刺', '灌注', '扫描', '电图', '波', '像',
    '术', '切除', '移植', '插管', '透析', '引流', '缝合', '清创', '重建', '修复',
    '置换', '成形', '植入', '支架', '搭桥', '消融', '放疗', '化疗', '介入',
    # 解剖/生理
    '肺', '心', '肝', '肾', '脑', '胃', '肠', '脾', '胆', '胰', '血管', '支气管',
    '气管', '动脉', '静脉', '毛细血管', '神经', '肌肉', '骨骼', '胸', '腹', '脊',
    '喉', '咽', '鼻', '耳', '眼', '皮肤', '黏膜', '膜', '腔', '窦', '管', '腺',
    # 功能/指标
    '压', '率', '容积', '容量', '流速', '流量', '阻力', '顺应性', '弥散', '通气',
    '换气', '灌注', '氧', '二氧化碳', '酸碱', '血气', '电解质', '糖', '脂', '蛋白',
    '酶', '激素', '抗体', '抗原', '受体', '基因', '细胞', '分子',
    # 免疫/炎症
    '免疫', '炎症', '过敏', '变态反应', '因子', '介质', '趋化', '吞噬', '应答',
    # 病程/预后
    '急', '慢', '轻', '重', '早期', '晚期', '急性', '慢性', '亚急性', '潜伏', '隐匿',
    '原发', '继发', '转移', '复发', '扩散', '播散', '浸润', '侵袭', '恶化', '加重',
    '好转', '痊愈', '缓解', '控制', '稳定', '迁延', '顿挫', '波动',
    # COPD专科
    '戒烟', '支气管舒张', '支气管扩张', '吸入装置', '储雾罐', '峰流速', '雾化器',
    '糖皮质激素', '支气管痉挛', '黏液栓', '肺气肿', '肺心病', '呼吸衰竭', '肺动脉高压',
    '氧疗', '机械通气', '无创通气', '肺康复', '呼吸肌', '膈肌',
]

# 虚字/结构字：候选词如果包含这些字，极大概率不是独立术语
STOP_CHARS = set(
    '的了和在是为以及其该此而但若如于之将被打把从向到由因则所即便就都也还又再已正很太'
    '非常已经正在可以应该可能通过进行使用建议需要目前情况选择研究改善相关推荐考虑根据'
    '必须记录标准观察这些策略存在减少导致降低措施出现形成成为作为列为定为视为认为称为'
    '命名分为包括评估影响比较相对绝对完全彻底总体大概大约具有发生未见明显显著一致相似'
    '相同不同差异区别分别各自依次逐步相继陆续连续反复多次数次初次首次每次历次期次批次'
    '例次人次例数人数次数频率比例构成分布结构特点特征特性性质属性状态状况情形形势局面'
    '情景场景场合场所地点位置方位方向趋势动向动态态势格局模式形式方式方法手段途径渠道'
    '路线路径过程历程进程流程程序步骤环节阶段时期期间时候时刻时间时机时限年代年度年份'
    '年月月份日期日子当天当日次日隔天连日以往过去曾经历来向来从来始终一直一贯一向根本'
    '压根简直几乎差不多约莫估计推测猜测猜想预计预期预料预见预测打算计划准备安排部署布置'
    '配置设置设定确定决定规定制定制订拟定拟订起草草拟编制编撰编纂编写撰写写作创作创造'
    '创立创建建立建设设立成立建成组合整合综合集合聚集汇集汇总收集搜集采集摄取吸收吸取'
    '汲取提取筛选挑选选取选用采用采纳接受接收受到获得得到取得赢得博得赚得挣得摘得夺得'
    '抢占占领占据占有拥有具备附有带有含有包含囊括涵盖涉及牵涉牵扯关联联系关系有关相应'
    '对应对照对比比拟类比类似相近相仿相当等于等价等同一样同样统一单一单纯纯粹简单简便'
    '简易简洁简明简略简要概括归纳总结统筹协调协同协作合作配合搭配配套匹配符合适合适宜'
    '适应适用恰当妥当妥善合适相宜适中适度适量适时适地适龄得当得体得法得力得宜得益得利'
    '得势得手得逞得胜得闲得空得便得暇'
)

# 2字常见非术语通用词（在医学文本中高频出现但非实体）
COMMON_BIWORDS = {
    '治疗', '患者', '药物', '临床', '研究', '症状', '诊断', '进行', '使用', '建议',
    '根据', '包括', '评估', '相关', '改善', '需要', '存在', '采取', '给予', '处理',
    '调整', '启动', '开展', '实施', '完成', '达到', '获得', '出现', '发生', '引起',
    '导致', '造成', '促进', '推动', '阻止', '防止', '避免', '减少', '降低', '增加',
    '提高', '维持', '保持', '恢复', '缓解', '减轻', '加重', '死亡', '预后', '结局',
    '事件', '水平', '程度', '情况', '结果', '目的', '目标', '意义', '作用', '效果',
    '因素', '原因', '机制', '方法', '方式', '途径', '模式', '类型', '种类', '等级',
    '标准', '指标', '参数', '数据', '资料', '文献', '报道', '分析', '探讨', '讨论',
    '说明', '介绍', '描述', '表明', '显示', '发现', '认为', '指出', '提出', '报告',
    '方面', '部分', '阶段', '过程', '范围', '幅度', '差异', '变化', '进展', '趋势',
    '方向', '问题', '困难', '挑战', '计划', '方案', '设计', '策略', '措施', '干预',
    '基础', '核心', '关键', '重点', '前提', '条件', '要求', '规定', '原则', '规范',
    '指南', '共识', '建议', '推荐', '意见', '声明', '草案', '试行', '修订', '更新',
    '版本', '章节', '段落', '内容', '信息', '知识', '技术', '技能', '能力', '素质',
    '质量', '安全', '风险', '危险', '危害', '损害', '损伤', '伤害', '不良', '严重',
    '轻微', '明显', '显著', '有效', '无效', '合理', '适当', '适宜', '适合', '正常',
    '异常', '典型', '非典型', '常见', '少见', '罕见', '多发', '散发', '流行', '地方',
    '季节', '周期', '持续', '反复', '间歇', '暂时', '永久', '一过性', '终身', '长期',
    '短期', '近期', '远期', '慢性', '急性', '亚急性', '慢性', '急性',
}

# =============================================


def contains_medical_keyword(word):
    """是否包含医学特征词根"""
    return any(kw in word for kw in MEDICAL_KEYWORDS)


def contains_stop_char(word):
    """是否包含结构虚字"""
    return any(c in STOP_CHARS for c in word)


def classify(item):
    """
    对单个候选词进行分类
    返回: ('auto' | 'review' | 'discard', reason)
    """
    word = item['word']
    pmi = item['pmi']
    score = item['score']
    freq = item['freq']
    length = len(word)

    # ========== 一票否决（直接丢弃） ==========
    # 含结构虚字（如“的X”、“X的”、“X中”等）
    if contains_stop_char(word):
        return 'discard', '含结构虚字'

    # 纯数字
    if word.isdigit():
        return 'discard', '纯数字'

    # 过长英文噪声
    if word.isalpha() and len(word) > 6 and not word.isupper():
        return 'discard', '过长英文'

    # 字母数字混合噪声
    import re
    if re.search(r'\d', word) and re.search(r'[a-zA-Z]', word) and not re.search(r'[\u4e00-\u9fff]', word):
        return 'discard', '字母数字混合'

    # 2字常见通用词
    if length == 2 and word in COMMON_BIWORDS:
        return 'discard', '2字常见通用词'

    # 低质量门槛
    if pmi < 5 or score < 12 or freq < 2:
        return 'discard', 'PMI/得分/频次过低'

    # ========== 高置信度（自动推荐） ==========
    # 包含医学特征词 + 质量过关
    if contains_medical_keyword(word):
        if pmi >= 7 and score >= 14 and freq >= 3:
            return 'auto', '含医学特征词且质量高'
        # 医学特征词但质量一般 -> 待审核
        return 'review', '含医学特征词但质量一般'

    # 标准医学缩写（全大写英文，2-5字符）
    if word.isupper() and word.isalpha() and 2 <= length <= 5:
        if pmi >= 7 and score >= 14:
            return 'auto', '标准医学缩写'
        return 'review', '英文缩写待确认'

    # 得分极高但无医学特征字（可能是人名/地名/机构名，需要审核）
    if score >= 17 and pmi >= 9:
        return 'review', '高分无医学特征字'

    # ========== 其余归入待审核 ==========
    if pmi >= 6 and score >= 13:
        return 'review', '中等质量待审核'

    return 'discard', '未满足任何正向条件'


def main():
    print("=" * 70)
    print("种子词典半自动精选辅助工具")
    print("=" * 70)

    # 读取候选词
    print(f"\n读取候选词: {INPUT_JSON}")
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"总候选词数量: {len(data)}")

    # 分类
    auto_list = []
    review_list = []
    discard_list = []

    for item in data:
        cat, reason = classify(item)
        item['category_reason'] = reason
        if cat == 'auto':
            auto_list.append(item)
        elif cat == 'review':
            review_list.append(item)
        else:
            discard_list.append(item)

    # 排序
    auto_list.sort(key=lambda x: x['score'], reverse=True)
    review_list.sort(key=lambda x: x['score'], reverse=True)
    discard_list.sort(key=lambda x: x['score'], reverse=True)

    print(f"\n分类结果:")
    print(f"  [高] 高置信度（自动推荐）: {len(auto_list)}")
    print(f"  [中] 中置信度（建议审核）: {len(review_list)}")
    print(f"  [低] 低置信度（建议丢弃）: {len(discard_list)}")

    # 保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    def save_tsv(path, items, include_reason=False):
        with open(path, 'w', encoding='utf-8') as f:
            if include_reason:
                f.write("排名\t词语\t频次\tPMI\t左熵\t右熵\t得分\t分类原因\n")
                for i, r in enumerate(items, 1):
                    f.write(f"{i}\t{r['word']}\t{r['freq']}\t{r['pmi']}\t{r['left_entropy']}\t{r['right_entropy']}\t{r['score']}\t{r['category_reason']}\n")
            else:
                f.write("排名\t词语\t频次\tPMI\t左熵\t右熵\t得分\n")
                for i, r in enumerate(items, 1):
                    f.write(f"{i}\t{r['word']}\t{r['freq']}\t{r['pmi']}\t{r['left_entropy']}\t{r['right_entropy']}\t{r['score']}\n")

    # 🟢 自动推荐
    save_tsv(os.path.join(OUTPUT_DIR, 'seed_dict_final_auto.tsv'), auto_list)
    with open(os.path.join(OUTPUT_DIR, 'seed_dict_final_auto_wordlist.txt'), 'w', encoding='utf-8') as f:
        for r in auto_list:
            f.write(r['word'] + '\n')

    # 🟡 待审核
    save_tsv(os.path.join(OUTPUT_DIR, 'seed_dict_final_review.tsv'), review_list, include_reason=True)

    # 🔴 丢弃
    save_tsv(os.path.join(OUTPUT_DIR, 'seed_dict_final_discard.tsv'), discard_list, include_reason=True)

    # 合并版（自动推荐 + 待审核）
    merged = auto_list + review_list
    with open(os.path.join(OUTPUT_DIR, 'seed_dict_final_merged_wordlist.txt'), 'w', encoding='utf-8') as f:

        for r in merged:
            f.write(r['word'] + '\n')

    print(f"\n[已保存]")
    print(f"  [高] seed_dict_final_auto.tsv / .txt  ({len(auto_list)}条)")
    print(f"  [中] seed_dict_final_review.tsv       ({len(review_list)}条)")
    print(f"  [低] seed_dict_final_discard.tsv      ({len(discard_list)}条)")
    print(f"  [合] seed_dict_final_merged_wordlist.txt ({len(merged)}条，auto+review)")

    # 预览
    print("\n" + "=" * 70)
    print("[高] 自动推荐 Top 20 预览")
    print("=" * 70)
    print(f"{'排名':<4} {'词语':<22} {'频次':<6} {'PMI':<8} {'得分':<8} {'原因'}")
    print("-" * 60)
    for i, r in enumerate(auto_list[:20], 1):
        print(f"{i:<4} {r['word']:<22} {r['freq']:<6} {r['pmi']:<8.2f} {r['score']:<8.2f} {r['category_reason']}")

    print("\n" + "=" * 70)
    print("[中] 待审核 Top 20 预览")
    print("=" * 70)
    print(f"{'排名':<4} {'词语':<22} {'频次':<6} {'PMI':<8} {'得分':<8} {'原因'}")
    print("-" * 60)
    for i, r in enumerate(review_list[:20], 1):
        print(f"{i:<4} {r['word']:<22} {r['freq']:<6} {r['pmi']:<8.2f} {r['score']:<8.2f} {r['category_reason']}")

    print("\n" + "=" * 70)
    print("[提示] 使用建议")
    print("=" * 70)
    print(f"1. [高] 自动推荐的 {len(auto_list)} 条可以直接用，不放心的话快速扫一眼即可。")
    print(f"2. [中] 待审核的 {len(review_list)} 条建议用Excel打开 seed_dict_final_review.tsv，")
    print("   逐行判断是否保留（删除行即表示丢弃）。")
    print(f"3. 若你觉得待审核里大部分都应该保留，可直接用 seed_dict_final_merged_wordlist.txt")
    print("   （包含 auto + review 的全部词语）。")
    print("4. 如需调整规则（比如某些医学词被误判了），修改本脚本中的 MEDICAL_KEYWORDS 或")
    print("   STOP_CHARS / COMMON_BIWORDS 后重新运行即可。")


if __name__ == '__main__':
    main()
