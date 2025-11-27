#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyInstaller打包脚本
用于构建ZifeiyuSec.exe可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# 项目根目录
PROJECT_ROOT = os.path.abspath('.')

# 确保dist目录存在
dist_dir = os.path.join(PROJECT_ROOT, 'dist')
if not os.path.exists(dist_dir):
    os.makedirs(dist_dir)

# 清理之前的构建
for item in ['build', 'dist/ZifeiyuSec']:
    item_path = os.path.join(PROJECT_ROOT, item)
    if os.path.exists(item_path):
        print(f"清理目录: {item_path}")
        shutil.rmtree(item_path)

# PyInstaller命令行参数
pyinstaller_args = [
    'pyinstaller',
    '--name=ZifeiyuSec',  # 输出文件名
    '--windowed',  # 无控制台窗口
    '--onefile',  # 打包成单个文件
    # 移除不存在的图标引用
    '--distpath=dist',  # 输出目录
    '--hidden-import=PyQt5.QtWidgets',
    '--hidden-import=PyQt5.QtGui',
    '--hidden-import=PyQt5.QtCore',
    'main.py'  # 主脚本
]

print("开始打包...")
print(f"执行命令: {' '.join(pyinstaller_args)}")

# 执行PyInstaller命令
result = subprocess.run(
    pyinstaller_args,
    cwd=PROJECT_ROOT,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# 打印输出
print("\nPyInstaller输出:")
print(result.stdout)

if result.stderr:
    print("\n错误信息:")
    print(result.stderr)

if result.returncode == 0:
    print("\n✅ 打包成功!")
    # 检查是否生成了exe文件
    exe_path = os.path.join(dist_dir, 'ZifeiyuSec.exe')
    if os.path.exists(exe_path):
        print(f"可执行文件路径: {exe_path}")
        # 创建data文件夹
        data_dir = os.path.join(dist_dir, 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"创建了data目录: {data_dir}")
            print("\n📋 打包完成后的使用说明:")
            print("1. 请将categories.json和tools.json复制到data目录中")
            print("2. 运行ZifeiyuSec.exe即可使用")
    else:
        print("❌ 未找到生成的可执行文件")
else:
    print(f"\n❌ 打包失败，返回代码: {result.returncode}")
