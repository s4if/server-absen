import os
from dotenv import load_dotenv
load_dotenv() 

# Load environment variables from .env file
class Config:
    pg_user = os.getenv('POSTGRES_USER')
    pg_password = os.getenv('POSTGRES_PASSWORD')
    pg_db = os.getenv('POSTGRES_DB')
    pg_port = os.getenv('POSTGRES_PORT', '5432')
    if pg_user and pg_password and pg_db:
        SQLALCHEMY_DATABASE_URI = f'postgresql://{pg_user}:{pg_password}@localhost:{pg_port}/{pg_db}'
    else:
        exit('Please set the environment variables POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB')
        #SQLALCHEMY_DATABASE_URI = 'sqlite:///attendance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change-in-production')
