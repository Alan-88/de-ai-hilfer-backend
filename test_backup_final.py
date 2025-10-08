import asyncio
import os
from app.core.config import get_database_url
from app.api.v1.management import export_database_service

async def test_backup():
    print('测试数据库备份功能...')
    print('数据库URL:', get_database_url())
    
    try:
        backup_file = await export_database_service()
        print(f'备份成功！文件路径: {backup_file}')
        
        if os.path.exists(backup_file):
            size = os.path.getsize(backup_file)
            print(f'备份文件大小: {size} bytes')
            
            # 读取前几行内容验证
            with open(backup_file, 'r', encoding='utf-8') as f:
                first_lines = f.read(200)
                print(f'备份文件前200字符: {first_lines}')
        else:
            print('备份文件不存在')
            
    except Exception as e:
        print(f'备份失败: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_backup())
