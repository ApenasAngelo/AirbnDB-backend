"""Router para endpoints de busca e filtros avançados."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models.schemas import ListingSimple, BestDeal
from app.database.connection import execute_query

router = APIRouter(prefix="/api", tags=["Search"])


# ============================================================================
# CONSULTA 9: Filtrar propriedades por critérios
# ============================================================================


@router.get("/listings/search", response_model=List[ListingSimple])
async def search_listings(
    min_price: Optional[float] = Query(None, description="Preço mínimo"),
    max_price: Optional[float] = Query(None, description="Preço máximo"),
    neighborhood1: Optional[str] = Query(None, description="Bairro 1"),
    neighborhood2: Optional[str] = Query(None, description="Bairro 2"),
    property_type: Optional[str] = Query(None, description="Tipo de propriedade"),
    min_rating: Optional[float] = Query(None, description="Nota mínima"),
    min_capacity: Optional[int] = Query(None, description="Capacidade mínima"),
    min_reviews: Optional[int] = Query(None, description="Número mínimo de avaliações"),
    amenity: Optional[str] = Query(None, description="Amenidade específica"),
    superhost_only: Optional[bool] = Query(None, description="Apenas superhosts"),
):
    """
    Busca propriedades com filtros avançados.
    Funcionalidade futura para busca/filtro no mapa.
    """
    query = """
    SELECT DISTINCT 
        P.id AS property_id,
        P.nome AS property_name,
        P.url AS listing_url,
        P.tipo AS property_type,
        P.preco AS price,
        P.nota AS rating,
        P.bairro AS neighborhood,
        P.latitude,
        P.longitude,
        P.numero_avaliacoes AS number_of_reviews,
        A.nome AS host_name,
        A.superhost AS is_superhost
    FROM Propriedade AS P
    JOIN Amenidade AS Am ON P.id = Am.id_propriedade
    JOIN Avaliacao AS Av ON P.id = Av.id_propriedade
    JOIN Anfitriao AS A ON P.id_anfitriao = A.id
    WHERE 1=1
    """

    params = []

    # Adicionar filtros opcionais
    if max_price is not None:
        query += " AND P.preco <= %s"
        params.append(max_price)

    if min_price is not None:
        query += " AND P.preco >= %s"
        params.append(min_price)

    if neighborhood1 or neighborhood2:
        neighborhoods = [n for n in [neighborhood1, neighborhood2] if n is not None]
        if neighborhoods:
            placeholders = ", ".join(["%s"] * len(neighborhoods))
            query += f" AND P.bairro IN ({placeholders})"
            params.extend(neighborhoods)

    if property_type is not None:
        query += " AND P.tipo = %s"
        params.append(property_type)

    if min_rating is not None:
        query += " AND P.nota >= %s"
        params.append(min_rating)

    if min_capacity is not None:
        query += " AND P.capacidade >= %s"
        params.append(min_capacity)

    if min_reviews is not None:
        query += " AND P.numero_avaliacoes > %s"
        params.append(min_reviews)

    if amenity is not None:
        query += " AND Am.nome = %s"
        params.append(amenity)

    if superhost_only is not None:
        query += " AND A.superhost = %s"
        params.append(1 if superhost_only else 0)

    query += " ORDER BY P.nota DESC, P.numero_avaliacoes DESC"

    try:
        results = execute_query(query, tuple(params) if params else None)
        return results or []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar propriedades: {str(e)}"
        )


# ============================================================================
# CONSULTA 14: Melhores ofertas
# ============================================================================


@router.get("/listings/best-deals", response_model=List[BestDeal])
async def get_best_deals(
    max_price: float = Query(5000, description="Preço máximo"),
    min_amenities: int = Query(3, description="Número mínimo de amenidades"),
):
    """
    Retorna as melhores ofertas: bom preço + múltiplas amenidades + host verificado.
    Funcionalidade futura para seção de "Recomendações" ou "Melhores Ofertas".
    """
    query = """
    SELECT 
        P.id AS property_id,
        P.nome AS property_name,
        P.url AS listing_url,
        P.preco AS price,
        P.nota AS rating,
        P.bairro AS neighborhood,
        P.latitude,
        P.longitude,
        COUNT(Am.nome) AS amenities_count,
        Anf.nome AS host_name,
        Anf.verificado AS host_verified
    FROM Propriedade P
    JOIN Anfitriao Anf ON P.id_anfitriao = Anf.id
    JOIN Amenidade Am ON P.id = Am.id_propriedade
    WHERE P.preco < %s
      AND Anf.verificado = TRUE
    GROUP BY P.id, P.nome, P.url, P.preco, P.nota, P.bairro, 
             P.latitude, P.longitude, Anf.nome, Anf.verificado
    HAVING COUNT(Am.nome) >= %s
    ORDER BY P.nota DESC, amenities_count DESC, P.preco ASC
    """

    try:
        results = execute_query(query, (max_price, min_amenities))
        return results or []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar melhores ofertas: {str(e)}"
        )
