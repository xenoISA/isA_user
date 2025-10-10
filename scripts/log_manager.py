#!/usr/bin/env python3
"""
日志管理脚本
提供日志清理、压缩、分析等功能
"""

import asyncio
import argparse
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import gzip
import shutil

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from core.log_aggregator import LogAggregator, LogMonitor, get_log_summary, search_recent_errors


async def cleanup_old_logs(log_dir: str, days_to_keep: int = 7):
    """清理旧日志文件"""
    log_path = Path(log_dir)
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    cleaned_files = []
    total_size_cleaned = 0
    
    for log_file in log_path.rglob("*.log*"):
        try:
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                file_size = log_file.stat().st_size
                log_file.unlink()
                cleaned_files.append(str(log_file))
                total_size_cleaned += file_size
        except Exception as e:
            print(f"Error cleaning {log_file}: {e}")
    
    print(f"Cleaned {len(cleaned_files)} files, freed {total_size_cleaned / 1024 / 1024:.2f} MB")
    return cleaned_files


async def compress_old_logs(log_dir: str, days_to_compress: int = 1):
    """压缩旧日志文件"""
    log_path = Path(log_dir)
    cutoff_date = datetime.now() - timedelta(days=days_to_compress)
    
    compressed_files = []
    
    for log_file in log_path.rglob("*.log"):
        try:
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_date and not str(log_file).endswith('.gz'):
                # 压缩文件
                gz_path = log_file.with_suffix(log_file.suffix + '.gz')
                
                with open(log_file, 'rb') as f_in:
                    with gzip.open(gz_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # 删除原文件
                log_file.unlink()
                compressed_files.append(str(log_file))
                
        except Exception as e:
            print(f"Error compressing {log_file}: {e}")
    
    print(f"Compressed {len(compressed_files)} files")
    return compressed_files


async def analyze_logs(log_dir: str, hours: int = 24):
    """分析日志并生成报告"""
    print(f"Analyzing logs from last {hours} hours...")
    
    # 获取摘要
    summary = await get_log_summary(log_dir, hours)
    
    print("\n=== Log Analysis Report ===")
    print(f"Total logs: {summary.get('total_logs', 0)}")
    print(f"Error count: {summary.get('error_count', 0)}")
    print(f"Warning count: {summary.get('warning_count', 0)}")
    print(f"Error rate: {summary.get('error_rate', 0):.2f}%")
    
    print(f"\nServices: {', '.join(summary.get('services', []))}")
    
    # 服务分布
    print("\n=== Service Log Distribution ===")
    distribution = summary.get('service_distribution', {})
    for service, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
        print(f"{service}: {count} logs")
    
    # 顶级错误
    print("\n=== Top Errors ===")
    top_errors = summary.get('top_errors', [])
    for i, error in enumerate(top_errors[:5], 1):
        print(f"{i}. {error.get('message', '')} (count: {error.get('count', 0)})")
    
    return summary


async def monitor_logs(log_dir: str):
    """监控日志并检查告警"""
    print("Monitoring logs for alerts...")
    
    aggregator = LogAggregator(log_dir)
    monitor = LogMonitor(aggregator)
    
    alerts = await monitor.check_alerts()
    
    if not alerts:
        print("✅ No alerts found - all services healthy")
        return
    
    print(f"\n⚠️  Found {len(alerts)} alerts:")
    
    for alert in alerts:
        severity = alert.get('severity', 'info').upper()
        alert_type = alert.get('type', 'unknown')
        message = alert.get('message', '')
        service = alert.get('service', 'global')
        
        print(f"[{severity}] {service}: {message}")
    
    return alerts


async def search_logs(log_dir: str, query: str, service: str = None, 
                     level: str = None, hours: int = 24, limit: int = 20):
    """搜索日志"""
    print(f"Searching logs for: '{query}'")
    if service:
        print(f"Service filter: {service}")
    if level:
        print(f"Level filter: {level}")
    
    aggregator = LogAggregator(log_dir)
    results = await aggregator.search_logs(query, service, level, hours, limit)
    
    print(f"\nFound {len(results)} matching log entries:")
    print("-" * 80)
    
    for result in results:
        timestamp = result.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {result.service} | {result.level} | {result.message}")
    
    return results


async def export_logs(log_dir: str, output_file: str, format: str = "json", hours: int = 24):
    """导出日志"""
    print(f"Exporting logs to {output_file} (format: {format})")
    
    aggregator = LogAggregator(log_dir)
    logs = await aggregator.collect_all_logs(hours)
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format.lower() == "json":
        with open(output_path, 'w', encoding='utf-8') as f:
            data = [aggregator.to_dict(log) for log in logs]
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    elif format.lower() == "csv":
        import csv
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            if logs:
                writer = csv.DictWriter(f, fieldnames=aggregator.to_dict(logs[0]).keys())
                writer.writeheader()
                for log in logs:
                    writer.writerow(aggregator.to_dict(log))
    
    print(f"Exported {len(logs)} log entries to {output_file}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="日志管理工具")
    parser.add_argument("--log-dir", default="logs", help="日志目录路径")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 清理命令
    cleanup_parser = subparsers.add_parser("cleanup", help="清理旧日志")
    cleanup_parser.add_argument("--days", type=int, default=7, help="保留天数")
    
    # 压缩命令
    compress_parser = subparsers.add_parser("compress", help="压缩旧日志")
    compress_parser.add_argument("--days", type=int, default=1, help="压缩天数之前的日志")
    
    # 分析命令
    analyze_parser = subparsers.add_parser("analyze", help="分析日志")
    analyze_parser.add_argument("--hours", type=int, default=24, help="分析小时数")
    
    # 监控命令
    subparsers.add_parser("monitor", help="监控日志告警")
    
    # 搜索命令
    search_parser = subparsers.add_parser("search", help="搜索日志")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument("--service", help="服务名过滤")
    search_parser.add_argument("--level", help="日志级别过滤")
    search_parser.add_argument("--hours", type=int, default=24, help="搜索小时数")
    search_parser.add_argument("--limit", type=int, default=20, help="结果限制")
    
    # 导出命令
    export_parser = subparsers.add_parser("export", help="导出日志")
    export_parser.add_argument("output", help="输出文件路径")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json", help="输出格式")
    export_parser.add_argument("--hours", type=int, default=24, help="导出小时数")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "cleanup":
            await cleanup_old_logs(args.log_dir, args.days)
        
        elif args.command == "compress":
            await compress_old_logs(args.log_dir, args.days)
        
        elif args.command == "analyze":
            await analyze_logs(args.log_dir, args.hours)
        
        elif args.command == "monitor":
            await monitor_logs(args.log_dir)
        
        elif args.command == "search":
            await search_logs(args.log_dir, args.query, args.service, 
                            args.level, args.hours, args.limit)
        
        elif args.command == "export":
            await export_logs(args.log_dir, args.output, args.format, args.hours)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())