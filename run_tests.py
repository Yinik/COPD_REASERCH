#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试运行脚本
用法: python run_tests.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 禁用BERT模型加载（加速测试）
import COPD图谱端到端抽取系统_v2 as _mod
_mod.USE_BERT = False

# 发现并运行所有测试
loader = unittest.TestLoader()
suite = loader.discover('tests', pattern='test_*.py')

# 运行测试
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# 输出摘要
print("\n" + "="*60)
print("测试摘要")
print("="*60)
print(f"总测试数: {result.testsRun}")
print(f"通过: {result.testsRun - len(result.failures) - len(result.errors)}")
print(f"失败: {len(result.failures)}")
print(f"错误: {len(result.errors)}")
print("="*60)

# 返回非零退出码如果有失败
sys.exit(0 if result.wasSuccessful() else 1)
