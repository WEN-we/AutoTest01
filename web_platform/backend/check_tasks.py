"""检查数据库中的测试任务"""
import pymysql

conn = pymysql.connect(
    host='localhost',
    user='root',
    password=os.getenv("DB_PASSWORD", ""),
    database='test_auto'
)

cursor = conn.cursor()
cursor.execute('SELECT id, name, test_type, test_path, test_scene FROM test_task')

print('数据库中的测试任务:')
print('-' * 80)
for row in cursor.fetchall():
    print(f"ID: {row[0]}")
    print(f"  名称: {row[1]}")
    print(f"  类型: {row[2]}")
    print(f"  路径: {row[3]}")
    print(f"  场景: {row[4]}")
    print()

cursor.close()
conn.close()
