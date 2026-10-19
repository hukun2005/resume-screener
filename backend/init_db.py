"""独立初始化脚本：单独运行即可建库建表并写入示例数据"""
from db import init_db

if __name__ == "__main__":
    init_db()
    print("数据库初始化完成：resume_screener 库、users/candidates/recommendations 表、示例数据均已就绪")