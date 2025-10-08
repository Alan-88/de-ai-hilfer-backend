#!/usr/bin/env python3
"""
测试数据库连接解析功能
"""

import urllib.parse
import os
from app.core.config import get_database_url

def test_database_url_parsing():
    """测试数据库URL解析功能"""
    
    # 获取当前的数据库URL
    db_url = get_database_url()
    print(f"当前数据库URL: {db_url}")
    
    if not db_url:
        print("❌ 数据库URL未设置")
        return False
    
    try:
        # 解析数据库URL
        parsed_url = urllib.parse.urlparse(db_url)
        
        print(f"✅ URL解析成功:")
        print(f"  - 主机: {parsed_url.hostname}")
        print(f"  - 端口: {parsed_url.port or 5432}")
        print(f"  - 用户名: {parsed_url.username}")
        print(f"  - 数据库名: {parsed_url.path.lstrip('/')}")
        print(f"  - 密码: {'已设置' if parsed_url.password else '未设置'}")
        
        # 构建pg_dump命令参数（模拟export_database_service的逻辑）
        command = [
            "pg_dump",
            "--clean",
            "--if-exists",
            "--no-password",
            "--host", parsed_url.hostname,
            "--port", str(parsed_url.port or 5432),
            "--username", parsed_url.username,
            "--dbname", parsed_url.path.lstrip('/'),
            "-f", "/tmp/test_backup.sql",
        ]
        
        print(f"✅ pg_dump命令构建成功:")
        print(f"  命令: {' '.join(command)}")
        
        # 检查环境变量设置
        env = os.environ.copy()
        if parsed_url.password:
            env["PGPASSWORD"] = parsed_url.password
            print(f"✅ PGPASSWORD环境变量已设置")
        
        return True
        
    except Exception as e:
        print(f"❌ URL解析失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== 数据库连接解析测试 ===")
    success = test_database_url_parsing()
    
    if success:
        print("\n✅ 测试通过！数据库备份功能应该可以正常工作。")
    else:
        print("\n❌ 测试失败！请检查数据库配置。")
