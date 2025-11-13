"""Gerenciamento de conexão com MySQL usando connection pooling."""

import mysql.connector
from mysql.connector import pooling, Error
from contextlib import contextmanager
from typing import Generator
from app.config import settings


# Pool de conexões global
connection_pool = None


def init_connection_pool():
    """Inicializa o pool de conexões com o MySQL."""
    global connection_pool

    try:
        print(f"🔄 Conectando ao MySQL em {settings.DB_HOST}:{settings.DB_PORT}...")
        connection_pool = pooling.MySQLConnectionPool(
            pool_name="airbnb_pool",
            pool_size=5,
            pool_reset_session=True,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            # Timeouts para evitar travamentos
            connection_timeout=5,  # Timeout de conexão (5 segundos)
            connect_timeout=5,
            autocommit=False,
        )
        print("✅ Pool de conexões MySQL inicializado com sucesso!")
    except Error as e:
        print(f"❌ Erro ao inicializar pool de conexões: {e}")
        raise


@contextmanager
def get_db_connection() -> Generator:
    """
    Context manager para obter uma conexão do pool.

    Uso:
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM table")
            results = cursor.fetchall()
    """
    connection = None
    try:
        connection = connection_pool.get_connection()
        yield connection
    except Error as e:
        print(f"❌ Erro ao obter conexão: {e}")
        raise
    finally:
        if connection and connection.is_connected():
            connection.close()


def execute_query(
    query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = True
):
    """
    Executa uma query SELECT e retorna os resultados.

    Args:
        query: Query SQL a ser executada
        params: Parâmetros para a query (prepared statement)
        fetch_one: Se True, retorna apenas um resultado
        fetch_all: Se True, retorna todos os resultados

    Returns:
        Lista de dicionários com os resultados ou None em caso de erro
    """
    if connection_pool is None:
        print("❌ Pool de conexões não foi inicializado!")
        raise Exception("Database connection pool not initialized")

    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True, buffered=True)
        try:
            # Definir timeout de 5 segundos para a query
            cursor.execute("SET SESSION MAX_EXECUTION_TIME=30000")
            cursor.execute(query, params or ())

            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return None
        except Error as e:
            print(f"❌ Erro ao executar query: {e}")
            print(f"❌ Query: {query[:200]}...")
            raise
        finally:
            cursor.close()


def execute_insert_update(query: str, params: tuple = None):
    """
    Executa uma query INSERT/UPDATE/DELETE.

    Args:
        query: Query SQL a ser executada
        params: Parâmetros para a query

    Returns:
        ID do último registro inserido (para INSERT) ou número de linhas afetadas
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.lastrowid or cursor.rowcount
        except Error as e:
            conn.rollback()
            print(f"❌ Erro ao executar INSERT/UPDATE: {e}")
            raise
        finally:
            cursor.close()


def close_connection_pool():
    """Fecha o pool de conexões (chamado ao encerrar a aplicação)."""
    global connection_pool
    if connection_pool:
        # mysql-connector-python não tem um método direto para fechar o pool
        # As conexões serão fechadas automaticamente quando o programa terminar
        print("✅ Pool de conexões MySQL encerrado.")
