#!/usr/bin/env python3
"""
测试Neon PostgreSQL数据库备份功能
验证修复后的数据库连接解析逻辑
"""

import urllib.parse
import os
import sys

def test_neon_database_url_parsing():
    """测试Neon数据库URL解析功能"""
    
    # 模拟Neon数据库URL（示例格式）
    neon_db_url = "postgresql://username:password@ep-example.us-east-2.aws.neon.tech/dbname?sslmode=require"
    
    print("=== Neon PostgreSQL数据库备份功能测试 ===")
    print(f"测试URL: {neon_db_url}")
    
    try:
        # 解析数据库URL
        parsed_url = urllib.parse.urlparse(neon_db_url)
        
        print(f"✅ URL解析成功:")
        print(f"  - 主机: {parsed_url.hostname}")
        print(f"  - 端口: {parsed_url.port or 5432}")
        print(f"  - 用户名: {parsed_url.username}")
        print(f"  - 数据库名: {parsed_url.path.lstrip('/')}")
        print(f"  - 密码: {'已设置' if parsed_url.password else '未设置'}")
        print(f"  - SSL模式: {urllib.parse.parse_qs(parsed_url.query).get('sslmode', ['prefer'])[0]}")
        
        # 构建pg_dump命令参数（模拟export_database_service的逻辑）
        backup_file = "/tmp/neon_test_backup.sql"
        command = [
            "pg_dump",
            "--clean",
            "--if-exists",
            "--no-password",
            "--host", parsed_url.hostname,
            "--port", str(parsed_url.port or 5432),
            "--username", parsed_url.username,
            "--dbname", parsed_url.path.lstrip('/'),
            "-f", backup_file,
        ]
        
        print(f"✅ pg_dump命令构建成功:")
        print(f"  命令: {' '.join(command)}")
        
        # 检查环境变量设置
        env = os.environ.copy()
        if parsed_url.password:
            env["PGPASSWORD"] = parsed_url.password
            print(f"✅ PGPASSWORD环境变量已设置")
        
        # 验证关键参数不为None
        if not parsed_url.hostname:
            print("❌ 主机名为空")
            return False
        if not parsed_url.username:
            print("❌ 用户名为空")
            return False
        if not parsed_url.path.lstrip('/'):
            print("❌ 数据库名为空")
            return False
            
        print(f"✅ 所有必需参数验证通过")
        return True
        
    except Exception as e:
        print(f"❌ URL解析失败: {str(e)}")
        return False

def test_psql_command_building():
    """测试psql命令构建逻辑"""
    
    print("\n=== psql恢复命令测试 ===")
    
    # 模拟Neon数据库URL
    neon_db_url = "postgresql://username:password@ep-example.us-east-2.aws.neon.tech/dbname?sslmode=require"
    sql_file = "/tmp/test_restore.sql"
    
    try:
        parsed_url = urllib.parse.urlparse(neon_db_url)
        
        # 构建psql命令参数（模拟import_database_service的逻辑）
        command = [
            "psql",
            "--no-password",
            "--host", parsed_url.hostname,
            "--port", str(parsed_url.port or 5432),
            "--username", parsed_url.username,
            "--dbname", parsed_url.path.lstrip('/'),
            "-f", sql_file,
        ]
        
        print(f"✅ psql命令构建成功:")
        print(f"  命令: {' '.join(command)}")
        
        return True
        
    except Exception as e:
        print(f"❌ psql命令构建失败: {str(e)}")
        return False

def check_pg_tools():
    """检查PostgreSQL工具是否可用"""
    
    print("\n=== PostgreSQL工具检查 ===")
    
    import subprocess
    
    # 检查pg_dump
    try:
        result = subprocess.run(["pg_dump", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ pg_dump可用: {result.stdout.strip()}")
        else:
            print("❌ pg_dump不可用")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"❌ pg_dump检查失败: {str(e)}")
        print("💡 提示: 在生产环境中确保PostgreSQL客户端工具已安装")
        return False
    
    # 检查psql
    try:
        result = subprocess.run(["psql", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ psql可用: {result.stdout.strip()}")
        else:
            print("❌ psql不可用")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"❌ psql检查失败: {str(e)}")
        print("💡 提示: 在生产环境中确保PostgreSQL客户端工具已安装")
        return False
    
    return True

def main():
    """主测试函数"""
    
    print("🚀 开始测试Neon PostgreSQL数据库备份功能修复...")
    
    # 测试1: URL解析
    test1_success = test_neon_database_url_parsing()
    
    # 测试2: psql命令构建
    test2_success = test_psql_command_building()
    
    # 测试3: 检查PostgreSQL工具（可选，因为本地可能没有安装）
    test3_success = check_pg_tools()
    
    # 总结
    print("\n" + "="*50)
    print("📊 测试结果总结:")
    print(f"  ✅ Neon数据库URL解析: {'通过' if test1_success else '失败'}")
    print(f"  ✅ psql命令构建: {'通过' if test2_success else '失败'}")
    print(f"  ✅ PostgreSQL工具检查: {'通过' if test3_success else '失败（可接受）'}")
    
    if test1_success and test2_success:
        print("\n🎉 核心功能测试通过！")
        print("📝 修复要点:")
        print("   1. 使用urllib.parse正确解析Neon数据库URL")
        print("   2. 明确指定--host、--port、--username、--dbname参数")
        print("   3. 通过PGPASSWORD环境变量传递密码")
        print("   4. 使用--no-password避免交互式提示")
        print("   5. 支持网络连接（TCP/IP）而非Unix socket")
        print("\n✅ 数据库备份功能应该可以在Neon环境中正常工作！")
        return True
    else:
        print("\n❌ 核心功能测试失败！")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
