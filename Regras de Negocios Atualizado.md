# Regras de Negócio do Sistema — Versão Atualizada

Este documento representa o estado atual do sistema como implementado no código e nas telas existentes. Ele tem como referência a lógica ativa do aplicativo, não apenas requisitos de projeto em fase de idealização.

## 1. Visão geral e perfis de acesso

O sistema é um ambiente web para gestão operacional da banda marcial, com foco em cadastro de integrantes, presenças, eventos, instrumentos, passes, comunicações e manutenção do banco de dados.

Os perfis atualmente praticados na aplicação são:

- Administrador: acesso completo à manutenção do sistema, usuários, backup, controles gerais e ações sensíveis.
- Profissional/operacional: acesso às rotas de gestão da banda, presenças, relatório, comunicações e cadastros operacionais.
- Usuário comum: acesso restringido às áreas permitidas pela autenticação e pela regra de permissão do sistema.

A proteção de rotas é feita via autenticação e decorators de permissão. Algumas ações críticas, como alteração de usuários, restauração de backup e gestão de passes, exigem privilégios administrativos.

---

## 2. Login, autenticação e segurança

### 2.1. Autenticação

- O sistema autentica o usuário com nome de usuário e senha.
- O login exige sessão ativa e validação de CSRF em ações mutáveis.
- Usuários podem ter senha obrigatória para troca no primeiro acesso ou após reset.
- A senha deve ser armazenada em hash com salt, nunca em texto puro.

### 2.2. Bloqueios e proteção

- Após tentativas inválidas consecutivas, o usuário pode ser bloqueado temporariamente.
- O bloqueio impede o acesso ao sistema até que o período de contenção termine.
- O usuário administrador padrão é protegido contra exclusão e reset sem controle explícito.
- Ações destrutivas e mutáveis exigem confirmação via POST com token CSRF.

### 2.3. Gestão de usuários

- O cadastro de usuários exige usuário e senha.
- O sistema aceita a distinção entre usuário administrador e usuário comum.
- Usuários podem ser ativados ou bloqueados.
- A senha pode ser redefinida por um administrador.
- O usuário admin padrão deve permanecer preservado para manutenção do sistema.

---

## 3. Cadastro de integrantes

O módulo de integrantes é o núcleo operacional do sistema e reúne dados pessoais, contatos, evento de vida na banda, vínculo escolar, foto e cartão de passe.

### 3.1. Dados principais

- O campo nome é obrigatório.
- O campo CIN/RG é obrigatório quando informado e deve ser único no sistema.
- O e-mail, quando preenchido, é normalizado para minúsculas.
- O telefone é normalizado para o padrão nacional.
- O endereço inclui CEP, logradouro, número, complemento, bairro, cidade e estado.
- O status de ativo/inativo do integrante é administrado pelo sistema.

### 3.2. Funções, escolas e vínculos

- O integrante pode ser vinculado a uma função da banda, como Maestro, Instrutor, Aluno ou Coreógrafo.
- O integrante pode estar vinculado a uma ou mais escolas.
- O vínculo escolar é preservado e atualizado conforme o cadastro/edição do registro.
- O cadastro pode incluir dados de responsáveis, como pai, mãe e contato de emergência.

### 3.3. Datas e status

- O sistema aceita data de entrada na banda.
- O sistema aceita data de desligamento da banda.
- Quando a data de desligamento é preenchida, o integrante é automaticamente inativado.
- Quando a data de desligamento é removida ou limpa, o integrante pode voltar a ficar ativo.
- A inativação automática funciona tanto na criação quanto na edição do integrante.

### 3.4. Cartão de passe

- O cartão de passe é opcional, mas, quando cadastrado, deve ser único.
- Somente integrantes com cartão ativo podem receber cota mensal ou lançamentos de passes.
- O número de controle do cartão deve ser único no banco.

### 3.5. Foto e autorização de menor

- A foto do integrante aceita os formatos comuns de imagem do sistema.
- Se houver autorização de imagem de menor, o sistema registra o responsável, termo, versão, data, usuário e IP de origem.
- O consentimento para imagem de menor deve ser ligado ao arquivo fotográfico específico autorizado.
- Quando a foto da pessoa menor muda, a autorização vigente precisa ser revalidada.

### 3.6. Busca e listagem

- A listagem de integrantes permite busca por nome.
- A listagem também pode filtrar por status de ativo/inativo.
- O histórico do integrante é preservado por inativação, em vez de exclusão física.

---

## 4. Gestão de escolas

- O cadastro de escola exige nome e permite endereço complementar.
- A listagem de escolas é tratada como base operacional para vínculo dos integrantes.
- A escola pode ser editada conforme necessidade administrativa.
- O sistema trabalha com vínculo de alunos por escola e pode gerar relatórios por unidade.
- O relatório de escolas deve contemplar quantidade de matrículas por unidade.

---

## 5. Instrumentos, tipos e naipes

### 5.1. Instrumentos

- O cadastro de instrumento inclui nome, tipo, naipe, patrimônio, marca, modelo, estado, data de aquisição e observações.
- O nome do instrumento é obrigatório.
- O patrimônio, quando informado, deve ser único.
- O estado do instrumento pode ser Novo, Bom, Regular ou Ruim.
- O instrumento pode ser ativado ou inativado.
- A listagem permite busca por nome e filtros por status e por tipo.

### 5.2. Tipos de instrumento

- O sistema mantém tipos independentes para categoria de instrumento.
- Os tipos usados no sistema incluem Sopro e Percussão.
- O nome do tipo é obrigatório.
- Não é permitido cadastrar nomes duplicados em comparação case-insensitive.
- O tipo só pode ser excluído se não houver instrumentos vinculados.
- A exclusão com dependência deve ser bloqueada e informada ao usuário.

### 5.3. Naipes

- O sistema mantém naipes independentes, com cadastro e listagem de apoio ao patrimônio musical.
- Os naipes cadastrados incluem Madeira, Metais, Percussão e Clarim.
- O nome do naipe é obrigatório.
- O cadastro de nomes duplicados é bloqueado.
- O naipe só pode ser excluído quando não houver instrumento vinculado a ele.

---

## 6. Presença, ensaios, eventos e atividades

### 6.1. Registros de presença

- A presença do integrante é registrada por atividade, ensaio ou evento.
- Cada aluno pode ter apenas uma presença por atividade/ensaio/evento dentro do mesmo contexto.
- O registro inclui data da presença, atributo de presença/ausência e observações.
- O sistema registra quem lançou a presença e o momento do registro.

### 6.2. Atividades, ensaios e eventos

- Atividades avulsas, ensaios e eventos são tratados como categoria de presença.
- O sistema pode sincronizar atividades com o Google Calendar, quando a integração estiver autorizada.
- Presenças vinculadas a eventos também podem ser usadas em regras de autorização de viagem.

### 6.3. Autorização de viagem

- O responsável pode autorizar a participação do menor em evento ou viagem.
- A autorização é registrada por evento e pode ser consultada para envio de comunicação ou controle de presença.

---

## 7. Gestão de passes e cotas

A regra de passes é uma funcionalidade operativa importante do sistema, com histórico, cota mensal, lançamentos avulsos e consumo por presença.

### 7.1. Cota mensal

- Cada aluno pode ter uma cota mensal de passes vinculada a um mês de referência.
- A cota é registrada por integrante e por mês.
- A cota mensal só pode ser cadastrada para participante com cartão de passe ativo.
- O sistema aceita quantidade zero ou positiva para a cota mensal; valores negativos são rejeitados.

### 7.2. Lançamentos e recargas

- A cota pode receber lançamento mensal.
- O sistema também aceita lançamento avulso, com justificativa obrigatória.
- A recarga extra mensal exige motivo administrativo e é registrada como movimento de ajuste.
- O sistema impede múltiplos registros duplicados da mesma recarga ou do mesmo lançamento avulso para o mesmo integrante no mês.

### 7.3. Consumo por presença

- Cada presença registrada consome 2 passes no saldo do aluno para o mês do evento/atividade.
- O sistema verifica o saldo antes de registrar a presença.
- Se o saldo for insuficiente, a presença não pode ser validada.
- O sistema realiza sincronização entre presença e movimento de passe com controle de estorno e saldo atual.

### 7.4. Histórico de movimentos

- Todos os movimentos de passes são auditados: disponibilização, consumo, recarga, estorno e outros ajustes.
- O histórico é consultável por mês e por aluno.
- O saldo atual é calculado a partir dos movimentos cumulados.

### 7.5. Condições de elegibilidade

- Somente integrantes com cartão ativo podem receber cotas e movimentações.
- O sistema bloqueia operações para cartões inativos ou inexistentes.

---

## 8. Central de comunicações

A Central de Comunicações é um módulo de envio de mensagens por e-mail, com público-alvo definido por regras de negócio.

### 8.1. Públicos suportados

- Geral: integrantes ativos.
- Responsáveis: responsável principal cadastrado do integrante.
- Evento: alunos autorizados para o evento especificado.
- Nipe: integrantes ativos com instrumentos vinculados ao naipe escolhido.
- Contatos externos: contatos previamente cadastrados ou informados com autorização válida.

### 8.2. Criação da comunicação

- A comunicação exige assunto e mensagem.
- O usuário define canal, tipo e público-alvo.
- Foi implementado controle explícito para evitar mistura de destinatário externo com outros públicos.
- Anexos podem ser adicionados à comunicação.
- A comunicação é criada em rascunho e só é enviada após confirmação de envio.

### 8.3. Regra de contatos externos

- O contato externo deve estar ativo para receber e-mail.
- O contato só pode receber e-mail se houver autorização de e-mail vigente.
- Se a autorização não existir, o sistema exige consentimento explícito e origem do consentimento.
- O contato pode ter autorização revogada; nesse caso o envio é bloqueado.
- O envio de e-mail para contato externo não pode acontecer sem esse controle.

### 8.4. Envio e rastreio

- O sistema monta a lista de destinatários elegíveis conforme o público selecionado.
- Os destinatários são registrados em histórico de envio da comunicação.
- O status da comunicação pode ser rascunho, enviado, parcial ou erro.
- O envio é processado e o erro individual do destinatário é mantido em log.

### 8.5. Bloqueio do módulo

- A Central de Comunicações fica indisponível quando a integração com o Google Workspace não está autorizada ou configurada.
- O sistema exibe aviso e bloqueia o fluxo de envio.

---

## 9. Integração com Google Workspace e OAuth

A aplicação pode operar com integrações Google para e-mail e calendário.

### 9.1. Google OAuth

- O sistema depende de autorização OAuth para uso de Gmail e/ou Google Calendar.
- A validação da disponibilidade da integração é feita por estado da configuração e autorização do usuário.
- Se a integração não estiver disponível, a funcionalidade de comunicação e sincronização com o calendário fica bloqueada.

### 9.2. Google Calendar

- Atividades, ensaios e eventos podem ser sincronizados com o Google Calendar quando autorizados.
- O sistema registra o identificador do evento gerado no Google e a data de sincronização.
- Se a sincronização falhar, a atividade pode ser salva no sistema e o usuário recebe aviso de falha de sincronização, sem interromper o fluxo principal.

### 9.3. Gmail

- O e-mail de envio pode ser usado por meio da conta configurada no Google Workspace.
- O envio de comunicações depende da validade da conta emissora e da autorização ativa do Google.
- Um envio de teste foi realizado com sucesso usando uma conta Google real; esta validação confirma o fluxo básico de envio, mas não substitui as verificações de consentimento, autorização e elegibilidade dos destinatários em cada comunicação.

---

## 10. Backup, restauração e proteção do banco

O sistema possui rotinas de backup e restauração do banco SQLite.

### 10.1. Backup local

- O sistema gera backups compactados em ZIP.
- Os arquivos ficam em pasta local de backup do usuário, na estrutura correspondente ao ambiente do sistema.
- A nomenclatura dos arquivos segue o padrão de backup do sistema.
- O painel administrativo expõe ações para criar, listar, restaurar e excluir backups.

### 10.2. Restauração

- Antes da restauração, o sistema salva uma cópia de segurança do banco atual.
- O backup é validado antes de ser restaurado.
- A restauração exige confirmação do administrador e informa que a aplicação pode precisar ser reiniciada.

### 10.3. Segurança do backup

- As operações de backup/restauração são restritas a administradores.
- Os backups devem ser protegidos por senha e por ambiente controlado.
- A senha do sistema e a localização de armazenamento precisam estar protegidas para evitar perda de dados.

### 10.4. Google Drive (opcional)

- O sistema também pode enviar cópias de backup para pasta específica do Google Drive, quando a integração e a configuração de armazenamento estiverem habilitadas.

---

## 11. LGPD, consentimento e proteção de dados

### 11.1. Autorização de imagem

- Para menores de idade, ou sempre que a autorização for requerida, o sistema exige consentimento do responsável legal antes de armazenar a imagem do integrante.
- A autorização registra responsável, vínculo, CPF quando informado, assinatura digital, e data/hora do consentimento.
- O sistema salva o arquivo de assinatura e vincula o consentimento à foto autorizada.

### 11.2. Auditoria

- O sistema registra quem realizou a autorização, qual termo foi aceito, o IP de origem e a versão do termo.
- Isso fornece rastreabilidade para o uso de imagens e dados pessoais.

### 11.3. Dados sensíveis e armazenamento

- Dados pessoais, contatos e fotos devem ser tratados como informações sensíveis.
- O sistema usa armazenamento local e controle de regras para evitar uso indevido de dados.
- O compartilhamento de dados por e-mail é permitido apenas para destinatários autorizados ou públicos elegíveis.

---

## 12. Inicialização do sistema

Na primeira execução, o sistema verifica a existência de dados essenciais e cria o mínimo necessário para funcionamento.

- Se não existir usuário administrador, o sistema pode criar um usuário padrão de manutenção.
- Os tipos de instrumento e naipes podem ser criados automaticamente, caso ainda não existam.
- As funções da banda podem ser inicializadas automaticamente.
- A base local de municípios e logradouros pode ser importada quando a base estiver vazia.

---

## 13. Normalização de dados

O sistema aplica normalização em vários campos para manter consistência.

- Nomes e endereços são tratados em formato padronizado.
- E-mails são armazenados em minúsculas.
- Telefones são normalizados para o padrão nacional.
- Estados (UF) são armazenados em maiúsculas.
- Dados de endereço e CEP podem ser preenchidos automaticamente a partir da base local ou fallback de consulta externa.

---

## 14. Regras atuais de operação

As regras abaixo refletem o funcionamento real da aplicação em sua versão atual:

- O sistema prioriza cadastros e manutenção operacional da banda marcial.
- A gestão de usuários, backup e tecnologia é centralizada em administradores.
- A gestão de presenças e passes é funcional e auditável por mês.
- A central de comunicações exige autorização e público explícito.
- O módulo de Google Workspace deve estar disponível para comunicação e sincronização.
- A aplicação usa um modelo de operação baseado em dados reais, históricos e confirmação de ações sensíveis.

Este documento deve ser entendido como uma descrição do comportamento atual do sistema e não como lista de requisitos futuros sem implementação validada no código e nas telas.
- A página de gerenciamento de naipes deve possuir formulário inline para criação e edição, sem necessidade de navegação para outra página.

- Ao editar um naipe, o formulário deve exibir o nome atual e permitir cancelar a operação.

- Todas as operações (criação, edição, exclusão) devem exibir mensagens de confirmação (flash messages).



---



## 6. Relatórios

- O sistema deve gerar relatório geral de integrantes ativos, exibindo dados pessoais, de contato, endereço, responsáveis e escola vinculada.

- O sistema deve gerar relatório individual por integrante, contendo todas as informações cadastrais.

- O sistema deve gerar relatório de escolas com quantidade de matrículas por unidade.

- Todos os relatórios devem exibir a data e hora de geração.

- Os relatórios devem seguir layout profissional para impressão ou exportação.



---



## 7. Endereçamento e CEP

- O sistema deve possuir base local de logradouros e cidades importada previamente.

- Ao informar um CEP no cadastro de integrante, o sistema deve consultar a base local e preencher automaticamente os campos de endereço (tipo, logradouro, bairro, cidade, UF).

- Caso o CEP não exista na base local, o sistema deve consultar a API ViaCEP como fallback.

- Logradouros consultados na API ViaCEP devem ser salvos automaticamente na base local para consultas futuras.

- A busca de CEP deve ser acessível apenas a usuários autenticados.



---



## 8. Consentimento de Imagem de Menor (LGPD)

- Para integrantes menores de 18 anos, ou cuja data de nascimento seja desconhecida, o sistema deve exigir autorização do responsável legal para armazenamento e uso da imagem.

- A autorização só é exigida quando houver upload de foto do integrante.

- O termo de autorização deve possuir controle de versão para auditoria.

- O responsável deve informar: nome completo, vínculo (Pai, Mãe, Responsável Legal ou Outro) e CPF (opcional).

- O responsável deve realizar uma assinatura digital desenhada diretamente no navegador.

- A assinatura digital deve ser convertida em imagem PNG e armazenada vinculada ao registro de autorização.

- O sistema deve registrar: data/hora do consentimento, usuário que registrou, IP de origem e versão do termo aceito.

- O consentimento deve ser vinculado ao arquivo de foto específico que está sendo autorizado.

- Na edição de um integrante menor que já possua foto, caso não exista autorização vigente para o arquivo atual, o sistema deve exigir nova autorização.

- A autorização vigente é aquela cujo arquivo de foto coberto corresponde exatamente à foto atual do integrante.



---



## 9. Inicialização do Sistema

- Na primeira execução, caso não exista nenhum usuário administrador, o sistema deve criar automaticamente o usuário padrão "admin" com senha inicial "123456".

- O usuário admin padrão deve ter a flag de troca obrigatória de senha ativada.

- O sistema deve criar automaticamente os tipos de instrumento (Sopro e Percussão) caso não existam.

- O sistema deve criar automaticamente os naipes (Madeira, Metais, Percussão e Clarim) caso não existam.

- O sistema deve criar automaticamente as funções da banda (Maestro, Instrutor, Aluno e Coreógrafo) caso não existam.

- O sistema deve importar automaticamente os municípios e logradouros do arquivo "municipios.sql", caso presente e a base local esteja vazia.



---



## 10. Normalização de Dados

- Campos textuais de nome, endereço, bairro, cidade, naturalidade e complemento devem ser normalizados para caixa alta e sem espaços duplicados.

- O campo telefone deve ser normalizado para o padrão (XX) XXXXX-XXXX ou (XX) XXXX-XXXX.

- O campo e-mail deve ser armazenado em minúsculas.

- O campo estado (UF) deve ser armazenado em maiúsculas.

- O campo CIN/RG deve ser mantido conforme digitado pelo usuário, sem transformação de caixa (preserva máscara e pontuação).



---



## 11. Estruturas Previstas

O sistema possui modelos de dados definidos para as seguintes funcionalidades, ainda em fase de implementação futura:



### Presença

Registro de presença dos integrantes por data, com indicação de presente/ausente e observações.



### Uniforme

Controle de entrega de uniformes aos integrantes, com data de entrega, tamanho e observações.



### Autorização de Viagem

Registro de autorização do responsável para participação do menor em eventos e viagens.



### Evento

Cadastro de eventos com nome, cidade, data, telefone de contato, responsável, taxa de participação, status e indicação de isenção.



---



## 12. Backup e Restauração do Banco de Dados (NOVO)

### 12.1. Geral

- O sistema deve permitir realizar backup e restauração do banco de dados SQLite.
- A funcionalidade deve ser acessível apenas por usuários administradores do sistema.
- O sistema deve exibir informações sobre o estado atual do banco de dados (existência, tamanho e localização).
- O sistema deve exibir a senha padrão de backup em local visível no painel de backup.

### 12.2. Criação de Backup

- O sistema deve permitir criar backups do banco de dados através de ação manual no painel administrativo.
- O backup deve ser compactado em formato ZIP.
- A senha do arquivo ZIP deve ser uma senha padrão do sistema (`SISTBMCM2024`), não sendo necessária definição pelo usuário.
- O arquivo de backup deve seguir o padrão de nomenclatura: `backup_YYYYMMDD_HHMMSS.zip`.
- Os backups devem ser salvos na pasta do usuário, subpasta `BKPSISTBMCM`.

### 12.3. Listagem de Backups

- O sistema deve listar todos os backups disponíveis na pasta `BKPSISTBMCM`.
- A listagem deve exibir: nome do arquivo, data de criação e tamanho.
- A listagem deve ser ordenada do backup mais recente para o mais antigo.

### 12.4. Restauração de Backup

- O sistema deve permitir restaurar o banco de dados a partir de um backup selecionado.
- Antes da restauração, o sistema deve criar automaticamente uma cópia de segurança do banco de dados atual.
- A cópia de segurança pré-restauração deve ser salva na mesma pasta `BKPSISTBMCM` com prefixo `database_pre_restore_`.
- O sistema deve validar a integridade do arquivo de backup antes de restaurar.
- Após restauração bem-sucedida, o sistema deve informar que é necessário reiniciar a aplicação para que as alterações tenham efeito.
- A restauração deve ser protegida por confirmação do usuário, alertando sobre a substituição do banco de dados atual.

### 12.5. Exclusão de Backup

- O sistema deve permitir excluir arquivos de backup individualmente.
- A exclusão deve ser protegida por confirmação do usuário.

### 12.6. Segurança

- O acesso ao painel de backup deve ser restrito exclusivamente a administradores.
- Todas as operações (criação, restauração, exclusão) devem exibir mensagens de confirmação ou erro (flash messages).
- A senha padrão de backup deve ser documentada e acessível no painel para evitar problemas de recuperação.
