-- =====================================================================
-- Cupcake Store – Projeto Físico do Banco de Dados (MySQL 8)
-- Derivado do Diagrama de Classes de persistência do PIT I.
-- Herança Usuario -> Cliente/Administrador/Entregador mapeada em
-- TABELA ÚNICA (coluna discriminadora `tipo`).
-- =====================================================================

DROP DATABASE IF EXISTS cupcake_store;
CREATE DATABASE cupcake_store CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cupcake_store;

-- ---------------------------------------------------------------------
-- Usuários (Usuario, Cliente, Administrador, Entregador)
-- ---------------------------------------------------------------------
CREATE TABLE usuario (
    id               INT           NOT NULL AUTO_INCREMENT,
    tipo             VARCHAR(20)   NOT NULL COMMENT 'cliente | administrador | entregador',
    nome             VARCHAR(120)  NOT NULL,
    email            VARCHAR(120)  NOT NULL,
    senha_hash       VARCHAR(255)  NOT NULL COMMENT 'RNF01 – hash, nunca a senha',
    telefone         VARCHAR(20),
    data_cadastro    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cpf              CHAR(11)               COMMENT 'Cliente – RN09',
    data_nascimento  DATE                   COMMENT 'Cliente',
    nivel_acesso     INT                    COMMENT 'Administrador',
    cnh              VARCHAR(20)            COMMENT 'Entregador',
    veiculo          VARCHAR(60)            COMMENT 'Entregador',
    CONSTRAINT pk_usuario PRIMARY KEY (id),
    CONSTRAINT uq_usuario_email UNIQUE (email),
    CONSTRAINT uq_usuario_cpf UNIQUE (cpf),
    CONSTRAINT ck_usuario_tipo CHECK (tipo IN ('cliente', 'administrador', 'entregador'))
) ENGINE = InnoDB;

CREATE TABLE endereco (
    id           INT           NOT NULL AUTO_INCREMENT,
    cliente_id   INT           NOT NULL,
    logradouro   VARCHAR(150)  NOT NULL,
    numero       VARCHAR(10)   NOT NULL,
    complemento  VARCHAR(60),
    bairro       VARCHAR(80)   NOT NULL,
    cidade       VARCHAR(80)   NOT NULL,
    uf           CHAR(2)       NOT NULL,
    cep          CHAR(8)       NOT NULL,
    CONSTRAINT pk_endereco PRIMARY KEY (id),
    CONSTRAINT fk_endereco_cliente FOREIGN KEY (cliente_id) REFERENCES usuario (id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- Catálogo
-- ---------------------------------------------------------------------
CREATE TABLE categoria (
    id         INT           NOT NULL AUTO_INCREMENT,
    nome       VARCHAR(60)   NOT NULL,
    descricao  VARCHAR(255),
    CONSTRAINT pk_categoria PRIMARY KEY (id),
    CONSTRAINT uq_categoria_nome UNIQUE (nome)
) ENGINE = InnoDB;

CREATE TABLE produto (
    id            INT            NOT NULL AUTO_INCREMENT,
    categoria_id  INT            NOT NULL,
    nome          VARCHAR(100)   NOT NULL,
    descricao     TEXT,
    sabor         VARCHAR(60),
    preco         DECIMAL(10,2)  NOT NULL,
    estoque       INT            NOT NULL DEFAULT 0,
    imagem_url    VARCHAR(255),
    ativo         BOOLEAN        NOT NULL DEFAULT TRUE COMMENT 'RN08 – exclusão lógica',
    CONSTRAINT pk_produto PRIMARY KEY (id),
    CONSTRAINT fk_produto_categoria FOREIGN KEY (categoria_id) REFERENCES categoria (id),
    CONSTRAINT ck_produto_preco CHECK (preco > 0),        -- RN07
    CONSTRAINT ck_produto_estoque CHECK (estoque >= 0)    -- RN07
) ENGINE = InnoDB;

CREATE INDEX ix_produto_categoria_ativo ON produto (categoria_id, ativo);

-- ---------------------------------------------------------------------
-- Carrinho
-- ---------------------------------------------------------------------
CREATE TABLE carrinho (
    id            INT       NOT NULL AUTO_INCREMENT,
    cliente_id    INT       NOT NULL,
    data_criacao  DATETIME  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_carrinho PRIMARY KEY (id),
    CONSTRAINT uq_carrinho_cliente UNIQUE (cliente_id),   -- composição 1:1
    CONSTRAINT fk_carrinho_cliente FOREIGN KEY (cliente_id) REFERENCES usuario (id) ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE item_carrinho (
    id              INT            NOT NULL AUTO_INCREMENT,
    carrinho_id     INT            NOT NULL,
    produto_id      INT            NOT NULL,
    quantidade      INT            NOT NULL DEFAULT 1,
    preco_unitario  DECIMAL(10,2)  NOT NULL,
    CONSTRAINT pk_item_carrinho PRIMARY KEY (id),
    CONSTRAINT fk_item_carrinho_carrinho FOREIGN KEY (carrinho_id) REFERENCES carrinho (id) ON DELETE CASCADE,
    CONSTRAINT fk_item_carrinho_produto FOREIGN KEY (produto_id) REFERENCES produto (id),
    CONSTRAINT ck_item_carrinho_qtd CHECK (quantidade > 0)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- Pedido e classes compostas
-- ---------------------------------------------------------------------
CREATE TABLE cupom (
    id          INT           NOT NULL AUTO_INCREMENT,
    codigo      VARCHAR(30)   NOT NULL,
    percentual  DECIMAL(5,2)  NOT NULL,
    validade    DATE          NOT NULL,
    ativo       BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_cupom PRIMARY KEY (id),
    CONSTRAINT uq_cupom_codigo UNIQUE (codigo),
    CONSTRAINT ck_cupom_percentual CHECK (percentual > 0 AND percentual <= 100)
) ENGINE = InnoDB;

CREATE TABLE pedido (
    id            INT            NOT NULL AUTO_INCREMENT,
    cliente_id    INT            NOT NULL,
    endereco_id   INT            NOT NULL,
    cupom_id      INT,
    data_pedido   DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subtotal      DECIMAL(10,2)  NOT NULL,
    desconto      DECIMAL(10,2)  NOT NULL DEFAULT 0,
    taxa_entrega  DECIMAL(10,2)  NOT NULL DEFAULT 0,
    valor_total   DECIMAL(10,2)  NOT NULL COMMENT 'RN03 – subtotal − desconto + taxa',
    status        ENUM('AGUARDANDO_PAGAMENTO','PAGO','EM_PREPARO','SAIU_PARA_ENTREGA','ENTREGUE','CANCELADO')
                                 NOT NULL DEFAULT 'AGUARDANDO_PAGAMENTO',
    CONSTRAINT pk_pedido PRIMARY KEY (id),
    CONSTRAINT fk_pedido_cliente FOREIGN KEY (cliente_id) REFERENCES usuario (id),
    CONSTRAINT fk_pedido_endereco FOREIGN KEY (endereco_id) REFERENCES endereco (id),
    CONSTRAINT fk_pedido_cupom FOREIGN KEY (cupom_id) REFERENCES cupom (id),
    CONSTRAINT ck_pedido_total CHECK (valor_total = subtotal - desconto + taxa_entrega)
) ENGINE = InnoDB;

CREATE INDEX ix_pedido_status_data ON pedido (status, data_pedido);
CREATE INDEX ix_pedido_cliente ON pedido (cliente_id, data_pedido);

CREATE TABLE item_pedido (
    id              INT            NOT NULL AUTO_INCREMENT,
    pedido_id       INT            NOT NULL,
    produto_id      INT            NOT NULL,
    quantidade      INT            NOT NULL,
    preco_unitario  DECIMAL(10,2)  NOT NULL COMMENT 'preço congelado no momento da compra',
    CONSTRAINT pk_item_pedido PRIMARY KEY (id),
    CONSTRAINT fk_item_pedido_pedido FOREIGN KEY (pedido_id) REFERENCES pedido (id) ON DELETE CASCADE,
    CONSTRAINT fk_item_pedido_produto FOREIGN KEY (produto_id) REFERENCES produto (id),
    CONSTRAINT ck_item_pedido_qtd CHECK (quantidade > 0)
) ENGINE = InnoDB;

CREATE TABLE pagamento (
    id                INT            NOT NULL AUTO_INCREMENT,
    pedido_id         INT            NOT NULL,
    forma             ENUM('PIX','CARTAO_CREDITO','CARTAO_DEBITO') NOT NULL,
    valor             DECIMAL(10,2)  NOT NULL,
    status            ENUM('PENDENTE','APROVADO','RECUSADO') NOT NULL DEFAULT 'PENDENTE',
    codigo_transacao  VARCHAR(64),
    tentativas        INT            NOT NULL DEFAULT 0 COMMENT 'RN05 – 3 recusas cancelam o pedido',
    data_pagamento    DATETIME,
    CONSTRAINT pk_pagamento PRIMARY KEY (id),
    CONSTRAINT uq_pagamento_pedido UNIQUE (pedido_id),    -- composição 1:1
    CONSTRAINT fk_pagamento_pedido FOREIGN KEY (pedido_id) REFERENCES pedido (id) ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE entrega (
    id             INT       NOT NULL AUTO_INCREMENT,
    pedido_id      INT       NOT NULL,
    entregador_id  INT,
    status         ENUM('AGUARDANDO','EM_ROTA','ENTREGUE') NOT NULL DEFAULT 'AGUARDANDO',
    previsao       DATETIME,
    data_entrega   DATETIME,
    CONSTRAINT pk_entrega PRIMARY KEY (id),
    CONSTRAINT uq_entrega_pedido UNIQUE (pedido_id),      -- composição 1:1
    CONSTRAINT fk_entrega_pedido FOREIGN KEY (pedido_id) REFERENCES pedido (id) ON DELETE CASCADE,
    CONSTRAINT fk_entrega_entregador FOREIGN KEY (entregador_id) REFERENCES usuario (id)
) ENGINE = InnoDB;

CREATE TABLE avaliacao (
    id          INT           NOT NULL AUTO_INCREMENT,
    pedido_id   INT           NOT NULL,
    nota        INT           NOT NULL,
    comentario  VARCHAR(500),
    data        DATETIME      DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_avaliacao PRIMARY KEY (id),
    CONSTRAINT uq_avaliacao_pedido UNIQUE (pedido_id),
    CONSTRAINT fk_avaliacao_pedido FOREIGN KEY (pedido_id) REFERENCES pedido (id) ON DELETE CASCADE,
    CONSTRAINT ck_avaliacao_nota CHECK (nota BETWEEN 1 AND 5)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- Dados iniciais mínimos (o restante é criado por `flask seed`)
-- ---------------------------------------------------------------------
INSERT INTO categoria (nome, descricao) VALUES
    ('Clássicos', 'Os sabores que todo mundo ama.'),
    ('Gourmet', 'Receitas especiais com ingredientes selecionados.'),
    ('Fit & Veganos', 'Sem lactose, sem açúcar refinado ou 100% vegetais.'),
    ('Datas Especiais', 'Edições limitadas para presentear.');

INSERT INTO cupom (codigo, percentual, validade) VALUES
    ('BEMVINDO10', 10.00, DATE_ADD(CURDATE(), INTERVAL 1 YEAR)),
    ('DOCE20', 20.00, DATE_ADD(CURDATE(), INTERVAL 1 YEAR));
