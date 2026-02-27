from dotenv import load_dotenv
import os
load_dotenv()

class DatabaseConfig:
    DB_HOST = os.getenv('DB_HOST')
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')


    def validate():
        if not DatabaseConfig.DB_HOST:
            raise ValueError("DB_HOST is not set in environment variables.")
        if not DatabaseConfig.DB_NAME:
            raise ValueError("DB_NAME is not set in environment variables.")
        if not DatabaseConfig.DB_USER:
            raise ValueError("DB_USER is not set in environment variables.")
        if not DatabaseConfig.DB_PASSWORD:
            raise ValueError("DB_PASSWORD is not set in environment variables.")