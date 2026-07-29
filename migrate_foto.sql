-- Migração: Tabelas Autorização Foto (ECA/LGPD)
-- Execute: sqlite3 instance/database.db < migrate_foto.sql

CREATE TABLE IF NOT EXISTS autorizacao_foto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id INTEGER NOT NULL,
    nome_responsavel TEXT NOT NULL,
    cpf_responsavel TEXT,
    telefone_responsavel TEXT,
    email_responsavel TEXT,
    ip TEXT,
    user_agent TEXT,
    termo_texto TEXT NOT NULL,
    hash_conteudo TEXT NOT NULL,
    assinatura_base64 TEXT,
    data_assinatura DATETIME,
    autoriza_foto BOOLEAN DEFAULT 0,
    pdf_path TEXT,
    codigo_2fa TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (aluno_id) REFERENCES aluno (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS log_autorizacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    autorizacao_id INTEGER NOT NULL,
    acao TEXT NOT NULL,
    ip TEXT,
    user_agent TEXT,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (autorizacao_id) REFERENCES autorizacao_foto (id) ON DELETE CASCADE
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_autorizacao_aluno ON autorizacao_foto(aluno_id);
CREATE INDEX IF NOT EXISTS idx_log_autorizacao ON log_autorizacao(autorizacao_id);
