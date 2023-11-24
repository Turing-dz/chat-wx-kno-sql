from langchain import SQLDatabase, SQLDatabaseChain
from langchain.prompts import PromptTemplate
import pymysql
import re
sql_question_to_answer="""数据库查询语句是：{first_format}\n数据库查询结果是：{second_format}\n请根据上述查询过程进行回答，回答的内容必须简单明了，必须在30个字以内：{question}"""
# tableinfo="""你是一个SQL专家，现在给你提供一个数据库表单的提示信息。
# #数据库表单的提示信息包括：
# #{
# #CREATE TABLE 产品表 (
# #    产品ID INT PRIMARY KEY,
# #    产品名称 NVARCHAR(100),
# #   产品描述 NVARCHAR(MAX),
# #    价格 DECIMAL(10, 2),
# #    库存数量 INT,
# #    发布日期 DATE,
# #    制造商 NVARCHAR(50),
# #    重量 DECIMAL(8, 2),
# #    颜色 NVARCHAR(20),
# #    尺寸 NVARCHAR(10),
# #    品牌 NVARCHAR(50),
# #    折扣 DECIMAL(5, 2),
# #    评分 DECIMAL(3, 2)
# #);
# #
# #/*
# #3 rows from 产品表 table:
# #产品ID, 产品名称, 产品描述, 价格, 库存数量, 发布日期, 制造商, 重量, 颜色, 尺寸, 品牌, 折扣, 评分
# #1 '商品1'  '这是商品1的描述'  99.99  100  '2023-01-01'  '制造商A'  2.5  '红色'  '大号'  '品牌X'  0.1  4.5 
# #2 '商品2'  '这是商品2的描述'  149.99  50  '2023-02-01'  '制造商B'  3.0  '蓝色'  '中号'  '品牌Y'  0.2  4.2 
# #3 '商品3'  '这是商品3的描述'  199.99  75  '2023-03-01'  '制造商C'  2.8  '绿色'  '小号'  '品牌Z'  0.05  4.8 
# #*/
# #}
# 请根据上述#数据库表单的提示信息，针对"用户问题"，创建一个语法正确的MySQL查询语句，使用LIMIT子句查询最多3个结果，必须将查询语句中的字段使用反引号（`）包括起来，必须使用"数据库表单的提示信息"中可见的列名创建MySQL查询语句，查询语句不能出现不存在的列名。请按以下#输出示例进行输出：
# #输出示例
# #用户问题：商品1的库存数量是什么？
# #MySQL查询语句：SELECT 库存数量 FROM 产品表 WHERE 产品名称 = '商品1';
# #输出示例
# #用户问题：商品3的颜色是什么？
# #MySQL查询语句：SELECT 颜色 FROM 产品表  WHERE 产品名称='商品1';

# 现在我们开始：
# 用户问题:{question}
# MySQL查询语句："""
