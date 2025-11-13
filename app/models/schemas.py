"""Schemas Pydantic para validação de dados da API."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal


# ============================================================================
# Modelos básicos
# ============================================================================


class Host(BaseModel):
    """Modelo para representar um anfitrião."""

    id: int = Field(..., alias="host_id")
    name: str = Field(..., alias="host_name")
    is_superhost: bool = Field(..., alias="is_superhost")
    verified: bool
    join_date: Optional[date] = Field(None, alias="host_join_date")
    url: Optional[str] = Field(None, alias="host_url")
    description: Optional[str] = Field(None, alias="host_description")
    location: Optional[str] = Field(None, alias="host_location")

    class Config:
        populate_by_name = True


class Property(BaseModel):
    """Modelo para representar uma propriedade."""

    id: int = Field(..., alias="property_id")
    name: str = Field(..., alias="property_name")
    description: Optional[str] = Field(None, alias="property_description")
    type: str = Field(..., alias="property_type")
    capacity: int = Field(..., alias="capacidade")
    bedrooms: int
    beds: int
    bathrooms: float
    neighborhood: str
    latitude: float
    longitude: float
    room_type: Optional[str] = None

    class Config:
        populate_by_name = True


class Amenity(BaseModel):
    """Modelo para uma amenidade."""

    name: str = Field(..., alias="amenity_name")

    class Config:
        populate_by_name = True


class Listing(BaseModel):
    """Modelo completo para uma acomodação (property + host + pricing)."""

    property_id: int
    property_name: str
    property_description: Optional[str] = None
    property_type: str
    capacity: int = Field(..., alias="capacidade")
    bedrooms: int
    beds: int
    bathrooms: float
    neighborhood: str
    latitude: float
    longitude: float
    room_type: Optional[str] = None
    price: float
    listing_url: str
    rating: float
    number_of_reviews: int
    host_id: int
    host_name: str
    is_superhost: bool
    verified: bool
    host_join_date: Optional[date] = None
    neighborhood_ranking: Optional[int] = None
    amenities: Optional[List[str]] = []

    class Config:
        populate_by_name = True


class ListingSimple(BaseModel):
    """Modelo simplificado para listagem de propriedades no mapa."""

    property_id: int
    property_name: str
    property_type: str
    price: float
    rating: float
    neighborhood: str
    latitude: float
    longitude: float
    number_of_reviews: int
    host_name: str
    is_superhost: bool

    class Config:
        populate_by_name = True


# ============================================================================
# Modelos para Estatísticas
# ============================================================================


class NeighborhoodStats(BaseModel):
    """Estatísticas agregadas por bairro."""

    neighborhood: str
    total_listings: int
    average_price: float
    average_rating: float
    average_capacity: Optional[float] = None
    average_bedrooms: Optional[float] = None
    average_bathrooms: Optional[float] = None
    average_reviews: Optional[float] = None
    superhost_count: Optional[int] = None
    verified_count: Optional[int] = None

    class Config:
        populate_by_name = True


class OverviewStats(BaseModel):
    """Estatísticas gerais do sistema."""

    total_properties: int
    total_hosts: int
    total_neighborhoods: int
    total_users: int
    overall_avg_price: float
    overall_avg_rating: float
    total_superhosts: int
    total_verified_hosts: int
    total_reviews: int

    class Config:
        populate_by_name = True


class HostRanking(BaseModel):
    """Ranking de anfitriões por bairro."""

    host_id: int
    host_name: str
    is_superhost: bool
    verified: bool
    neighborhood: str
    total_properties: int
    avg_rating: float
    total_reviews: int
    avg_price: float
    neighborhood_host_rank: int

    class Config:
        populate_by_name = True


class TrendingProperty(BaseModel):
    """Propriedades mais avaliadas recentemente."""

    property_id: int
    property_name: str
    neighborhood: str
    price: float
    rating: float
    host_name: str
    is_superhost: bool
    recent_reviews_count: int
    unique_reviewers: int
    avg_comment_length: int

    class Config:
        populate_by_name = True


# ============================================================================
# Modelos para Heatmap
# ============================================================================


class HeatmapPoint(BaseModel):
    """Ponto no mapa de calor."""

    lat: float
    lng: float
    intensity: float
    price: Optional[float] = None

    class Config:
        populate_by_name = True


# ============================================================================
# Modelos para Avaliações
# ============================================================================


class Review(BaseModel):
    """Modelo para uma avaliação."""

    review_id: int
    review_date: date
    comment: Optional[str] = None
    user_id: int
    user_name: str
    property_name: Optional[str] = None
    user_total_reviews: Optional[int] = 0

    class Config:
        populate_by_name = True


# ============================================================================
# Modelos para Calendário
# ============================================================================


class Availability(BaseModel):
    """Disponibilidade de uma propriedade em uma data."""

    date: date
    available: bool

    class Config:
        populate_by_name = True


class AvailabilityDate(BaseModel):
    """Data disponível de uma propriedade."""

    date: date

    class Config:
        populate_by_name = True


class HostProfile(BaseModel):
    """Perfil completo de um anfitrião."""

    host_id: int
    host_name: str
    host_url: Optional[str] = None
    host_join_date: Optional[date] = None
    host_description: Optional[str] = None
    is_superhost: bool
    verified: bool
    host_location: Optional[str] = None
    total_properties: int
    average_rating: Optional[float] = None
    total_reviews: int

    class Config:
        populate_by_name = True


class HostProperty(BaseModel):
    """Propriedade de um anfitrião."""

    property_id: int
    property_name: str
    property_type: str
    neighborhood: str
    price: float
    rating: float
    number_of_reviews: int
    capacity: int = Field(..., alias="capacidade")
    bedrooms: int
    bathrooms: float
    ranking_among_host_properties: int

    class Config:
        populate_by_name = True


# ============================================================================
# Modelos para Buscas e Filtros
# ============================================================================


class SearchFilters(BaseModel):
    """Filtros para busca de propriedades."""

    min_price: Optional[float] = None
    max_price: Optional[float] = None
    neighborhoods: Optional[List[str]] = None
    property_type: Optional[str] = None
    min_rating: Optional[float] = None
    min_capacity: Optional[int] = None
    min_reviews: Optional[int] = None
    amenity: Optional[str] = None
    superhost_only: Optional[bool] = None
