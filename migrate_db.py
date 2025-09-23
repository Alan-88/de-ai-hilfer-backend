import os
import sqlite3
import sqlalchemy
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.sql import text # 1. 导入 text 用于执行原生SQL

# --- 配置 ---
LOCAL_SQLITE_DB_PATH = "word_entries.db"
CLOUD_POSTGRES_URL = "postgresql://neondb_owner:npg_RNtUcf8Td0vb@ep-fragrant-bar-a1g0ncrm-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
# -------------------------------------------------------------

Base = declarative_base()

# --- 1. 数据模型定义 (保持不变) ---
class KnowledgeEntry(Base):
    __tablename__ = 'knowledge_entries'
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(String, index=True, nullable=False, unique=True)
    entry_type = Column(String(50), nullable=False, default='WORD')
    analysis_markdown = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=True)

class EntryAlias(Base):
    __tablename__ = 'entry_aliases'
    id = Column(Integer, primary_key=True, index=True)
    alias_text = Column(String, index=True, nullable=False, unique=True)
    entry_id = Column(Integer, ForeignKey('knowledge_entries.id'), nullable=False)

class FollowUp(Base):
    __tablename__ = 'follow_ups'
    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey('knowledge_entries.id'), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=True)


def migrate_data():
    print("--- 开始数据迁移 ---")

    # --- 1. 连接并读取 SQLite 数据 (保持不变) ---
    if not os.path.exists(LOCAL_SQLITE_DB_PATH):
        print(f"[错误] 未找到本地数据库文件: {LOCAL_SQLITE_DB_PATH}")
        return

    print("1/5: 正在连接到本地 SQLite 数据库并读取所有数据...")
    conn = sqlite3.connect(LOCAL_SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    entries = cursor.execute("SELECT * FROM knowledge_entries").fetchall()
    aliases = cursor.execute("SELECT * FROM entry_aliases").fetchall()
    follow_ups = cursor.execute("SELECT * FROM follow_ups").fetchall()
    conn.close()
    print(f"-> 成功读取 {len(entries)} 条词条, {len(aliases)} 条别名, {len(follow_ups)} 条追问。")

    # --- 2. 连接到云端 PostgreSQL 并创建表结构 (保持不变) ---
    if "user:password" in CLOUD_POSTGRES_URL:
        print("[警告] 请确保你已经将 CLOUD_POSTGRES_URL 替换为真实的连接字符串！")
        return

    print("2/5: 正在连接到云端 PostgreSQL 数据库并重建表结构...")
    pg_engine = create_engine(CLOUD_POSTGRES_URL)
    Base.metadata.drop_all(pg_engine) 
    Base.metadata.create_all(pg_engine) 
    Session = sessionmaker(bind=pg_engine)
    pg_session = Session()

    try:
        # --- 3. 迁移核心词条 (保持不变) ---
        print("3/5: 正在迁移核心词条...")
        if entries:
            pg_session.bulk_insert_mappings(KnowledgeEntry, [dict(row) for row in entries])
            pg_session.commit()
            print(f"-> 成功迁移 {len(entries)} 条核心词条。")
        else:
            print("-> 无核心词条数据可迁移。")

        # --- 4. 迁移别名和追问 (保持不变) ---
        print("4/5: 正在迁移别名和追问...")
        valid_entry_ids = {entry['id'] for entry in entries}
        
        cleaned_aliases = [dict(row) for row in aliases if row['entry_id'] in valid_entry_ids]
        if len(aliases) != len(cleaned_aliases):
             print(f"-> [清洗] 已自动忽略 {len(aliases) - len(cleaned_aliases)} 条无效别名。")
        if cleaned_aliases:
            pg_session.bulk_insert_mappings(EntryAlias, cleaned_aliases)
        
        cleaned_follow_ups = [dict(row) for row in follow_ups if row['entry_id'] in valid_entry_ids]
        if len(follow_ups) != len(cleaned_follow_ups):
             print(f"-> [清洗] 已自动忽略 {len(follow_ups) - len(cleaned_follow_ups)} 条无效追问。")
        if cleaned_follow_ups:
            pg_session.bulk_insert_mappings(FollowUp, cleaned_follow_ups)

        pg_session.commit()
        print(f"-> 成功迁移 {len(cleaned_aliases)} 条别名和 {len(cleaned_follow_ups)} 条追问。")

        # --- 5. 【关键修复】校准序列 (Calibrate Sequences) ---
        print("5/5: 正在校准所有主键序列...")
        with pg_engine.connect() as connection:
            # 遍历所有模型/表，为它们的主键序列校准
            for table in Base.metadata.sorted_tables:
                table_name = table.name
                # PostgreSQL 默认的序列命名规则是 "表名_主键列名_seq"
                pk_column_name = table.primary_key.columns.values()[0].name
                sequence_name = f"{table_name}_{pk_column_name}_seq"
                
                # 使用原生SQL来更新序列的计数值
                # 我们找到表中当前最大的ID，然后告诉序列下一个ID应该是这个最大值+1
                sql = text(f"SELECT setval('{sequence_name}', COALESCE((SELECT MAX({pk_column_name}) FROM {table_name}), 1))")
                connection.execute(sql)
                print(f"-> 序列 '{sequence_name}' 已校准。")
            connection.commit()

    except Exception as e:
        print(f"[错误] 写入数据或校准时发生错误: {e}")
        pg_session.rollback()
    finally:
        pg_session.close()

    print("--- 数据迁移完成！数据库已准备就绪。 ---")

if __name__ == "__main__":
    migrate_data()