#!/usr/local/bin/python
# Connect to MariaDB Platform
import mysql.connector #mariadb

try:
	#連線DB
	conn = mysql.connector.connect(
		user="root",
		password="",
		host="localhost",
		port=3306,
		database="test"
	)
	#建立執行SQL指令用之cursor, 設定傳回dictionary型態的查詢結果 [{'欄位名':值, ...}, ...]
	cursor=conn.cursor(dictionary=True)
except mysql.connector.Error as e: # mariadb.Error as e:
	print(e)
	print("Error connecting to DB")
	exit(1)


def add(data):
	sql="insert into 表格 (欄位,...) VALUES (%s,%s,...)"
	#param=('值',...)
	cursor.execute(sql,param)
	conn.commit()
	return
	
def delete(id):
	sql="delete from 表格 where 條件"
	cur.execute(sql,(id,))
	conn.commit()
	return

def update(id,data):
	sql="update 表格 set 欄位=值,... where 條件"
	#param=('值',...)
	cursor.execute(sql,param)
	conn.commit()
	return
	
def getList():
	sql="select 欄位,... from 表格 where 條件;"
	#param=('值',...)
	cursor.execute(sql,param)
	return cursor.fetchall()
