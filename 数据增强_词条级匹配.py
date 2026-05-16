import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课题2：数据增强 —— 基于已有真实百度百科数据重新匹配
策略：从"句子级严格匹配"改为"词条级宽松匹配"
保留全部原始真实数据，不添加任何外部文本
"""

import os
import json
import re

SAVE_DIR = r"I:\101实验专题"


def log(msg):
    print(f"  → {msg}")


# 已有的56个真实医学标准三元组（保持不变）
GOLD_STANDARD = [
    {"head": "糖尿病", "relation": "症状", "tail": "多饮"},
    {"head": "糖尿病", "relation": "症状", "tail": "多食"},
    {"head": "糖尿病", "relation": "症状", "tail": "多尿"},
    {"head": "糖尿病", "relation": "症状", "tail": "体重下降"},
    {"head": "糖尿病", "relation": "症状", "tail": "乏力"},
    {"head": "糖尿病", "relation": "症状", "tail": "视力模糊"},
    {"head": "2型糖尿病", "relation": "症状", "tail": "多饮"},
    {"head": "2型糖尿病", "relation": "症状", "tail": "多食"},
    {"head": "2型糖尿病", "relation": "症状", "tail": "多尿"},
    {"head": "2型糖尿病", "relation": "症状", "tail": "体重下降"},
    {"head": "1型糖尿病", "relation": "症状", "tail": "多饮"},
    {"head": "1型糖尿病", "relation": "症状", "tail": "多食"},
    {"head": "1型糖尿病", "relation": "症状", "tail": "多尿"},
    {"head": "糖尿病", "relation": "药物治疗", "tail": "二甲双胍"},
    {"head": "糖尿病", "relation": "药物治疗", "tail": "格列美脲"},
    {"head": "糖尿病", "relation": "药物治疗", "tail": "阿卡波糖"},
    {"head": "糖尿病", "relation": "药物治疗", "tail": "胰岛素"},
    {"head": "糖尿病", "relation": "药物治疗", "tail": "西格列汀"},
    {"head": "糖尿病", "relation": "药物治疗", "tail": "达格列净"},
    {"head": "2型糖尿病", "relation": "药物治疗", "tail": "二甲双胍"},
    {"head": "2型糖尿病", "relation": "药物治疗", "tail": "格列美脲"},
    {"head": "2型糖尿病", "relation": "药物治疗", "tail": "阿卡波糖"},
    {"head": "1型糖尿病", "relation": "药物治疗", "tail": "胰岛素"},
    {"head": "糖尿病", "relation": "检查", "tail": "血糖检测"},
    {"head": "糖尿病", "relation": "检查", "tail": "糖化血红蛋白"},
    {"head": "糖尿病", "relation": "检查", "tail": "口服葡萄糖耐量试验"},
    {"head": "糖尿病", "relation": "检查", "tail": "尿糖检测"},
    {"head": "糖尿病", "relation": "检查", "tail": "空腹血糖"},
    {"head": "糖尿病", "relation": "检查", "tail": "餐后2小时血糖"},
    {"head": "2型糖尿病", "relation": "检查", "tail": "血糖检测"},
    {"head": "2型糖尿病", "relation": "检查", "tail": "糖化血红蛋白"},
    {"head": "糖尿病", "relation": "并发症", "tail": "糖尿病视网膜病变"},
    {"head": "糖尿病", "relation": "并发症", "tail": "糖尿病肾病"},
    {"head": "糖尿病", "relation": "并发症", "tail": "糖尿病足"},
    {"head": "糖尿病", "relation": "并发症", "tail": "糖尿病酮症酸中毒"},
    {"head": "糖尿病", "relation": "并发症", "tail": "心血管疾病"},
    {"head": "2型糖尿病", "relation": "并发症", "tail": "糖尿病视网膜病变"},
    {"head": "2型糖尿病", "relation": "并发症", "tail": "糖尿病肾病"},
    {"head": "糖尿病", "relation": "就诊科室", "tail": "内分泌科"},
    {"head": "2型糖尿病", "relation": "就诊科室", "tail": "内分泌科"},
    {"head": "1型糖尿病", "relation": "就诊科室", "tail": "内分泌科"},
    {"head": "糖尿病视网膜病变", "relation": "就诊科室", "tail": "眼科"},
    {"head": "糖尿病肾病", "relation": "就诊科室", "tail": "肾内科"},
    {"head": "糖尿病足", "relation": "就诊科室", "tail": "血管外科"},
    {"head": "二甲双胍", "relation": "作用机制", "tail": "减少肝糖输出"},
    {"head": "二甲双胍", "relation": "作用机制", "tail": "改善胰岛素敏感性"},
    {"head": "格列美脲", "relation": "作用机制", "tail": "刺激胰岛β细胞分泌胰岛素"},
    {"head": "阿卡波糖", "relation": "作用机制", "tail": "延缓碳水化合物吸收"},
    {"head": "西格列汀", "relation": "作用机制", "tail": "抑制DPP-4酶活性"},
    {"head": "达格列净", "relation": "作用机制", "tail": "促进尿糖排泄"},
    {"head": "胰岛素", "relation": "作用机制", "tail": "促进葡萄糖摄取"},
    {"head": "胰岛素", "relation": "作用机制", "tail": "降低血糖"},
    {"head": "糖化血红蛋白", "relation": "临床意义", "tail": "反映近3个月平均血糖水平"},
    {"head": "空腹血糖", "relation": "临床意义", "tail": "诊断糖尿病的重要指标"},
    {"head": "口服葡萄糖耐量试验", "relation": "临床意义", "tail": "评估机体葡萄糖调节能力"},
    {"head": "尿糖检测", "relation": "临床意义", "tail": "辅助判断血糖控制情况"}
]


def 加载百度百科词条():
    """按词条分割，保留原始格式"""
    baidu_file = os.path.join(SAVE_DIR, "1_原始文本_百度百科糖尿病词条_扩展版.txt")
    if not os.path.exists(baidu_file):
        baidu_file = os.path.join(SAVE_DIR, "1_原始文本_百度百科糖尿病词条.txt")

    with open(baidu_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 按 ===== 分割成独立词条
    raw_entries = re.split(r'=+', content)

    entries = []
    for entry in raw_entries:
        entry = entry.strip()
        if len(entry) < 30:
            continue

        # 提取词条名称
        name_match = re.search(r'【词条名称】(.*?)\n', entry)
        name = name_match.group(1).strip() if name_match else "未知词条"

        # 去掉标记，保留纯文本内容
        clean = re.sub(r'【词条名称】', '', entry)
        clean = re.sub(r'【词条摘要】', '\n', clean)
        clean = re.sub(r'【词条内容】', '\n', clean)
        clean = clean.strip()

        entries.append({
            "词条名": name,
            "原文": entry,
            "纯文本": clean,
            "字数": len(clean)
        })

    return entries


def 词条级远程监督匹配(entries, triples):
    """
    核心改进：不再要求同一句子，只要head和tail出现在同一个词条文本中即可
    """
    print("\n" + "=" * 60)
    print("【重新匹配】采用词条级宽松策略...")
    print("=" * 60)

    labeled_data = []

    for entry in entries:
        text = entry["纯文本"]
        name = entry["词条名"]

        for t in triples:
            h = t["head"]
            r = t["relation"]
            tail = t["tail"]

            # 宽松条件：head和tail都出现在这个词条里
            if h in text and tail in text:
                # 提取包含这两个实体的上下文片段
                idx_h = text.find(h)
                idx_t = text.find(tail)

                # 取两个实体前后各扩展60字，或整个相关句子
                start = max(0, min(idx_h, idx_t) - 60)
                end = min(len(text), max(idx_h, idx_t) + max(len(h), len(tail)) + 60)
                context = text[start:end]

                # 如果片段太长，截断
                if len(context) > 300:
                    context = context[:300] + "..."

                # 找到包含这两个实体的最相关句子（用于展示）
                sentences = re.split(r'[。！？\n]', text)
                best_sent = ""
                for sent in sentences:
                    if h in sent and tail in sent:
                        best_sent = sent.strip()
                        break
                # 如果同一句子找不到，就用上下文片段

                labeled_data.append({
                    "词条名": name,
                    "上下文片段": context,
                    "相关句子": best_sent if best_sent else context[:100],
                    "实体1": h,
                    "关系": r,
                    "实体2": tail,
                    "匹配级别": "词条级",
                    "标注方式": "远程监督",
                    "数据来源": "百度百科真实词条+医学标准库"
                })

    # 去重（按实体对+关系，保留最长上下文）
    best = {}
    for item in labeled_data:
        key = (item["实体1"], item["关系"], item["实体2"])
        if key not in best or len(item["上下文片段"]) > len(best[key]["上下文片段"]):
            best[key] = item

    unique_data = list(best.values())

    # 保存
    output_file = os.path.join(SAVE_DIR, "4_远程监督训练数据_词条级匹配.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(unique_data, f, ensure_ascii=False, indent=2)

    # 统计
    句子级 = sum(
        1 for d in unique_data if d["相关句子"] and d["实体1"] in d["相关句子"] and d["实体2"] in d["相关句子"])
    词条级 = len(unique_data) - 句子级

    print(f"\n✅ 匹配完成！")
    print(f"  总样本数: {len(unique_data)} 条")
    print(f"  其中同句匹配: {句子级} 条（高质量）")
    print(f"  词条级匹配: {词条级} 条（可用）")
    print(f"  → {output_file}")

    # 按关系分布
    print(f"\n【按关系类型分布】")
    rel_count = {}
    for item in unique_data:
        rel_count[item["关系"]] = rel_count.get(item["关系"], 0) + 1
    for r, c in sorted(rel_count.items(), key=lambda x: -x[1]):
        print(f"  {r}: {c} 条")

    # 按词条分布
    print(f"\n【按词条分布（前10）】")
    entry_count = {}
    for item in unique_data:
        entry_count[item["词条名"]] = entry_count.get(item["词条名"], 0) + 1
    for name, c in sorted(entry_count.items(), key=lambda x: -x[1])[:10]:
        print(f"  {name}: {c} 条匹配")

    return unique_data


def 生成最终报告(train_count):
    print("\n" + "=" * 60)
    print("【最终数据报告】")
    print("=" * 60)

    # 对比
    old_file = os.path.join(SAVE_DIR, "4_远程监督训练数据.json")
    old_count = 0
    if os.path.exists(old_file):
        with open(old_file, "r", encoding="utf-8") as f:
            old_count = len(json.load(f))

    print(f"  严格句子级匹配（旧）: {old_count} 条")
    print(f"  宽松词条级匹配（新）: {train_count} 条")
    print(f"  提升倍数: {train_count / max(old_count, 1):.1f}x")

    if train_count >= 100:
        print("\n  ✅ 数据量充足，可用于BERT微调！")
    elif train_count >= 50:
        print("\n  ⚠ 数据量基本够用，建议后续再补充2-3篇真实医学文章")
    else:
        print("\n  ❌ 数据量仍然偏少，需要补充原始文本")

    print(f"\n  所有文件保存在: {SAVE_DIR}")
    print("=" * 60)


def main():
    print("=" * 60)
    print("课题2：数据增强 —— 词条级宽松匹配")
    print("保留全部原始真实数据，仅优化匹配策略")
    print("=" * 60)

    entries = 加载百度百科词条()
    log(f"加载到 {len(entries)} 个真实百度百科词条")

    # 显示词条长度分布
    长词条 = [e for e in entries if e["字数"] > 200]
    短词条 = [e for e in entries if e["字数"] <= 200]
    log(f"  长词条(>200字): {len(长词条)} 个 —— 主要匹配来源")
    log(f"  短词条(≤200字): {len(短词条)} 个 —— 匹配贡献较少")

    train_data = 词条级远程监督匹配(entries, GOLD_STANDARD)
    生成最终报告(len(train_data))

    print("\n✅ 完成！请查看新文件: 4_远程监督训练数据_词条级匹配.json")


if __name__ == "__main__":
    main()