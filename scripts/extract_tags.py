#!/usr/bin/env python3
"""
批量提取 YAML/ YML 文件中 tags 字段并去重
用法: python extract_tags.py /path/to/directory [--output output.txt]
"""

import os
import sys
import argparse
import yaml
from pathlib import Path

def extract_tags_from_file(file_path):
    """从单个 YAML 文件中提取 tags 字段（可能为字符串或列表）

    兼容两种位置：
      - Nuclei 官方模板规范：info.tags（嵌套在 info 下）
      - 顶层 tags 字段（其他自定义结构）
    tags 值可能是逗号分隔字符串或列表。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if not data:
                return []
            # 优先取 info.tags（Nuclei 规范），其次取顶层 tags
            tags_raw = None
            info = data.get('info')
            if isinstance(info, dict):
                tags_raw = info.get('tags')
            if tags_raw is None:
                tags_raw = data.get('tags')
            if tags_raw is None:
                return []
            if isinstance(tags_raw, list):
                return [str(tag).strip() for tag in tags_raw if tag]
            if isinstance(tags_raw, str):
                parts = [p.strip() for p in tags_raw.split(',') if p.strip()]
                return parts
            return [str(tags_raw).strip()]
    except Exception as e:
        print(f"警告: 处理文件 {file_path} 时出错: {e}", file=sys.stderr)
        return []

def scan_directory(root_dir, extensions=('.yaml', '.yml')):
    """递归扫描目录，收集所有 tags"""
    all_tags = set()
    root = Path(root_dir)
    if not root.exists():
        print(f"错误: 目录 '{root_dir}' 不存在", file=sys.stderr)
        sys.exit(1)
    for file_path in root.rglob('*'):
        if file_path.suffix.lower() in extensions:
            tags = extract_tags_from_file(file_path)
            all_tags.update(tags)
    return all_tags

def main():
    parser = argparse.ArgumentParser(description='提取 YAML 文件中的 tags 字段并去重')
    parser.add_argument('directory', help='要扫描的根目录')
    parser.add_argument('-o', '--output', help='输出文件路径（不指定则打印到标准输出）')
    args = parser.parse_args()

    tags_set = scan_directory(args.directory)
    sorted_tags = sorted(tags_set)

    if args.output:
        # 确保输出目录存在
        out_dir = os.path.dirname(args.output)
        if out_dir:  # 如果有目录部分，则创建（exist_ok=True 避免已存在报错）
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            for tag in sorted_tags:
                f.write(tag + '\n')
        print(f"结果已保存至 {args.output}")
    else:
        for tag in sorted_tags:
            print(tag)

if __name__ == '__main__':
    main()