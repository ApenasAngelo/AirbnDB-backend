"""Router para endpoints relacionados a listings/propriedades."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models.schemas import (
    Listing,
    ListingSimple,
    Amenity,
    Review,
    AvailabilityDate,
    HostProfile,
    HostProperty,
)
from app.database.connection import execute_query

router = APIRouter(prefix="/api", tags=["Listings"])


# ============================================================================
# CONSULTA 1: Buscar propriedades com filtros avançados (UNIFICADA)
# ============================================================================


@router.get("/listings/search", response_model=List[Listing])
async def search_listings(
    # Filtros de preço
    min_price: Optional[float] = Query(None, description="Preço mínimo"),
    max_price: Optional[float] = Query(None, description="Preço máximo"),
    # Filtros de bairros (multi-seleção)
    neighborhoods: Optional[str] = Query(
        None, description="Bairros separados por vírgula"
    ),
    # Filtros de qualidade
    min_rating: Optional[float] = Query(None, description="Nota mínima"),
    min_capacity: Optional[int] = Query(None, description="Capacidade mínima"),
    min_reviews: Optional[int] = Query(None, description="Número mínimo de avaliações"),
    # Filtro de superhost
    superhost_only: Optional[bool] = Query(None, description="Apenas superhosts"),
    # Filtros de disponibilidade
    check_in: Optional[str] = Query(None, description="Data check-in (YYYY-MM-DD)"),
    check_out: Optional[str] = Query(None, description="Data check-out (YYYY-MM-DD)"),
    min_available_days: Optional[int] = Query(
        None, description="Mínimo de dias disponíveis"
    ),
    # Paginação/Limites
    limit: Optional[int] = Query(100, description="Limite de resultados"),
    offset: Optional[int] = Query(0, description="Offset para paginação"),
):
    """
    Consulta SIMPLIFICADA de busca de propriedades (sem subqueries pesadas).
    """
    # Query base simplificada
    query = """
    SELECT 
        P.id AS property_id,
        P.nome AS property_name,
        P.descricao AS property_description,
        P.tipo AS property_type,
        P.capacidade,
        P.quartos AS bedrooms,
        P.camas AS beds,
        P.banheiros AS bathrooms,
        P.bairro AS neighborhood,
        P.latitude,
        P.longitude,
        P.tipo_quarto AS room_type,
        P.preco AS price,
        P.url AS listing_url,
        P.nota AS rating,
        P.numero_avaliacoes AS number_of_reviews,
        A.id AS host_id,
        A.nome AS host_name,
        A.superhost AS is_superhost,
        A.verificado AS verified,
        A.data_ingresso AS host_join_date,
        (SELECT COUNT(*) + 1
         FROM Propriedade AS P2
         WHERE P2.bairro = P.bairro
           AND (P2.nota > P.nota 
                OR (P2.nota = P.nota AND P2.numero_avaliacoes > P.numero_avaliacoes))
        ) AS neighborhood_ranking
    FROM Propriedade AS P
    INNER JOIN Anfitriao AS A ON P.id_anfitriao = A.id
    WHERE P.latitude IS NOT NULL AND P.longitude IS NOT NULL
    """

    params = []

    # Adicionar filtros dinamicamente
    if min_price is not None:
        query += " AND P.preco >= %s"
        params.append(min_price)
    if max_price is not None:
        query += " AND P.preco <= %s"
        params.append(max_price)
    if neighborhoods:
        neighborhood_list = [n.strip() for n in neighborhoods.split(",")]
        placeholders = ", ".join(["%s"] * len(neighborhood_list))
        query += f" AND P.bairro IN ({placeholders})"
        params.extend(neighborhood_list)
    if min_rating is not None:
        query += " AND P.nota >= %s"
        params.append(min_rating)
    if min_capacity is not None:
        query += " AND P.capacidade >= %s"
        params.append(min_capacity)
    if min_reviews is not None:
        query += " AND P.numero_avaliacoes >= %s"
        params.append(min_reviews)
    if superhost_only:
        query += " AND A.superhost = 1"

    query += " ORDER BY P.nota DESC, P.numero_avaliacoes DESC LIMIT %s OFFSET %s"
    params.append(limit)
    params.append(offset)

    try:
        results = execute_query(query, tuple(params))
        return results or []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar propriedades: {str(e)}"
        )


# ============================================================================
# CONSULTA 2: Obter amenidades de uma propriedade específica
# ============================================================================


@router.get("/properties/{property_id}/amenities", response_model=List[Amenity])
async def get_property_amenities(property_id: int):
    """
    Retorna todas as amenidades/comodidades de uma propriedade.
    Utilizada por: PropertyDetails (exibe as comodidades no painel de detalhes)
    """
    query = """
    SELECT 
        Am.nome AS amenity_name
    FROM Amenidade AS Am
    WHERE Am.id_propriedade = %s
    ORDER BY Am.nome
    """

    try:
        results = execute_query(query, (property_id,))
        return results or []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar amenidades: {str(e)}"
        )


# ============================================================================
# CONSULTA 6: Verificar disponibilidade de uma propriedade
# ============================================================================


@router.get(
    "/properties/{property_id}/availability", response_model=List[AvailabilityDate]
)
async def get_property_availability(property_id: int):
    """
    Retorna apenas as datas disponíveis de uma propriedade.
    Utilizada por: AvailabilityCalendar (exibe calendário de disponibilidade)
    """
    query = """
    SELECT 
        C.data AS date
    FROM Calendario AS C
    WHERE C.id_propriedade = %s
      AND C.disponivel = 1
    ORDER BY C.data
    """

    try:
        results = execute_query(query, (property_id,))
        return results or []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar disponibilidade: {str(e)}"
        )


# ============================================================================
# CONSULTA 7: Obter avaliações de uma propriedade (com paginação)
# ============================================================================


@router.get("/properties/{property_id}/reviews", response_model=List[Review])
async def get_property_reviews(
    property_id: int,
    min_year: Optional[int] = Query(None, description="Ano mínimo das avaliações"),
    offset: int = Query(0, description="Offset para paginação"),
):
    """
    Retorna avaliações de uma propriedade com dados do usuário (paginado).
    Inclui subconsulta para total de reviews do usuário.
    Utilizada por: PropertyDetails (seção de avaliações)
    """
    query = """
    SELECT 
        U.nome AS user_name,
        P.nome AS property_name,
        Av.comentario AS comment,
        Av.id AS review_id,
        Av.data AS review_date,
        U.id AS user_id,
        (SELECT COUNT(*)
         FROM Avaliacao AS Av2
         WHERE Av2.id_usuario = U.id) AS user_total_reviews
    FROM Usuario AS U
    JOIN Avaliacao AS Av ON Av.id_usuario = U.id
    JOIN Propriedade AS P ON P.id = Av.id_propriedade
    WHERE Av.id_propriedade = %s
      AND (%s IS NULL OR YEAR(Av.data) >= %s)
    ORDER BY Av.data DESC
    LIMIT 10
    OFFSET %s
    """

    try:
        results = execute_query(query, (property_id, min_year, min_year, offset))
        return results or []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar avaliações: {str(e)}"
        )


# ============================================================================
# CONSULTA 9: Perfil do anfitrião e suas propriedades
# ============================================================================


@router.get("/hosts/{host_id}/profile", response_model=HostProfile)
async def get_host_profile(host_id: int):
    """
    Retorna informações completas do anfitrião.
    Utilizada por: HostProfile (ao clicar no nome do anfitrião)
    """
    query = """
    SELECT 
        A.id AS host_id,
        A.nome AS host_name,
        A.url AS host_url,
        A.data_ingresso AS host_join_date,
        A.descricao AS host_description,
        A.superhost AS is_superhost,
        A.verificado AS verified,
        A.localizacao AS host_location,
        COUNT(DISTINCT P.id) AS total_properties,
        ROUND(AVG(P.nota), 2) AS average_rating,
        SUM(P.numero_avaliacoes) AS total_reviews
    FROM Anfitriao AS A
    LEFT JOIN Propriedade AS P ON P.id_anfitriao = A.id
    WHERE A.id = %s
    GROUP BY A.id, A.nome, A.url, A.data_ingresso, A.descricao, 
             A.superhost, A.verificado, A.localizacao
    """

    try:
        result = execute_query(query, (host_id,), fetch_one=True)

        if not result:
            raise HTTPException(status_code=404, detail="Anfitrião não encontrado")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar perfil do host: {str(e)}"
        )


@router.get("/hosts/{host_id}/properties", response_model=List[HostProperty])
async def get_host_properties(
    host_id: int, offset: int = Query(0, description="Offset para paginação")
):
    """
    Retorna propriedades do anfitrião (paginado).
    Inclui ranking da propriedade entre as do anfitrião.
    """
    query = """
    SELECT 
        P.id AS property_id,
        P.nome AS property_name,
        P.tipo AS property_type,
        P.bairro AS neighborhood,
        P.preco AS price,
        P.nota AS rating,
        P.numero_avaliacoes AS number_of_reviews,
        P.capacidade,
        P.quartos AS bedrooms,
        P.banheiros AS bathrooms,
        (SELECT COUNT(*) + 1
         FROM Propriedade AS P2
         WHERE P2.id_anfitriao = P.id_anfitriao
           AND (P2.nota > P.nota 
                OR (P2.nota = P.nota AND P2.numero_avaliacoes > P.numero_avaliacoes))
        ) AS ranking_among_host_properties
    FROM Propriedade AS P
    WHERE P.id_anfitriao = %s
    ORDER BY P.nota DESC, P.numero_avaliacoes DESC
    LIMIT 5
    OFFSET %s
    """

    try:
        results = execute_query(query, (host_id, offset))
        return results or []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar propriedades do host: {str(e)}"
        )
