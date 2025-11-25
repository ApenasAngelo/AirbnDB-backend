# Backend AirbnDB - API FastAPI

Backend da aplicação AirbnDB desenvolvido com FastAPI e MySQL para o trabalho de Banco de Dados.

## 🚀 Tecnologias

- **FastAPI** - Framework web moderno e rápido
- **MySQL** - Banco de dados relacional
- **mysql-connector-python** - Driver Python para MySQL
- **Pydantic** - Validação de dados
- **uv** - Gerenciador de pacotes Python

## 📋 Pré-requisitos

- Python 3.10 ou superior
- MySQL 8.0 ou superior
- uv (gerenciador de pacotes)

## 🔧 Instalação

1. **Criar e ativar o ambiente virtual:**

```bash
uv venv
.venv\Scripts\activate  # Windows
```

2. **Instalar dependências:**

```bash
uv pip install -e .
```

3. **Configurar variáveis de ambiente:**

Copie o arquivo `.env.example` para `.env` e configure:

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais do MySQL:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=airbnb
```

4. **Criar o banco de dados:**

Execute o script SQL `airbnb_schema.sql` (localizado na pasta /misc) no MySQL para um banco de dados limpo:

```bash
mysql -u root -p < ../airbnb.sql
```

Ou utilize o `airbnb_com_dados.sql` da mesma forma, para popular o banco de dados automaticamente.

## ▶️ Executar a aplicação

Execute a aplicação iniciando o script principal na raiz do projeto:

```bash
python run.py
```

O alias python pode variar entre as máquinas (`py`, `python`, `python3`, etc)

A API estará disponível em: `http://localhost:8000`

Documentação interativa (Swagger): `http://localhost:8000/docs`

## 📚 Endpoints da API

### Root & Health

- `GET /` - Informações da API
- `GET /health` - Health check

### Listings

- `GET /api/listings/search` - Buscar propriedades com filtros avançados
  - Query params: `min_price`, `max_price`, `neighborhoods`, `min_rating`, `min_capacity`, `min_reviews`, `superhost_only`, `check_in`, `check_out`, `min_available_days`, `limit`, `offset`
- `GET /api/properties/{property_id}/amenities` - Amenidades de uma propriedade
- `GET /api/properties/{property_id}/availability` - Disponibilidade de uma propriedade
- `GET /api/properties/{property_id}/reviews` - Avaliações de uma propriedade (paginado)
  - Query params: `min_year`, `offset`
- `GET /api/hosts/{host_id}/profile` - Perfil completo do anfitrião
- `GET /api/hosts/{host_id}/properties` - Propriedades de um anfitrião (paginado)
  - Query params: `offset`

### Statistics

- `GET /api/neighborhoods/stats` - Estatísticas agregadas por bairro
- `GET /api/stats/overview` - Estatísticas gerais do sistema
- `GET /api/hosts/ranking` - Ranking de anfitriões com múltiplas propriedades
  - Query params: `neighborhood` (opcional)
- `GET /api/properties/trending` - Propriedades com mais avaliações recentes (últimos 6 meses)

### Heatmap

- `GET /api/heatmap/density` - Dados para mapa de calor de densidade
- `GET /api/heatmap/price` - Dados para mapa de calor de preços

### Search

- `GET /api/listings/search` - Busca com filtros avançados
  - Query params: `min_price`, `max_price`, `neighborhood1`, `neighborhood2`, `property_type`, `min_rating`, `min_capacity`, `min_reviews`, `amenity`, `superhost_only`
- `GET /api/listings/best-deals` - Melhores ofertas (bom preço + múltiplas amenidades + host verificado)
  - Query params: `max_price`, `min_amenities`

## 🧪 Testar com Postman

Importe o arquivo `postman_collection.json` (localizado na pasta /misc) no Postman para testar todos os endpoints.

## 👨‍💻 Desenvolvimento

O projeto utiliza `uv` como gerenciador de pacotes. Para adicionar novas dependências:

```bash
uv pip install nome-do-pacote
```
