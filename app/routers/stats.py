"""Router para endpoints relacionados a estatísticas."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models.schemas import (
    NeighborhoodStats,
    OverviewStats,
    HostRanking,
    TrendingProperty,
)
from app.database.connection import execute_query

router = APIRouter(prefix="/api", tags=["Statistics"])


# ============================================================================
# CONSULTA 3: Estatísticas agregadas por bairro
# ============================================================================


@router.get("/neighborhoods/stats", response_model=List[NeighborhoodStats])
async def get_neighborhood_stats():
    """
    Retorna estatísticas agregadas de cada bairro.
    Utilizada por: Statistics (gera gráficos e tabela de estatísticas por bairro)
    """
    query = """
    SELECT 
        P.bairro AS neighborhood,
        COUNT(DISTINCT P.id) AS total_listings,
        ROUND(AVG(P.preco), 2) AS average_price,
        ROUND(AVG(P.nota), 2) AS average_rating,
        ROUND(AVG(P.capacidade), 2) AS average_capacity,
        ROUND(AVG(P.quartos), 2) AS average_bedrooms,
        ROUND(AVG(P.banheiros), 2) AS average_bathrooms,
        ROUND(AVG(P.numero_avaliacoes), 2) AS average_reviews,
        SUM(CASE WHEN A.superhost = 1 THEN 1 ELSE 0 END) AS superhost_count,
        SUM(CASE WHEN A.verificado = 1 THEN 1 ELSE 0 END) AS verified_count
    FROM Propriedade AS P
    INNER JOIN Anfitriao AS A ON P.id_anfitriao = A.id
    GROUP BY P.bairro
    ORDER BY total_listings DESC
    """

    try:
        results = execute_query(query)
        return results or []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar estatísticas por bairro: {str(e)}"
        )


# ============================================================================
# CONSULTA 8: Estatísticas gerais do sistema
# ============================================================================


@router.get("/stats/overview", response_model=OverviewStats)
async def get_overview_stats():
    """
    Retorna estatísticas gerais do sistema.
    Utilizada por: Statistics (cards de resumo no dashboard)
    """
    query = """
    SELECT 
        COUNT(DISTINCT P.id) AS total_properties,
        COUNT(DISTINCT A.id) AS total_hosts,
        COUNT(DISTINCT P.bairro) AS total_neighborhoods,
        COUNT(DISTINCT U.id) AS total_users,
        ROUND(AVG(P.preco), 2) AS overall_avg_price,
        ROUND(AVG(P.nota), 2) AS overall_avg_rating,
        SUM(CASE WHEN A.superhost = 1 THEN 1 ELSE 0 END) AS total_superhosts,
        SUM(CASE WHEN A.verificado = 1 THEN 1 ELSE 0 END) AS total_verified_hosts,
        COUNT(DISTINCT Av.id) AS total_reviews
    FROM Propriedade AS P
    JOIN Anfitriao AS A ON P.id_anfitriao = A.id
    LEFT JOIN Avaliacao AS Av ON Av.id_propriedade = P.id
    LEFT JOIN Usuario AS U ON U.id = Av.id_usuario
    """

    try:
        result = execute_query(query, fetch_one=True)
        if not result:
            raise HTTPException(
                status_code=404, detail="Não foi possível obter estatísticas"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar estatísticas gerais: {str(e)}"
        )


# ============================================================================
# CONSULTA 10: Ranking de anfitriões por bairro
# ============================================================================


@router.get("/hosts/ranking", response_model=List[HostRanking])
async def get_host_ranking(neighborhood: Optional[str] = Query(None)):
    """
    Retorna ranking de anfitriões com múltiplas propriedades.
    Utilizada por: Statistics (tabela "Top Hosts por Bairro")
    """

    # Construir query dinâmica baseada no filtro
    if neighborhood:
        where_clause = "WHERE P.bairro = ?"
        params = (neighborhood,)
    else:
        where_clause = ""
        params = ()

    query = f"""
    SELECT 
        A.id AS host_id,
        A.nome AS host_name,
        A.superhost AS is_superhost,
        A.verificado AS verified,
        P.bairro AS neighborhood,
        COUNT(DISTINCT P.id) AS total_properties,
        ROUND(AVG(P.nota), 2) AS avg_rating,
        SUM(P.numero_avaliacoes) AS total_reviews,
        ROUND(AVG(P.preco), 2) AS avg_price,
        (SELECT COUNT(DISTINCT A2.id)
         FROM Anfitriao AS A2
         INNER JOIN (
            SELECT id_anfitriao, AVG(nota) as avg_rating, SUM(numero_avaliacoes) as total_reviews
            FROM Propriedade
            WHERE bairro = P.bairro
            GROUP BY id_anfitriao
            HAVING COUNT(id) >= 2
         ) AS HostStats ON A2.id = HostStats.id_anfitriao
         WHERE HostStats.avg_rating > AVG(P.nota)
            OR (HostStats.avg_rating = AVG(P.nota) AND HostStats.total_reviews > SUM(P.numero_avaliacoes))
        ) + 1 AS neighborhood_host_rank
    FROM Anfitriao AS A
    INNER JOIN Propriedade AS P ON A.id = P.id_anfitriao
    {where_clause}
    GROUP BY A.id, A.nome, A.superhost, A.verificado, P.bairro
    HAVING COUNT(P.id) >= 2
    ORDER BY avg_rating DESC, total_reviews DESC
    LIMIT 50
    """

    try:
        results = execute_query(query, params if params else None)
        return results or []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar ranking de anfitriões: {str(e)}"
        )


# ============================================================================
# CONSULTA 11: Propriedades mais avaliadas nos últimos 6 meses
# ============================================================================


@router.get("/properties/trending", response_model=List[TrendingProperty])
async def get_trending_properties():
    """
    Retorna propriedades com mais avaliações recentes (últimos 6 meses).
    Utilizada por: Statistics (card "Propriedades Mais Populares")
    """
    query = """
    SELECT 
        P.id AS property_id,
        P.nome AS property_name,
        P.bairro AS neighborhood,
        P.preco AS price,
        P.nota AS rating,
        A.nome AS host_name,
        A.superhost AS is_superhost,
        COUNT(Av.id) AS recent_reviews_count,
        COUNT(DISTINCT U.id) AS unique_reviewers,
        ROUND(AVG(CASE 
            WHEN Av.comentario IS NOT NULL THEN LENGTH(Av.comentario)
            ELSE 0 
        END), 0) AS avg_comment_length
    FROM Propriedade AS P
    INNER JOIN Anfitriao AS A ON P.id_anfitriao = A.id
    INNER JOIN Avaliacao AS Av ON Av.id_propriedade = P.id
    INNER JOIN Usuario AS U ON U.id = Av.id_usuario
    WHERE Av.data >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
    GROUP BY P.id, P.nome, P.bairro, P.preco, P.nota, A.nome, A.superhost
    HAVING recent_reviews_count >= 5
    ORDER BY recent_reviews_count DESC, unique_reviewers DESC
    LIMIT 20
    """

    try:
        results = execute_query(query)
        return results or []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar propriedades em alta: {str(e)}"
        )
