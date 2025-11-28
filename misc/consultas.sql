-- ============================================================================
-- 1. CONSULTA: Buscar propriedades com filtros básicos
-- ============================================================================
-- Endpoint: GET /api/listings/search
--            - Filtros aplicados no backend
-- ============================================================================

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
WHERE P.latitude IS NOT NULL 
  AND P.longitude IS NOT NULL
-- Ordenação por relevância (rating e reviews):
ORDER BY P.nota DESC, P.numero_avaliacoes DESC
LIMIT ?
-- Parâmetro: offset para paginação (0, 100, 200, 300, etc.)
OFFSET ?;

-- Filtros adicionados no backend:
-- AND P.latitude >= ?              -- south bound (se fornecido)
-- AND P.latitude <= ?              -- north bound (se fornecido)
-- AND P.longitude >= ?             -- west bound (se fornecido)
-- AND P.longitude <= ?             -- east bound (se fornecido)
-- AND P.preco >= ?                 -- min_price (se fornecido)
-- AND P.preco <= ?                 -- max_price (se fornecido)
-- AND P.bairro IN (?, ?, ...)      -- neighborhoods (se fornecido)
-- AND P.nota >= ?                  -- min_rating (se fornecido)
-- AND P.capacidade >= ?            -- min_capacity (se fornecido)
-- AND P.numero_avaliacoes >= ?     -- min_reviews (se fornecido)
-- AND A.superhost = 1              -- superhost_only (se fornecido)


-- ============================================================================
-- 2. CONSULTA: Obter amenidades de uma propriedade específica
-- ============================================================================
-- Endpoint: GET /api/properties/:id/amenities
-- ============================================================================

SELECT 
    Am.nome AS amenity_name
FROM Amenidade AS Am
WHERE Am.id_propriedade = ?
ORDER BY Am.nome;


-- ============================================================================
-- 3. CONSULTA: Estatísticas agregadas por bairro
-- ============================================================================
-- Endpoint: GET /api/neighborhoods/stats
-- ============================================================================

SELECT 
    P.bairro AS neighborhood,
    COUNT(P.id) AS total_listings,
    ROUND(AVG(P.preco), 2) AS average_price,
    ROUND(AVG(P.nota), 2) AS average_rating,
    ROUND(AVG(P.capacidade), 2) AS average_capacity,
    ROUND(AVG(P.quartos), 2) AS average_bedrooms,
    ROUND(AVG(P.banheiros), 2) AS average_bathrooms,
    ROUND(AVG(P.numero_avaliacoes), 2) AS average_reviews,
    SUM(CASE WHEN A.superhost = 1 THEN 1 ELSE 0 END) AS superhost_count,
    SUM(CASE WHEN A.verificado = 1 THEN 1 ELSE 0 END) AS verified_count
FROM Propriedade AS P
JOIN Anfitriao AS A ON P.id_anfitriao = A.id
GROUP BY P.bairro
ORDER BY total_listings DESC;


-- ============================================================================
-- 4. CONSULTA: Dados para heatmap de densidade
-- ============================================================================
-- Endpoint: GET /api/heatmap/density
-- ============================================================================

SELECT 
    P.latitude AS lat,
    P.longitude AS lng,
    1 AS intensity
FROM Propriedade AS P
WHERE P.latitude IS NOT NULL 
  AND P.longitude IS NOT NULL;


-- ============================================================================
-- 5. CONSULTA: Dados para heatmap de preços
-- ============================================================================
-- Endpoint: GET /api/heatmap/price
-- ============================================================================

SELECT 
    P.latitude AS lat,
    P.longitude AS lng,
    P.preco AS price,
    (P.preco - MIN(P.preco) OVER()) / (MAX(P.preco) OVER() - MIN(P.preco) OVER()) AS intensity
FROM Propriedade AS P
WHERE P.latitude IS NOT NULL 
  AND P.longitude IS NOT NULL
  AND P.preco IS NOT NULL;


-- ============================================================================
-- 6. CONSULTA: Verificar disponibilidade de uma propriedade
-- ============================================================================
-- Endpoint: GET /api/properties/:id/availability
-- ============================================================================

SELECT 
    C.data AS date
FROM Calendario AS C
WHERE C.id_propriedade = ?
-- Apenas datas disponíveis
  AND C.disponivel = 1
ORDER BY C.data;


-- ============================================================================
-- 7. CONSULTA: Obter avaliações de uma propriedade
-- ============================================================================
-- Endpoint: GET /api/properties/:id/reviews?min_year={ano}&offset={offset}
-- ============================================================================

SELECT 
    U.nome AS user_name,
    P.nome AS property_name,
    Av.comentario AS comment,
    Av.id AS review_id,
    Av.data AS review_date,
    U.id AS user_id,
    -- SUBQUERY: Total de avaliações feitas pelo usuário
    (SELECT COUNT(*)
     FROM Avaliacao AS Av2
     WHERE Av2.id_usuario = U.id) AS user_total_reviews
FROM Usuario AS U
JOIN Avaliacao AS Av ON Av.id_usuario = U.id
JOIN Propriedade AS P ON P.id = Av.id_propriedade
WHERE Av.id_propriedade = ?  -- Parâmetro: ID da propriedade
  AND (? IS NULL OR YEAR(Av.data) >= ?)  -- Parâmetro: ano mínimo (opcional)
ORDER BY Av.data DESC
LIMIT 10
-- Parâmetro: offset para paginação (0, 10, 20, 30, etc.)
OFFSET ?;


-- ============================================================================
-- 8. CONSULTA: Estatísticas gerais do sistema
-- ============================================================================
-- Endpoint: GET /api/stats/overview
-- ============================================================================

SELECT 
    COUNT(DISTINCT P.id) AS total_properties,
    COUNT(DISTINCT A.id) AS total_hosts,
    COUNT(DISTINCT P.bairro) AS total_neighborhoods,
    COUNT(DISTINCT U.id) AS total_users,
    ROUND(AVG(P.preco), 2) AS overall_avg_price,
    ROUND(AVG(P.nota), 2) AS overall_avg_rating,
    COUNT(DISTINCT CASE WHEN A.superhost = 1 THEN A.id END) AS total_superhosts,
    COUNT(DISTINCT CASE WHEN A.verificado = 1 THEN A.id END) AS total_verified_hosts,
    COUNT(DISTINCT Av.id) AS total_reviews
FROM Propriedade AS P
JOIN Anfitriao AS A ON P.id_anfitriao = A.id
LEFT JOIN Avaliacao AS Av ON Av.id_propriedade = P.id
LEFT JOIN Usuario AS U ON U.id = Av.id_usuario;


-- ============================================================================
-- 9.(a). CONSULTA: Perfil do anfitrião
-- ============================================================================
-- Endpoint: GET /api/hosts/:id/profile
-- ============================================================================

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
WHERE A.id = ?
GROUP BY A.id, A.nome, A.url, A.data_ingresso, A.descricao, A.superhost, A.verificado, A.localizacao;

-- ============================================================================
-- 9.(b). CONSULTA: Propriedades do anfitrião
-- ============================================================================
-- Endpoint: GET /api/hosts/:id/properties?offset={offset}
-- ============================================================================

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
    -- SUBCONSULTA: Ranking da propriedade entre as do anfitrião
    (SELECT COUNT(*) + 1
     FROM Propriedade AS P2
     WHERE P2.id_anfitriao = P.id_anfitriao
       AND (P2.nota > P.nota 
            OR (P2.nota = P.nota AND P2.numero_avaliacoes > P.numero_avaliacoes))
    ) AS ranking_among_host_properties
FROM Propriedade AS P
WHERE P.id_anfitriao = ?  -- Parâmetro: ID do anfitrião
ORDER BY P.nota DESC, P.numero_avaliacoes DESC
LIMIT 5
-- Parâmetro: offset para paginação (0, 5, 10, 15, etc.)
OFFSET ?;


-- ============================================================================
-- 10. CONSULTA: Ranking dos melhores anfitriões por bairro
-- ============================================================================
-- Endpoint: GET /api/hosts/ranking?neighborhood={bairro}
-- ============================================================================

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
    -- SUBQUERY: Calcula ranking do anfitrião no bairro
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
-- Filtro opcional por bairro (pode ser removido para ver todos)
WHERE P.bairro = ?
GROUP BY A.id, A.nome, A.superhost, A.verificado, P.bairro
-- Apenas anfitriões com 2+ propriedades
HAVING COUNT(P.id) >= 2
ORDER BY avg_rating DESC, total_reviews DESC
LIMIT 50;


-- ============================================================================
-- 11. CONSULTA: Propriedades mais avaliadas nos últimos 6 meses
-- ============================================================================
-- Endpoint: GET /api/properties/trending
-- ============================================================================

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
LIMIT 20;
