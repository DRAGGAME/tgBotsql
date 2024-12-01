import os
from dotenv import load_dotenv

load_dotenv()
PG_user = str(os.getenv('PG_user'))
PG_password = str(os.getenv('PG_password'))
ip = str(os.getenv('ip'))
DATABASE = str(os.getenv('DATABASE'))

POSTGRES_URI = f'postgresql://{PG_user}:{PG_password}@{ip}/{DATABASE}'
