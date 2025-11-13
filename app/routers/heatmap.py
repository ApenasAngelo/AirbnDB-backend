"""Router para endpoints relacionados a heatmaps."""

from fastapi import APIRouter, HTTPException
from typing import List
from app.models.schemas import HeatmapPoint
from app.database.connection import execute_query

router = APIRouter(prefix="/api", tags=["Heatmap"])


# ============================================================================
# CONSULTA 4: Dados para heatmap de densidade
# ============================================================================


@router.get("/heatmap/density", response_model=List[HeatmapPoint])
async def get_density_heatmap():
    """
    Retorna coordenadas de todas as propriedades para mapa de calor de densidade.
    Cada propriedade tem peso 1 (intensity).
    """
    query = """
    SELECT 
        P.latitude AS lat,
        P.longitude AS lng,
        1 AS intensity
    FROM Propriedade AS P
    WHERE P.latitude IS NOT NULL 
      AND P.longitude IS NOT NULL
    """

    try:
        results = execute_query(query)
        return results or []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar dados de densidade: {str(e)}"
        )


# ============================================================================
# CONSULTA 5: Dados para heatmap de preços
# ============================================================================


@router.get("/heatmap/price", response_model=List[HeatmapPoint])
async def get_price_heatmap():
    """
    Retorna coordenadas e preços normalizados para mapa de calor de preços.
    A intensidade é calculada normalizando os preços entre 0 e 1.
    """
    query = """
    SELECT 
        P.latitude AS lat,
        P.longitude AS lng,
        P.preco AS price,
        (P.preco - MIN(P.preco) OVER()) / 
        NULLIF((MAX(P.preco) OVER() - MIN(P.preco) OVER()), 0) AS intensity
    FROM Propriedade AS P
    WHERE P.latitude IS NOT NULL 
      AND P.longitude IS NOT NULL
      AND P.preco IS NOT NULL
    """

    try:
        results = execute_query(query)
        # Garantir que intensity não seja None (caso todos os preços sejam iguais)
        for result in results:
            if result["intensity"] is None:
                result["intensity"] = 0.5
        return results or []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar dados de preços: {str(e)}"
        )
