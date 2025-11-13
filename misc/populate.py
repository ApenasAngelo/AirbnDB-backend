#!/usr/bin/env python3
"""
Script para importar dados de 3 arquivos CSV para o banco de dados AirbnbRJ.

Importa dados de:
  1. listings.csv (Anfitriao, Propriedade, Amenidade)
  2. calendar.csv (Calendario)
  3. reviews.csv (Usuario, Avaliacao)

Uso:
    python populate.py <listings.csv> <calendar.csv> <reviews.csv>

Exemplo:
    python populate.py listings_cleaned.csv calendar_cleaned.csv reviews.csv
    python populate.py ../csv/listings.csv ../csv/calendar.csv ../csv/reviews.csv
"""

import csv
import sys
import os
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv


# Carregar variáveis de ambiente
load_dotenv()


# ============================================================================
# CONFIGURAÇÕES DO BANCO DE DADOS
# ============================================================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "airbnb"),
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
}


# ============================================================================
# ANÁLISE E MAPEAMENTO DOS CSVs
# ============================================================================
"""
═══════════════════════════════════════════════════════════════════════════
ARQUIVO 1: listings.csv (25 colunas após limpeza)
═══════════════════════════════════════════════════════════════════════════

ANFITRIAO (8 colunas):
  host_id                       → Anfitriao.id (BIGINT)
  host_name                     → Anfitriao.nome (VARCHAR(100))
  host_url                      → Anfitriao.url (VARCHAR(255))
  host_since                    → Anfitriao.data_ingresso (DATE)
  host_about                    → Anfitriao.descricao (TEXT)
  host_is_superhost             → Anfitriao.superhost (BOOLEAN: t/f)
  host_identity_verified        → Anfitriao.verificado (BOOLEAN: t/f)
  host_location                 → Anfitriao.localizacao (VARCHAR(100))

PROPRIEDADE (17 colunas):
  id                            → Propriedade.id (BIGINT)
  name                          → Propriedade.nome (VARCHAR(255))
  property_type                 → Propriedade.tipo (VARCHAR(100))
  accommodates                  → Propriedade.capacidade (INT)
  neighbourhood_cleansed        → Propriedade.bairro (VARCHAR(100))
  bedrooms                      → Propriedade.quartos (INT, pode ser NULL)
  bathrooms                     → Propriedade.banheiros (DECIMAL(4,2), se NULL → 0)
  beds                          → Propriedade.camas (INT, pode ser NULL)
  description                   → Propriedade.descricao (TEXT)
  listing_url                   → Propriedade.url (VARCHAR(255))
  review_scores_rating          → Propriedade.nota (DECIMAL(2,1), dividir por 20)
  price                         → Propriedade.preco (DECIMAL(10,2), limpar "$" e ",")
  number_of_reviews             → Propriedade.numero_avaliacoes (INT)
  room_type                     → Propriedade.tipo_quarto (VARCHAR(30))
  latitude                      → Propriedade.latitude (DECIMAL(9,6))
  longitude                     → Propriedade.longitude (DECIMAL(9,6))
  host_id (FK)                  → Propriedade.id_anfitriao (BIGINT)

AMENIDADE (1 coluna → parsing para múltiplas linhas):
  amenities                     → JSON array: ["Wifi", "Kitchen", ...]
                                → Amenidade.nome (VARCHAR(100))
                                → Amenidade.id_propriedade (FK)

═══════════════════════════════════════════════════════════════════════════
ARQUIVO 2: calendar.csv (3 colunas após limpeza)
═══════════════════════════════════════════════════════════════════════════

CALENDARIO:
  listing_id                    → Calendario.id_propriedade (FK)
  date                          → Calendario.data (DATE: YYYY-MM-DD)
  available                     → Calendario.disponivel (BOOLEAN: t/f)

═══════════════════════════════════════════════════════════════════════════
ARQUIVO 3: reviews.csv (6 colunas)
═══════════════════════════════════════════════════════════════════════════

USUARIO:
  reviewer_id                   → Usuario.id (BIGINT)
  reviewer_name                 → Usuario.nome (VARCHAR(100))

AVALIACAO:
  id                            → Avaliacao.id (BIGINT)
  date                          → Avaliacao.data (DATE)
  comments                      → Avaliacao.comentario (TEXT)
  reviewer_id (FK)              → Avaliacao.id_usuario (BIGINT)
  listing_id (FK)               → Avaliacao.id_propriedade (BIGINT)

═══════════════════════════════════════════════════════════════════════════
TRANSFORMAÇÕES NECESSÁRIAS:
═══════════════════════════════════════════════════════════════════════════
✓ price: "$1,234.00" → 1234.00 (remover "$" e ",")
✓ review_scores_rating: 4.8 (escala 0-5) OU 96 (escala 0-100) → dividir por 20 se > 5
✓ bathrooms: NULL → 0
✓ host_is_superhost / host_identity_verified: "t" → True, "f" → False
✓ available: "t" → True, "f" → False
✓ amenities: '["Wifi", "Kitchen"]' → parse JSON e inserir linhas separadas
✓ bedrooms/beds/quartos: NULL → 0
"""


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================


def connect_db():
    """Conecta ao banco de dados MySQL."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print(f"✅ Conectado ao MySQL - Banco: {DB_CONFIG['database']}")
            return connection
    except Error as e:
        print(f"❌ Erro ao conectar ao MySQL: {e}")
        sys.exit(1)


def parse_boolean(value: str) -> bool:
    """Converte string boolean do CSV (t/f) para Python bool."""
    if isinstance(value, bool):
        return value
    if not value or value.strip() == "":
        return False
    return value.strip().lower() in ["t", "true", "1", "yes"]


def parse_price(price_str: str, default: float = 0.0) -> Decimal:
    """
    Converte string de preço do CSV para Decimal.
    Remove "$", "," e espaços.
    Exemplo: "$1,234.00" → 1234.00
    """
    if not price_str or price_str.strip() == "":
        return Decimal(str(default))
    try:
        # Remover "$", ",", e espaços
        cleaned = price_str.strip().replace("$", "").replace(",", "").replace(" ", "")
        return Decimal(cleaned)
    except:
        return Decimal(str(default))


def parse_rating(rating_str: str) -> Decimal:
    """
    Converte rating do CSV para escala 0-5.
    Se o valor for > 5, assume escala 0-100 e divide por 20.
    Exemplo: "96" → 4.8, "4.8" → 4.8
    """
    if not rating_str or rating_str.strip() == "":
        return Decimal("0.0")
    try:
        value = Decimal(rating_str.strip())
        if value > 5:
            # Escala 0-100, converter para 0-5
            value = value / 20
        # Limitar entre 0 e 5
        return min(max(value, Decimal("0.0")), Decimal("5.0"))
    except:
        return Decimal("0.0")


def parse_decimal(value: str, default: float = 0.0) -> Decimal:
    """Converte string para Decimal, retornando default se vazio ou NULL."""
    if not value or value.strip() == "" or value.strip().upper() == "NULL":
        return Decimal(str(default))
    try:
        return Decimal(value.strip())
    except:
        return Decimal(str(default))


def parse_int(value: str, default: int = 0) -> int:
    """Converte string para int, retornando default se vazio ou NULL."""
    if not value or value.strip() == "" or value.strip().upper() == "NULL":
        return default
    try:
        # Remover casas decimais se existir (ex: "2.0" → 2)
        return int(float(value.strip()))
    except:
        return default


def parse_date(date_str: str) -> Optional[str]:
    """Converte string de data para formato MySQL (YYYY-MM-DD)."""
    if not date_str or date_str.strip() == "" or date_str.strip().upper() == "NULL":
        return None
    try:
        # Tenta parsear no formato YYYY-MM-DD
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except:
        return None


def parse_amenities_json(amenities_str: str) -> List[str]:
    """
    Parse do campo amenities que está em formato JSON.
    Exemplo: '["Wifi", "Kitchen", "Air conditioning"]'
    """
    if not amenities_str or amenities_str.strip() == "":
        return []

    try:
        amenities_list = json.loads(amenities_str)
        # Limitar tamanho do nome da amenidade para 100 caracteres
        return [a[:100] for a in amenities_list if a and isinstance(a, str)]
    except:
        return []


# ============================================================================
# FUNÇÕES DE INSERÇÃO NO BANCO
# ============================================================================


def insert_host(cursor, row: Dict[str, str]) -> bool:
    """
    Insere um anfitrião no banco a partir dos dados do listings.csv.
    Retorna True se inserido, False se já existe.
    """
    host_id = parse_int(row.get("host_id", ""))
    if not host_id:
        return False

    # Verificar se o host já existe
    cursor.execute("SELECT id FROM Anfitriao WHERE id = %s", (host_id,))
    if cursor.fetchone():
        return False  # Host já existe

    # Extrair dados do CSV
    nome = (row.get("host_name", "") or "Anfitrião")[:100]
    url = row.get("host_url", "") or None
    if url:
        url = url[:255]

    data_ingresso = parse_date(row.get("host_since", ""))
    descricao = row.get("host_about", "") or None
    superhost = parse_boolean(row.get("host_is_superhost", "f"))
    verificado = parse_boolean(row.get("host_identity_verified", "f"))
    localizacao = row.get("host_location", "") or None
    if localizacao:
        localizacao = localizacao[:100]

    query = """
    INSERT INTO Anfitriao (
        id, nome, url, data_ingresso, descricao, 
        superhost, verificado, localizacao
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    cursor.execute(
        query,
        (
            host_id,
            nome,
            url,
            data_ingresso,
            descricao,
            superhost,
            verificado,
            localizacao,
        ),
    )
    return True


def insert_property(cursor, row: Dict[str, str]) -> bool:
    """
    Insere uma propriedade no banco a partir dos dados do listings.csv.
    Retorna True se inserido, False se já existe.
    """
    property_id = parse_int(row.get("id", ""))
    if not property_id:
        return False

    # Verificar se a propriedade já existe
    cursor.execute("SELECT id FROM Propriedade WHERE id = %s", (property_id,))
    if cursor.fetchone():
        return False

    # Extrair dados do CSV
    nome = (row.get("name", "") or "Sem nome")[:255]
    tipo = (row.get("property_type", "") or "Apartment")[:100]
    capacidade = parse_int(row.get("accommodates", ""), 2)
    bairro = (row.get("neighbourhood_cleansed", "") or "Desconhecido")[:100]
    quartos = parse_int(row.get("bedrooms", ""), 0)  # NULL → 0
    banheiros = parse_decimal(row.get("bathrooms", ""), 0.0)  # NULL → 0
    camas = parse_int(row.get("beds", ""), 0)  # NULL → 0
    descricao = row.get("description", "") or None
    url = row.get("listing_url", "") or None
    if url:
        url = url[:255]

    # Processar rating (pode estar em escala 0-5 ou 0-100)
    nota = parse_rating(row.get("review_scores_rating", ""))

    # Processar preço (remover "$" e ",")
    preco = parse_price(row.get("price", ""), 100.0)

    numero_avaliacoes = parse_int(row.get("number_of_reviews", ""), 0)
    tipo_quarto = (row.get("room_type", "") or "Entire home/apt")[:30]
    latitude = parse_decimal(row.get("latitude", ""), -22.9068)
    longitude = parse_decimal(row.get("longitude", ""), -43.1729)
    id_anfitriao = parse_int(row.get("host_id", ""))

    if not id_anfitriao:
        return False  # Propriedade precisa de anfitrião válido

    query = """
    INSERT INTO Propriedade (
        id, nome, tipo, capacidade, bairro, quartos, banheiros, camas,
        descricao, url, nota, preco, numero_avaliacoes, tipo_quarto,
        latitude, longitude, id_anfitriao
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s
    )
    """

    cursor.execute(
        query,
        (
            property_id,
            nome,
            tipo,
            capacidade,
            bairro,
            quartos,
            banheiros,
            camas,
            descricao,
            url,
            nota,
            preco,
            numero_avaliacoes,
            tipo_quarto,
            latitude,
            longitude,
            id_anfitriao,
        ),
    )

    return True


def insert_amenities(cursor, property_id: int, amenities_str: str) -> int:
    """
    Insere amenidades para uma propriedade a partir do JSON do CSV.
    Retorna o número de amenidades inseridas.
    """
    amenities = parse_amenities_json(amenities_str)

    if not amenities:
        return 0

    query = "INSERT IGNORE INTO Amenidade (id_propriedade, nome) VALUES (%s, %s)"

    count = 0
    for amenity in amenities:
        cursor.execute(query, (property_id, amenity))
        count += 1

    return count


def insert_calendar_entry(cursor, row: Dict[str, str]) -> bool:
    """
    Insere uma entrada de calendário a partir dos dados do calendar.csv.
    Retorna True se inserido, False se já existe ou erro.
    """
    listing_id = parse_int(row.get("listing_id", ""))
    date_str = parse_date(row.get("date", ""))
    disponivel = parse_boolean(row.get("available", "f"))

    if not listing_id or not date_str:
        return False

    query = """
    INSERT IGNORE INTO Calendario (data, disponivel, id_propriedade) 
    VALUES (%s, %s, %s)
    """

    cursor.execute(query, (date_str, disponivel, listing_id))
    return True


def insert_usuario(cursor, reviewer_id: int, reviewer_name: str) -> bool:
    """
    Insere um usuário no banco a partir dos dados do reviews.csv.
    Retorna True se inserido, False se já existe.
    """
    if not reviewer_id:
        return False

    # Verificar se o usuário já existe
    cursor.execute("SELECT id FROM Usuario WHERE id = %s", (reviewer_id,))
    if cursor.fetchone():
        return False

    nome = (reviewer_name or "Usuário")[:100]

    query = "INSERT INTO Usuario (id, nome) VALUES (%s, %s)"
    cursor.execute(query, (reviewer_id, nome))
    return True


def insert_avaliacao(cursor, row: Dict[str, str]) -> bool:
    """
    Insere uma avaliação no banco a partir dos dados do reviews.csv.
    Retorna True se inserido, False se já existe ou erro.
    """
    avaliacao_id = parse_int(row.get("id", ""))
    if not avaliacao_id:
        return False

    # Verificar se a avaliação já existe
    cursor.execute("SELECT id FROM Avaliacao WHERE id = %s", (avaliacao_id,))
    if cursor.fetchone():
        return False

    data = parse_date(row.get("date", ""))
    comentario = row.get("comments", "") or None
    id_usuario = parse_int(row.get("reviewer_id", ""))
    id_propriedade = parse_int(row.get("listing_id", ""))

    if not id_usuario or not id_propriedade:
        return False

    query = """
    INSERT INTO Avaliacao (id, data, comentario, id_usuario, id_propriedade)
    VALUES (%s, %s, %s, %s, %s)
    """

    cursor.execute(query, (avaliacao_id, data, comentario, id_usuario, id_propriedade))
    return True


# ============================================================================
# FUNÇÕES PRINCIPAIS DE IMPORTAÇÃO
# ============================================================================


def import_listings(cursor, connection, csv_path: str, stats: Dict) -> None:
    """Importa dados do arquivo listings.csv (Anfitriao, Propriedade, Amenidade)."""
    print(f"\n{'═'*70}")
    print("📂 ETAPA 1: Importando LISTINGS.CSV")
    print(f"{'═'*70}\n")
    print(f"   Arquivo: {csv_path}")

    if not os.path.exists(csv_path):
        print(f"   ❌ Arquivo não encontrado!")
        return

    with open(csv_path, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        # Passo 1: Coletar hosts únicos
        print("\n   🔍 Passo 1.1: Coletando anfitriões únicos...")
        hosts_map = {}
        listings_rows = []

        for row in reader:
            listings_rows.append(row)
            host_id = parse_int(row.get("host_id", ""))
            if host_id and host_id not in hosts_map:
                hosts_map[host_id] = row

        print(f"   ✓ {len(hosts_map)} anfitriões únicos encontrados")

        # Passo 2: Inserir hosts
        print("\n   👤 Passo 1.2: Inserindo anfitriões...")
        for host_row in hosts_map.values():
            try:
                if insert_host(cursor, host_row):
                    stats["hosts_inserted"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"   ⚠️ Erro ao inserir host: {e}")

        print(f"   ✅ {stats['hosts_inserted']} anfitriões inseridos")

        # Passo 3: Inserir propriedades e amenidades
        print("\n   🏠 Passo 1.3: Inserindo propriedades e amenidades...")
        for i, row in enumerate(listings_rows, 1):
            try:
                property_id = parse_int(row.get("id", ""))

                if insert_property(cursor, row):
                    stats["properties_inserted"] += 1

                    # Inserir amenidades
                    amenities_str = row.get("amenities", "")
                    amenities_count = insert_amenities(
                        cursor, property_id, amenities_str
                    )
                    stats["amenities_inserted"] += amenities_count

                # Commit a cada 500 linhas
                if i % 500 == 0:
                    connection.commit()
                    print(
                        f"   ⏳ Progresso: {i}/{len(listings_rows)} propriedades processadas..."
                    )

            except Exception as e:
                stats["errors"] += 1
                if stats["errors"] <= 5:  # Mostrar apenas primeiros 5 erros
                    print(f"   ⚠️ Erro na linha {i}: {e}")

        connection.commit()
        print(f"\n   ✅ {stats['properties_inserted']} propriedades inseridas")
        print(f"   ✅ {stats['amenities_inserted']} amenidades inseridas")


def import_calendar(cursor, connection, csv_path: str, stats: Dict) -> None:
    """Importa dados do arquivo calendar.csv (Calendario)."""
    print(f"\n{'═'*70}")
    print("📅 ETAPA 2: Importando CALENDAR.CSV")
    print(f"{'═'*70}\n")
    print(f"   Arquivo: {csv_path}")

    if not os.path.exists(csv_path):
        print(f"   ❌ Arquivo não encontrado!")
        return

    with open(csv_path, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        print("\n   📆 Inserindo entradas de calendário...")

        for i, row in enumerate(reader, 1):
            try:
                if insert_calendar_entry(cursor, row):
                    stats["calendar_inserted"] += 1

                # Commit a cada 5000 linhas (calendário é grande)
                if i % 5000 == 0:
                    connection.commit()
                    print(f"   ⏳ Progresso: {i} entradas processadas...")

            except Exception as e:
                stats["errors"] += 1
                if stats["errors"] <= 5:
                    print(f"   ⚠️ Erro na linha {i}: {e}")

        connection.commit()
        print(f"\n   ✅ {stats['calendar_inserted']} entradas de calendário inseridas")


def import_reviews(cursor, connection, csv_path: str, stats: Dict) -> None:
    """Importa dados do arquivo reviews.csv (Usuario, Avaliacao)."""
    print(f"\n{'═'*70}")
    print("⭐ ETAPA 3: Importando REVIEWS.CSV")
    print(f"{'═'*70}\n")
    print(f"   Arquivo: {csv_path}")

    if not os.path.exists(csv_path):
        print(f"   ❌ Arquivo não encontrado!")
        return

    with open(csv_path, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        # Passo 1: Coletar usuários únicos
        print("\n   🔍 Passo 3.1: Coletando usuários únicos...")
        usuarios_map = {}
        reviews_rows = []

        for row in reader:
            reviews_rows.append(row)
            reviewer_id = parse_int(row.get("reviewer_id", ""))
            if reviewer_id and reviewer_id not in usuarios_map:
                usuarios_map[reviewer_id] = row.get("reviewer_name", "")

        print(f"   ✓ {len(usuarios_map)} usuários únicos encontrados")

        # Passo 2: Inserir usuários
        print("\n   👥 Passo 3.2: Inserindo usuários...")
        for reviewer_id, reviewer_name in usuarios_map.items():
            try:
                if insert_usuario(cursor, reviewer_id, reviewer_name):
                    stats["usuarios_inserted"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"   ⚠️ Erro ao inserir usuário: {e}")

        print(f"   ✅ {stats['usuarios_inserted']} usuários inseridos")

        # Passo 3: Inserir avaliações
        print("\n   💬 Passo 3.3: Inserindo avaliações...")
        for i, row in enumerate(reviews_rows, 1):
            try:
                if insert_avaliacao(cursor, row):
                    stats["avaliacoes_inserted"] += 1

                # Commit a cada 1000 linhas
                if i % 1000 == 0:
                    connection.commit()
                    print(
                        f"   ⏳ Progresso: {i}/{len(reviews_rows)} avaliações processadas..."
                    )

            except Exception as e:
                stats["errors"] += 1
                if stats["errors"] <= 5:
                    print(f"   ⚠️ Erro na linha {i}: {e}")

        connection.commit()
        print(f"\n   ✅ {stats['avaliacoes_inserted']} avaliações inseridas")


def import_all_csvs(listings_path: str, calendar_path: str, reviews_path: str):
    """Importa dados dos 3 arquivos CSV para o banco de dados."""

    # Conectar ao banco
    connection = connect_db()
    cursor = connection.cursor()

    # Estatísticas
    stats = {
        "hosts_inserted": 0,
        "properties_inserted": 0,
        "amenities_inserted": 0,
        "calendar_inserted": 0,
        "usuarios_inserted": 0,
        "avaliacoes_inserted": 0,
        "errors": 0,
    }

    try:
        # Desabilitar checks temporariamente para performance
        print("\n⚙️  Configurando banco para importação em lote...")
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        cursor.execute("SET UNIQUE_CHECKS=0")
        cursor.execute("SET AUTOCOMMIT=0")

        print("✅ Configurações aplicadas\n")

        # Importar os 3 arquivos na ordem correta
        import_listings(cursor, connection, listings_path, stats)
        import_calendar(cursor, connection, calendar_path, stats)
        import_reviews(cursor, connection, reviews_path, stats)

        # Re-habilitar checks
        print(f"\n{'═'*70}")
        print("⚙️  Reabilitando verificações do banco...")
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        cursor.execute("SET UNIQUE_CHECKS=1")
        cursor.execute("SET AUTOCOMMIT=1")
        print("✅ Verificações reabilitadas")

        # Mostrar estatísticas finais
        print(f"\n{'═'*70}")
        print("📊 ESTATÍSTICAS FINAIS DA IMPORTAÇÃO")
        print(f"{'═'*70}")
        print(f"Anfitriões inseridos:         {stats['hosts_inserted']:>10,}")
        print(f"Propriedades inseridas:       {stats['properties_inserted']:>10,}")
        print(f"Amenidades inseridas:         {stats['amenities_inserted']:>10,}")
        print(f"Calendário (entradas):        {stats['calendar_inserted']:>10,}")
        print(f"Usuários inseridos:           {stats['usuarios_inserted']:>10,}")
        print(f"Avaliações inseridas:         {stats['avaliacoes_inserted']:>10,}")
        print(f"{'─'*70}")
        print(
            f"Total de inserções:           {sum(stats.values()) - stats['errors']:>10,}"
        )
        print(f"Erros encontrados:            {stats['errors']:>10,}")
        print(f"{'═'*70}")
        print("✅ Importação concluída com sucesso!\n")

    except Exception as e:
        connection.rollback()
        print(f"\n❌ Erro durante importação: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        cursor.close()
        connection.close()
        print("🔌 Conexão com o banco fechada.")


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Função principal."""
    print("=" * 70)
    print("  📊 AirbnbRJ - Script de Importação de Dados CSV")
    print("=" * 70)
    print()

    # Verificar argumentos
    if len(sys.argv) < 4:
        print("❌ Erro: Arquivos CSV não fornecidos")
        print()
        print("Uso:")
        print("  python populate.py <listings.csv> <calendar.csv> <reviews.csv>")
        print()
        print("Exemplo:")
        print(
            "  python populate.py listings_cleaned.csv calendar_cleaned.csv reviews.csv"
        )
        print(
            "  python populate.py ../csv/listings.csv ../csv/calendar.csv ../csv/reviews.csv"
        )
        print()
        print("Ordem dos arquivos:")
        print("  1. listings.csv  - Dados de anfitriões, propriedades e amenidades")
        print("  2. calendar.csv  - Dados de disponibilidade do calendário")
        print("  3. reviews.csv   - Dados de usuários e avaliações")
        sys.exit(1)

    listings_path = sys.argv[1]
    calendar_path = sys.argv[2]
    reviews_path = sys.argv[3]

    # Verificar se arquivos existem
    missing_files = []
    for path in [listings_path, calendar_path, reviews_path]:
        if not os.path.exists(path):
            missing_files.append(path)

    if missing_files:
        print("❌ Arquivos não encontrados:")
        for f in missing_files:
            print(f"   • {f}")
        sys.exit(1)

    # Confirmar importação
    print(f"📁 Arquivos:")
    print(f"   1. Listings:  {listings_path}")
    print(f"   2. Calendar:  {calendar_path}")
    print(f"   3. Reviews:   {reviews_path}")
    print()
    print(f"🗄️  Banco de Dados:")
    print(f"   Host:     {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"   Database: {DB_CONFIG['database']}")
    print(f"   User:     {DB_CONFIG['user']}")
    print()

    response = input("⚠️  Deseja continuar com a importação? (s/N): ")
    if response.lower() not in ["s", "sim", "y", "yes"]:
        print("❌ Importação cancelada pelo usuário")
        sys.exit(0)

    print()

    # Executar importação
    import_all_csvs(listings_path, calendar_path, reviews_path)


if __name__ == "__main__":
    main()
