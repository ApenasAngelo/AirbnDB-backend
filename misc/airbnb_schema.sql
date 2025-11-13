CREATE TABLE Usuario(
	id BIGINT PRIMARY KEY,
	nome VARCHAR(100)
);

CREATE TABLE Anfitriao (
	id BIGINT PRIMARY KEY,
	nome VARCHAR(100) NOT NULL,
	url VARCHAR(255) UNIQUE,
	data_ingresso DATE,
	descricao TEXT,
	superhost BOOLEAN,
	verificado BOOLEAN,
	localizacao VARCHAR(100)
);

CREATE TABLE Propriedade (
	id BIGINT PRIMARY KEY,
	nome VARCHAR(255),
	tipo VARCHAR(100),
	capacidade INT,
	bairro VARCHAR(100),
	quartos INT,
	banheiros DECIMAL(4,2),
	camas INT,
	descricao TEXT,
	url VARCHAR(255),
	nota DECIMAL(2, 1),
	preco DECIMAL(10, 2),
	numero_avaliacoes INT,
	tipo_quarto VARCHAR(30),
	latitude DECIMAL(9, 6),
	longitude DECIMAL(9, 6),
	id_anfitriao BIGINT
);

CREATE TABLE Calendario (
	data DATE, 
	disponivel BOOLEAN,
	id_propriedade BIGINT,
	PRIMARY KEY (data, id_propriedade)
);

CREATE TABLE Avaliacao (
	id BIGINT,
	data DATE,
	comentario TEXT,
	id_usuario BIGINT,
	id_propriedade BIGINT,
	PRIMARY KEY (id)
);

CREATE TABLE Amenidade (
	id_propriedade BIGINT,
	nome VARCHAR(100),
	PRIMARY KEY(id_propriedade, nome)
);

ALTER TABLE Propriedade
	ADD FOREIGN KEY(id_anfitriao)
	REFERENCES Anfitriao (id);

ALTER TABLE Calendario
	ADD FOREIGN KEY(id_propriedade)
	REFERENCES Propriedade (id);

ALTER TABLE Avaliacao
	ADD FOREIGN KEY(id_usuario)
	REFERENCES Usuario (id);

ALTER TABLE Avaliacao
	ADD FOREIGN KEY(id_propriedade)
	REFERENCES Propriedade (id);

ALTER TABLE Amenidade
	ADD FOREIGN KEY(id_propriedade)
	REFERENCES Propriedade (id);