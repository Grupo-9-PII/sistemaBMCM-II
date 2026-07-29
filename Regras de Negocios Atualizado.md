# Regras de Negócio do Sistema — Versão Atualizada



## 1. Cadastro

O sistema deve ser capaz de realizar vários tipos de cadastro com o objetivo de alimentar a base de dados.



### 1.1. Cadastro de usuário

O Sistema deve ser capaz de cadastrar usuários e distinguir entre usuário administrador, e usuário do sistema.



#### Regras do usuário administrador

- Ao cadastrar um usuário deverá ser fornecido um nome de usuário, uma senha e marcar a opção "Usuário administrador".

- O campo usuário deverá ser limitado em 40 caracteres e o sistema deve bloquear a inserção de mais caracteres além do limite. O campo deve impedir a digitação de caracteres especiais e números e permitir apenas letras, ponto (.) e underscore (_) e não deve permitir inserir espaço. Esse campo deve ser único.

- O campo senha deve ter no mínimo 6 caracteres e no máximo 10. O campo não deve permitir digitar caracteres além do permitido. O campo deve fornecer um botão para mostrar ou ocultar a visualização da senha. A senha deverá ser encriptada utilizando hash + salt.

- O cadastro de usuário deve incluir um switch para marcar se o usuário é um administrador.

- Os dois campos devem ser obrigatórios e caso não seja preenchido o sistema não deve permitir o cadastro e informar qual campo não foi digitado.

- O sistema deve permitir o cancelamento do cadastro tendo como ação voltar à página anterior.

- A senha deverá ser alterada no primeiro login efetuado.



#### Regras do usuário comum

O usuário comum deve ser cadastrado por um administrador que vai informar os dados de primeiro acesso (username/password). A senha deverá ser alterada no primeiro login efetuado.



### 1.2. Gestão de usuários

- O sistema deve listar e exibir usuários cadastrados no sistema. Deve ser exibida uma lista com informações do id, nome de usuário, tipo de usuário (administrador/usuário comum), status (ativo/inativo), status de senha (definida no primeiro acesso ou indefinida) e opções para gerenciar o usuário (editar, resetar senha e bloquear).

- O usuário admin padrão do sistema não deve ser exibido nesse painel.

- A funcionalidade de gerenciar usuários deve ser exibida apenas a um administrador do sistema.



#### Editar usuário

Ao editar um usuário o sistema deve permitir alterar a senha, bloqueando a digitação do campo de usuário. Também deve ser possível alterar entre usuário comum e administrador do sistema. Ao concluir a ação um popup deverá ser exibido informando a ação concluída.



#### Resetar senha

A senha deverá ser resetada para o padrão definido e o campo de status de senha deve ficar pendente até que seja efetuado um novo login no usuário editado. Ao concluir a ação um popup deverá ser exibido informando a ação concluída.



#### Bloquear usuário

A ação deve bloquear completamente o usuário impedindo de utilizar qualquer parte do sistema. Ao concluir a ação um popup deverá ser exibido informando a ação concluída.



#### Excluir usuário

A ação deve apagar completamente o usuário do banco de dados do sistema.



#### Proteção do usuário admin padrão

O usuário admin é destinado para manutenção do sistema, sendo que é listado na relação de usuários, mas nenhuma ação pode ser tomada por nenhum outro usuário, mesmo Administradores, não sendo possível a sua exclusão.

O gerenciamento de usuários deve ter um botão para cadastro de novo usuário.



---



## 2. Login e Autenticação

- O sistema deve autenticar o usuário através de nome de usuário e senha.

- Após 3 tentativas de login inválidas consecutivas, o sistema deve bloquear o usuário por 12 horas.

- O bloqueio deve impedir completamente o acesso ao sistema durante o período definido.

- No primeiro login de um usuário recém-cadastrado ou com senha resetada, o sistema deve obrigar a troca da senha antes de permitir o acesso às funcionalidades.

- A troca de senha deve exigir a senha atual, a nova senha e a confirmação da nova senha.

- A nova senha deve ter no mínimo 6 caracteres.

- A senha deve ser armazenada de forma segura utilizando hash com salt.

- O logout deve encerrar a sessão do usuário e redirecioná-lo para a tela de login.



---



## 3. Cadastro de Integrantes

O sistema deve ser capaz de cadastrar integrantes (alunos) da banda marcial, mantendo dados pessoais, de contato, endereço, responsáveis, vínculo escolar e foto.



### Regras do cadastro de integrante

- O campo nome é obrigatório.

- O campo CIN/RG deve ser único no sistema; caso já cadastrado, o sistema deve impedir o registro e informar o conflito.

- A data de nascimento, quando informada, deve ser validada quanto ao formato (YYYY-MM-DD).

- O campo e-mail, quando informado, deve ser armazenado em minúsculas.

- O campo telefone deve ser normalizado para o padrão nacional (XX) XXXXX-XXXX.

- O endereço deve permitir informação de CEP, logradouro, número, complemento, bairro, cidade e estado.

- O sistema deve permitir o vínculo de um integrante a uma escola previamente cadastrada.

- O sistema deve permitir o cadastro de um ou mais responsáveis vinculados ao integrante (nome do pai, nome da mãe, telefone, e-mail e endereço).

- O sistema deve permitir a seleção da função do integrante na banda (Maestro, Instrutor, Aluno, Coreógrafo).

- A foto do integrante deve aceitar apenas os formatos PNG, JPG, JPEG, GIF e WEBP.

- A foto deve ser renomeada automaticamente seguindo o padrão: aluno_{id}_{data_hora}.{extensão}.

- O sistema deve preservar o histórico do integrante; em vez de exclusão física, a inativação deve ser utilizada.

- A listagem de integrantes deve permitir busca por nome e filtro por status (ativo/inativo).

- Ao editar um integrante, o sistema deve manter o vínculo escolar atualizado (remover vínculo anterior e criar novo, se informado).

- O campo CIN/RG na edição deve ser validado contra duplicidade com outros integrantes.

- O sistema deve permitir informar a data de entrada na banda marcial (formato YYYY-MM-DD).

- O sistema deve permitir informar a data de desligamento da banda marcial (formato YYYY-MM-DD).

- Quando a data de desligamento for preenchida, o integrante deve ser automaticamente inativado (status = inativo).

- Quando a data de desligamento for removida/limpa, o integrante deve ser automaticamente ativado (status = ativo).

- A inativação automática deve ocorrer tanto na criação quanto na edição do integrante.

- As datas de entrada e desligamento devem ser validadas quanto ao formato (YYYY-MM-DD) e exibir mensagens de erro em caso de formato inválido.



---



## 4. Gestão de Escolas

- O sistema deve permitir o cadastro de escolas com nome e endereço.

- O nome da escola é obrigatório.

- O sistema deve listar todas as escolas cadastradas em ordem alfabética.

- O sistema deve permitir a edição dos dados da escola.

- O sistema deve permitir a exclusão física da escola do banco de dados.

- O sistema deve gerar relatório de escolas contendo o total de escolas cadastradas e o total de matrículas (vínculos de integrantes) por escola.



---



## 5. Gestão de Instrumentos

O sistema deve permitir o cadastro, edição, ativação/inativação e exclusão de instrumentos musicais do patrimônio da banda marcial.



### 5.1. Regras do instrumento

- O sistema deve permitir o cadastro de instrumentos com os seguintes campos: nome, tipo, naipe, patrimônio, marca, modelo, estado, data de aquisição e observações.

- O campo nome é obrigatório.

- O campo patrimônio, quando informado, deve ser único no sistema.

- A data de aquisição, quando informada, deve ser validada quanto ao formato (YYYY-MM-DD).

- O campo estado deve classificar o instrumento conforme as condições: Novo, Bom, Regular ou Ruim.

- O sistema deve permitir a edição dos dados do instrumento.

- O sistema deve permitir a ativação/inativação do instrumento (soft delete).

- O sistema deve permitir a exclusão física do instrumento.

- A listagem de instrumentos deve permitir busca por nome e filtros por status (ativo/inativo) e por tipo.

- Os tipos de instrumento pré-cadastrados no sistema são: Sopro e Percussão.

- Os naipes pré-cadastrados no sistema são: Madeira, Metais, Percussão e Clarim.

- O formulário de cadastro/edição de instrumento deve oferecer links de acesso rápido para gerenciamento de tipos e naipes.



### 5.2. Gestão de Tipos de Instrumento (NOVO)

- O sistema deve permitir o cadastro, edição e exclusão de tipos de instrumento de forma independente.

- O nome do tipo é obrigatório.

- O sistema não deve permitir a criação de tipos com nomes duplicados (validação case-insensitive).

- O sistema deve listar todos os tipos cadastrados em ordem alfabética, exibindo a quantidade de instrumentos vinculados a cada tipo.

- O sistema deve permitir a edição do nome de um tipo existente.

- O sistema deve permitir a exclusão de um tipo **somente se não houver instrumentos vinculados** a ele. Caso existam vínculos, o sistema deve impedir a exclusão e informar a quantidade de instrumentos dependentes.

- A funcionalidade de gerenciamento de tipos deve ser acessível apenas a usuários autenticados com perfil profissional ou administrador.

- A página de gerenciamento de tipos deve possuir formulário inline para criação e edição, sem necessidade de navegação para outra página.

- Ao editar um tipo, o formulário deve exibir o nome atual e permitir cancelar a operação.

- Todas as operações (criação, edição, exclusão) devem exibir mensagens de confirmação (flash messages).



### 5.3. Gestão de Naipes (NOVO)

- O sistema deve permitir o cadastro, edição e exclusão de naipes de forma independente.

- O nome do naipe é obrigatório.

- O sistema não deve permitir a criação de naipes com nomes duplicados (validação case-insensitive).

- O sistema deve listar todos os naipes cadastrados em ordem alfabética, exibindo a quantidade de instrumentos vinculados a cada naipe.

- O sistema deve permitir a edição do nome de um naipe existente.

- O sistema deve permitir a exclusão de um naipe **somente se não houver instrumentos vinculados** a ele. Caso existam vínculos, o sistema deve impedir a exclusão e informar a quantidade de instrumentos dependentes.

- A funcionalidade de gerenciamento de naipes deve ser acessível apenas a usuários autenticados com perfil profissional ou administrador.

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
