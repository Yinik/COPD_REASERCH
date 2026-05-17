@echo off
chcp 65001 >nul
echo ============================================================
echo   COPD知识图谱项目 - 一键演示脚本
echo ============================================================
echo.
echo 本脚本将依次执行：
echo   1. 项目数据完整性验证
echo   2. 知识图谱可视化生成
echo   3. 打开产出目录查看结果
echo.
echo ============================================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请确保Python已安装并加入PATH
    pause
    exit /b 1
)

echo [1/3] 运行数据完整性验证...
python verify_project.py
if errorlevel 1 (
    echo [警告] 验证未完全通过，请检查上方输出
) else (
    echo [通过] 数据验证完成
)

echo.
echo [2/3] 生成知识图谱可视化图片...
python generate_kg_viz.py
echo [通过] 可视化图片已生成到 assets/ 目录

echo.
echo [3/3] 打开产出目录...
if exist assets start assets
echo.

echo ============================================================
echo   演示完成！
echo ============================================================
echo.
echo 产出文件：
echo   - assets/kg_full.png        : 完整知识图谱
echo   - assets/kg_copd_core.png   : COPD中心辐射图
echo   - assets/kg_drug.png        : 药物子图
echo   - assets/kg_symptom.png     : 症状子图
echo   - assets/relation_stats.png : 关系统计图
echo   - assets/entity_pie.png     : 实体分布图
echo.
echo 下一步（可选）：
echo   - 启动Neo4j并导入数据：见 关系抽取结果/Neo4j导入教程.md
echo   - 运行端到端演示：python COPD图谱端到端抽取系统.py
echo.
pause
