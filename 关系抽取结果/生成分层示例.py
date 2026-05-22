#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import config  # 统一路径配置
import csv
from collections import defaultdict

rows = []
with open('v4_最大覆盖版_原始三元组_带溯源.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

groups = defaultdict(list)
for r in rows:
    groups[r['关系类型']].append(r)

output_path = '审核参考_各关系类型代表性示例.txt'
with open(output_path, 'w', encoding='utf-8-sig') as out:
    out.write('=' * 80 + '\n')
    out.write('COPD关系抽取审核 -- 各关系类型代表性示例\n')
    out.write('=' * 80 + '\n')
    
    for rel_type in ['疾病-症状', '药物-治疗-疾病', '危险因素-疾病', '疾病-治疗', '检查-辅助诊断-疾病', '疾病-并发症', '相关']:
        items = groups[rel_type]
        explicit_count = sum(1 for x in items if x['匹配类型'] == 'explicit')
        cooccur_count = len(items) - explicit_count
        out.write('\n')
        out.write(f'【{rel_type}】共 {len(items)} 条 (explicit: {explicit_count}, cooccur: {cooccur_count})\n')
        out.write('-' * 60 + '\n')
        
        shown = 0
        for r in items:
            if r['匹配类型'] == 'explicit' and shown < 2:
                sent = r['原始句子']
                if len(sent) > 120:
                    sent = sent[:120] + '...'
                out.write(f'  保留示例: {r["头实体"]} → {r["尾实体"]}\n')
                out.write(f'    证据: {sent}\n')
                out.write('\n')
                shown += 1
        
        for r in items:
            if r['匹配类型'] == 'cooccur' and shown < 3:
                sent = r['原始句子']
                if len(sent) > 120:
                    sent = sent[:120] + '...'
                out.write(f'  共现实例: {r["头实体"]} → {r["尾实体"]}\n')
                out.write(f'    证据: {sent}\n')
                out.write('\n')
                shown += 1
                break

print(f"已生成: {output_path}")
