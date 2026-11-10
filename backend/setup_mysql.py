"""Prepara o MySQL local para a Cantina em Dia (uma vez por computador).

    .venv\\Scripts\\python.exe backend\\setup_mysql.py

Pede a senha do root do MySQL (ou lê MYSQL_ROOT_PASSWORD), cria os bancos
cantina_em_dia e cantina_em_dia_test e o usuário "cantina" com senha aleatória,
com acesso só a esses bancos, e grava a conexão no .env. A senha do root não é guardada.
"""
import getpass
import os
import secrets
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
DATABASES = ['cantina_em_dia', 'cantina_em_dia_test']
HOSTS = ['localhost', '127.0.0.1', '::1']


def main():
    port = int(os.environ.get('MYSQL_PORT', '3306'))
    root_password = os.environ.get('MYSQL_ROOT_PASSWORD') or getpass.getpass('Senha do root do MySQL: ')
    password = secrets.token_urlsafe(24)
    connection = pymysql.connect(host='127.0.0.1', port=port, user='root', password=root_password, connect_timeout=5)
    with connection, connection.cursor() as cursor:
        for name in DATABASES:
            cursor.execute(f'CREATE DATABASE IF NOT EXISTS {name} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci')
        for host in HOSTS:
            cursor.execute('CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s', ('cantina', host, password))
            cursor.execute('ALTER USER %s@%s IDENTIFIED BY %s', ('cantina', host, password))
            for name in DATABASES:
                cursor.execute(f'GRANT ALL PRIVILEGES ON {name}.* TO %s@%s', ('cantina', host))
    env = ROOT / '.env'
    previous = {}
    if env.exists():
        text = env.read_text(encoding='utf-8')
        (ROOT / '.env.anterior').write_text(text, encoding='utf-8')
        previous = dict(line.split('=', 1) for line in text.splitlines() if '=' in line and not line.startswith('#'))
    env.write_text('\n'.join([
        f'DATABASE_URL=mysql+pymysql://cantina:{password}@127.0.0.1:{port}/cantina_em_dia',
        f"API_PORT={previous.get('API_PORT', '8000')}",
        f"WEB_PORT={previous.get('WEB_PORT', '5173')}",
        f"CANTINA_AUTO_BACKUP={previous.get('CANTINA_AUTO_BACKUP', '1')}", '',
    ]), encoding='utf-8')
    print('MySQL pronto: bancos cantina_em_dia e cantina_em_dia_test e usuário cantina criados. Conexão gravada no .env.')


if __name__ == '__main__':
    main()
