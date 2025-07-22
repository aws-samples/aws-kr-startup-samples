#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import boto3
import pymysql
import random
import datetime
import time
import os
import logging

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def init_mysql(connection):
    """MySQL 데이터베이스 및 테이블 초기화"""
    with connection.cursor() as cursor:
        # rds 데이터베이스 생성 (존재하지 않으면)
        cursor.execute("CREATE DATABASE IF NOT EXISTS rds")
        cursor.execute("USE rds")
        
        # CloudFormation 스키마와 동일한 테이블 생성
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS store_sales (
            salesid INT,
            listid INT,
            sellerid INT,
            buyerid INT,
            eventid INT,
            dateid SMALLINT,
            qtysold SMALLINT,
            pricepaid DECIMAL(8, 2),
            commission DECIMAL(8, 2),
            saletime TIMESTAMP
        )
        """
        cursor.execute(create_table_sql)
        connection.commit()

def generate_random_sales_data():
    """CloudFormation 스키마에 맞는 랜덤 판매 데이터 생성"""
    return {
        'salesid': random.randint(1, 100000),
        'listid': random.randint(1, 10000),
        'sellerid': random.randint(1, 5000),
        'buyerid': random.randint(1, 10000),
        'eventid': random.randint(1, 1000),
        'dateid': random.randint(1800, 2500),  # 날짜 ID 범위
        'qtysold': random.randint(1, 8),
        'pricepaid': round(random.uniform(10.0, 1000.0), 2),
        'commission': round(random.uniform(1.0, 100.0), 2)
    }

def insert_to_mysql(connection, data):
    """MySQL에 데이터 삽입"""
    with connection.cursor() as cursor:
        insert_sql = """
        INSERT INTO rds.store_sales VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
        """
        
        cursor.execute(insert_sql, (
            data['salesid'],
            data['listid'],
            data['sellerid'],
            data['buyerid'],
            data['eventid'],
            data['dateid'],
            data['qtysold'],
            data['pricepaid'],
            data['commission']
        ))
        connection.commit()

def lambda_handler(event, context):
    """Sales data generator Lambda function"""
    
    try:
        # 환경 변수에서 설정 읽기
        host = os.environ.get('HOST')
        database = os.environ.get('DATABASE', 'mysql')
        secret_arn = os.environ.get('SECRET_ARN')
        
        logger.info(f"Connecting to database: {host}")
        
        # Secrets Manager에서 DB 자격증명 가져오기
        secrets_client = boto3.client('secretsmanager')
        secret_response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(secret_response['SecretString'])
        
        username = secret['username']
        password = secret['password']
        
        # MySQL 연결
        connection = pymysql.connect(
            host=host,
            user=username,
            password=password,
            charset='utf8mb4'
        )
        
        # 데이터베이스 및 테이블 초기화
        init_mysql(connection)
        
        # 50초 동안 랜덤 데이터 생성 및 삽입 (CloudFormation 방식과 동일)
        start_time = time.time()
        records_inserted = 0
        
        while time.time() - start_time < 50:
            # 랜덤 판매 데이터 생성
            sales_data = generate_random_sales_data()
            
            # MySQL에 삽입
            insert_to_mysql(connection, sales_data)
            records_inserted += 1
            
            # 약간의 지연 (너무 빠른 삽입 방지)
            time.sleep(0.1)
        
        connection.close()
        logger.info(f"Successfully inserted {records_inserted} sales records")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully generated {records_inserted} sales records',
                'records_inserted': records_inserted
            })
        }
        
    except Exception as e:
        logger.error(f"Error generating sales data: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
