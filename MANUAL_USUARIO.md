# Manual do Usuário - Sistema BMCM

## Sistema de Gestão da Banda Marcial Municipal de Marília - SP

---
> 📘 Este manual foi desenvolvido para orientar o uso do Sistema BMCM.
>
> Para dúvidas técnicas, entre em contato com o administrador.

## 1. Introdução

### 1.1 Objetivo do Sistema
O Sistema BMCM é uma aplicação web desenvolvida para apoiar a gestão administrativa da Banda Marcial Municipal de Marília - SP. O sistema permite o cadastro, consulta, atualização e acompanhamento de integrantes da banda, com foco em organização administrativa e continuidade histórica dos dados.

### 1.2 Público-Alvo
- Administradores do sistema
- Profissionais responsáveis pela gestão
- Coordenadores da banda

### 1.3 Requisitos de Acesso
- Navegador web moderno (Chrome, Firefox, Edge, Safari)
- Conexão com o servidor onde o sistema está hospedado
- Credenciais de acesso (usuário e senha)

---

## 2. Guia Rápido

Siga os passos abaixo para começar a utilizar o sistema rapidamente:

1. Acesse o sistema pelo navegador
2. Informe seu usuário e senha
3. Após o login, acesse o menu superior e clique em **Integrantes**
4. Clique em **"Novo Integrante"**
5. Preencha os dados obrigatórios
6. Clique em **"Salvar"**

✔ Pronto! O aluno já estará cadastrado no sistema.

> Dica: Utilize o menu superior para navegar entre as funcionalidades.
>
## 3. Acesso ao Sistema

### 3.1 Tela de Login
Ao acessar o sistema, o usuário será direcionado para a tela de login.

![Tela de Login](./assets/imgs/Login.png)

**Campos:**
- **Usuário**: Campo obrigatório para inserção do nome de usuário
- **Senha**: Campo obrigatório para inserção da senha

**Botão "Entrar"**: Realiza a autenticação no sistema

### 3.2 Primeiro Acesso
No primeiro acesso, o sistema solicitará a alteração da senha padrão. O usuário deverá:
1. Inserir a senha atual (fornecida pelo administrador)
2. Criar uma nova senha com no mínimo 6 caracteres
3. Confirmar a nova senha

![Tela de Login](./assets/imgs/tela-alterar-senha.png)
### 3.3 Recuperação de Senha
Em caso de esquecimento de senha, entre em contato com o administrador do sistema.

---

## 4. Dashboard (Painel Principal)

### 4.1 Visão Geral
Após o login, o usuário acessa o dashboard que apresenta estatísticas gerais do sistema:

![Dashboard](./assets/imgs/Dash.png)

Estatísticas apresentadas:
- Total de alunos cadastrados
- Alunos ativos
- Total de escolas cadastradas
- Instrumentos ativos
- Usuários ativos
- Usuários administradores

### 4.2 Menu de Navegação
O menu principal está disponível na barra superior ou lateral e permite acesso a todas as funcionalidades do sistema.

![Menu](./assets/imgs/tela-menu.png)

---

## 4. Gestão de Usuários (Administrador)

### 4.1 Listar Usuários
Acesse o menu superior e clique em **Usuários** para visualizar todos os usuários cadastrados no sistema.

![Usuarios](./assets/imgs/tela-admin-usuarios.png)

**Informações exibidas:**
- Nome de usuário
- Status (ativo/inativo)
- Tipo (administrador ou não)
- Última alteração de senha

### 4.2 Criar Novo Usuário
1. Acesse o menu superior e clique em **Usuários**
2. Clique em **"Novo Usuário"**
3. Preencha os campos:

![Novo Usuario](./assets/imgs/tela-criar-usuario.png)

- **Usuário**: Nome de login (único)
- **Senha**: Senha inicial
- **Administrador**: Marque se o usuário terá acesso administrativo
4. Clique em **"Salvar"**

### 4.3 Editar Usuário
1. Acesse o menu superior e clique em **Usuários**
2. Clique no botão de edição ao lado do usuário desejado
3. Altere os dados necessários
4. Clique em **"Salvar"**

**Nota**: O nome de usuário não pode ser alterado após a criação.

### 4.4 Alterar Senha de Usuário
1. Acesse o menu superior e clique em **Usuários**
2. Clique em **"Resetar Senha"** ao lado do usuário
3. A senha será redefinida para a senha padrão do sistema

### 4.5 Ativar/Desativar Usuário
1. Acesse o menu superior e clique em **Usuários**
2. Clique no botão de alternância ao lado do usuário
3. O usuário será ativado ou bloqueado imediatamente

### 4.6 Excluir Usuário
1. Acesse o menu superior e clique em **Usuários**
2. Clique no botão de exclusão ao lado do usuário
3. Confirme a exclusão na mensagem apresentada

**Nota**: O usuário "admin" não pode ser excluído ou alterado por outros usuários.

---

## 5. Gestão de Alunos/Integrantes

### 5.1 Listar Alunos
Acesse o menu superior e clique em **Integrantes** para visualizar todos os alunos cadastrados.

![Integrantes](./assets/imgs/tela-admin-alunos.png)

**Filtros disponíveis:**
- Busca por nome
- Filtrar por status (ativos/inativos)

**Informações exibidas:**
- Nome do aluno
- Data de nascimento
- Escola
- Status (ativo/inativo)
- Ações (editar, visualizar, excluir)

### 5.2 Cadastrar Novo Aluno
1. Acesse o menu superior e clique em **Integrantes**
2. Clique em **"Novo Aluno"**
3. Preencha os dados em abas:

![Cadastro de Integrantes](./assets/imgs/tela-cadastrar-aluno.png)

**Aba Dados Pessoais:**
- Nome completo (obrigatório)
- Data de nascimento
- Naturalidade
- CPF/RG
- E-mail
- Telefone

**Aba Endereço:**
- CEP (busca automática)
- Endereço
- Número
- Complemento
- Bairro
- Cidade
- Estado

**Aba Informações da Banda:**
- Função na banda (maestro, aluno, etc.)
- Foto do aluno

**Aba Escola:**
- Selecione a escola
- Ano letivo

**Aba Instrumento:**
- Selecione o instrumento atualmente associado ao integrante
- Informe observações, quando necessário

Ao trocar o instrumento, a associação anterior recebe uma data de devolução e permanece no histórico. Instrumentos inativos não podem ser associados a novos integrantes.

**Aba Responsáveis (para menores):**
- Nome do responsável
- Parentesco
- Telefone
- E-mail

**Aba Autorizações:**
- Termo de autorização de foto (obrigatório para menores)

4. Clique em **"Salvar"**


### 5.3  Cadastro de Aluno Menor de Idade

Para alunos menores de 18 anos:

1. Preencha os dados normalmente
2. Vá até a aba **Responsáveis**
3. Cadastre pelo menos um responsável
4. Vá até a aba **Autorizações**
5. Marque o consentimento de imagem
6. Realize a assinatura digital

⚠ Obrigatório para salvar com foto

### 5.4 Editar Aluno
1. Acesse o menu superior e clique em **Integrantes**
2. Clique no botão de edição ao lado do aluno desejado
3. Altere os dados necessários
4. Clique em **"Salvar"**

### 5.5 Visualizar Aluno (Relatório Individual)
1. Acesse o menu superior e clique em **Integrantes**
2. Clique no botão de visualização ao lado do aluno
3. O sistema exibirá um relatório completo com todos os dados

![Rel Aluno](./assets/imgs/tela-relatorio-aluno.png)

### 5.6 Ativar/Desativar Aluno
1. Acesse o menu superior e clique em **Integrantes**
2. Clique no botão de alternância ao lado do aluno
3. O aluno será marcado como inativo (não excluído)

**Nota**: O sistema mantém o histórico dos alunos inativos ao invés de excluí-los.

### 5.7 Excluir Aluno
1. Acesse o menu superior e clique em **Integrantes**
2. Clique no botão de exclusão ao lado do aluno
3. Confirme a exclusão na mensagem apresentada

---

## 6. Gestão de Escolas

### 6.1 Listar Escolas
Acesse o dashboard e clique em **Escolas** para visualizar todas as escolas cadastradas.

![Escolas](./assets/imgs/tela-admin-escolas.png)

**Informações exibidas:**
- Nome da escola
- Endereço
- Quantidade de alunos vinculados
- Ações (editar, excluir)

### 6.2 Cadastrar Nova Escola
1. Acesse o dashboard e clique em **Escolas**
2. Clique em **"Nova Escola"**
3. Preencha os campos:

![Nova Escola](./assets/imgs/tela-cadastrar-escola.png)

- **Nome**: Nome da escola (obrigatório)
- **Endereço**: Endereço completo
4. Clique em **"Salvar"**

### 6.3 Editar Escola
1. Acesse o dashboard e clique em **Escolas**
2. Clique no botão de edição ao lado da escola desejada
3. Altere os dados necessários
4. Clique em **"Salvar"**

### 6.4 Excluir Escola
1. Acesse o dashboard e clique em **Escolas**
2. Clique no botão de exclusão ao lado da escola
3. Confirme a exclusão

**Nota**: Só será possível excluir escolas que não tenham alunos vinculados.

### 6.5 Relatório de Escolas
Na tela de Escolas, clique em **Relatório** para visualizar um relatório com todas as escolas e seus respectivos alunos vinculados.

![Rel Escolas](./assets/imgs/tela-relatorio-escolas.png)

---

## 7. Gestão de Instrumentos

### 7.1 Listar Instrumentos
Clique em **Instrumentos** no menu superior para visualizar todos os instrumentos cadastrados.

![Instrumentos](./assets/imgs/tela-admin-instrumentos.png)

**Informações exibidas:**
- Nome do instrumento
- Tipo
- Naipe
- Status (ativo/inativo)
- Ações (editar, ativar/inativar)

### 7.2 Cadastrar Novo Instrumento
1. Clique em **Instrumentos** no menu superior
2. Clique em **"Novo Instrumento"**
3. Preencha os campos:

![Novo Instrumento](./assets/imgs/tela-cadastrar-instrumento.png)

- **Nome**: Nome do instrumento (obrigatório)
- **Tipo**: Categoria do instrumento
- **Naipe**: Seção da banda
- **Descrição**: Descrição adicional
4. Clique em **"Salvar"**

### 7.3 Editar Instrumento
1. Clique em **Instrumentos** no menu superior
2. Clique no botão de edição ao lado do instrumento desejado
3. Altere os dados necessários
4. Clique em **"Salvar"**

### 7.4 Ativar/Desativar Instrumento
1. Clique em **Instrumentos** no menu superior
2. Clique no botão de alternância ao lado do instrumento
3. O instrumento será ativado ou inativado

---

## 8. Tipos e Naipes

### 8.1 Tipos de Instrumento
Gerencie as categorias de instrumentos (ex: cordas, sopros, percussão).

![Tipos](./assets/imgs/tela-admin-tipos.png)

### 8.2 Naipes
Gerencie as seções da banda (ex: metais, madeiras, percussão).

![Naipes](./assets/imgs/tela-admin-naipes.png)

---

## 9. Presença, Ensaios e Eventos

### 9.1 Criar um Ensaio

1. No menu superior, clique em **Presença**
2. Clique em **Novo ensaio**
3. Informe:
  - título;
  - data;
  - horário;
  - local;
  - observações;
  - status.
4. Clique em **Criar e registrar chamada**

Após o cadastro, o sistema abrirá automaticamente a folha de chamada.

### 9.2 Registrar Presença em um Ensaio

Na folha de chamada, os integrantes ativos são agrupados pelo instrumento atualmente associado. Para cada integrante, marque uma situação:

- **Presente**;
- **Ausente**;
- **Justificado**.

Clique em **Salvar presença** para registrar ou atualizar a chamada. O usuário responsável e o horário do registro são armazenados para auditoria.

O botão **Imprimir** gera uma versão adequada para impressão e conferência durante o ensaio.

### 9.3 Editar ou Cancelar um Ensaio

Na tela **Presença**, use:

- **Editar** para alterar título, data, horário, local, observações ou status;
- **Cancelar** para alterar o status para cancelado.

O cancelamento não exclui o ensaio nem suas presenças, preservando o histórico administrativo.

### 9.4 Criar um Evento ou Apresentação

1. No menu superior, clique em **Eventos**
2. Clique em **Novo evento**
3. Informe:
  - nome do evento;
  - data;
  - cidade ou local;
  - status;
  - responsável;
  - telefone.
4. Clique em **Criar e registrar chamada**

Os status disponíveis são **A confirmar**, **Confirmado** e **Cancelado**.

### 9.5 Registrar Presença em Evento

Na listagem de **Eventos**, clique em **Chamada**. A folha funciona da mesma forma que a folha de ensaio, agrupando integrantes por instrumento e permitindo marcar presença, ausência ou justificativa.

### 9.6 Editar ou Cancelar um Evento

Na tela **Eventos**, use **Editar** para atualizar os dados do evento. Use **Cancelar** quando a apresentação não for realizada.

O cancelamento é lógico: os dados do evento e os registros de presença permanecem disponíveis para consulta.

### 9.7 Consultar Histórico e Frequência

1. Acesse **Presença**
2. Clique em **Histórico**
3. Selecione um integrante ou mantenha **Todos os integrantes**
4. Clique em **Filtrar histórico**

O sistema exibirá as chamadas, datas, atividades, locais, integrantes e situações. Quando um integrante for selecionado, será exibido o percentual de frequência calculado com base nos registros disponíveis.

Use **Imprimir** para gerar uma cópia do histórico.

---

## 10. Relatórios

### 10.1 Relatório Geral de Alunos
Acesse para visualizar todos os alunos cadastrados com filtros por:
- Escola
- Status
- Função na banda

![Rel alunos](./assets/imgs/tela-relatorio-geral.png)

### 10.2 Relatório Individual de Aluno
Acesse através da visualização de cada aluno para obter um relatório detalhado.

![Rel Aluno](./assets/imgs/tela-relatorio-aluno.png)

### 10.3 Relatório de Escolas
Acesse para visualizar todas as escolas e seus alunos vinculados.

![Rel Escolas](./assets/imgs/tela-relatorio-escolas.png)

---

## 11. Backup do Sistema

### 11.1 Criar Backup
1. No menu do usuário, no canto superior direito, selecione **Backup do Banco**
2. Clique em **"Criar Backup Agora"**
3. O sistema gerará uma cópia do banco de dados

![Backup](./assets/imgs/tela-admin-backup.png)

### 11.2 Restaurar Backup
1. No menu do usuário, selecione **Backup do Banco**
2. Selecione o backup desejado da lista
3. Clique em **"Restaurar"**
4. Confirme a operação

**Aviso**: A restauração substituirá todos os dados atuais. Faça um backup antes se necessário.

### 11.3 Excluir Backup
1. No menu do usuário, selecione **Backup do Banco**
2. Selecione o backup desejado
3. Clique em **"Excluir"**

---

## 12. Alteração de Senha

### 12.1 Alterar Própria Senha
1. Clique no seu nome de usuário no menu superior
2. Selecione **"Alterar Senha"**
3. Preencha:

![Alt. Senha](./assets/imgs/tela-alterar-senha.png)

- Senha atual
- Nova senha
- Confirme a nova senha
1. Clique em **"Salvar"**

---

## 13. Logout

### 13.1 Sair do Sistema
1. Clique no seu nome de usuário no menu superior
2. Selecione **"Sair"**

---

## 14. Perfis de Usuário

### 14.1 Administrador
Acesso completo a todas as funcionalidades:
- Gestão de usuários
- Gestão de alunos
- Gestão de escolas
- Gestão de instrumentos
- Relatórios
- Backup
- Configurações do sistema

### 14.2 Profissional
Acesso às funcionalidades de gestão:
- Gestão de alunos
- Gestão de escolas
- Gestão de instrumentos
- Relatórios

### 14.3 Usuário Comum
Acesso básico:
- Visualização de dados
- Relatórios

---

## 15. Dicas de Segurança

1. **Senhas**: Use senhas fortes com no mínimo 6 caracteres
2. **Logout**: Sempre saia do sistema após o uso
3. **Compartilhamento**: Não compartilhe suas credenciais
4. **Bloqueio**: O sistema bloqueia o usuário após 3 tentativas de login incorretas por 12 horas
### 15.1 Boas Práticas de Segurança

- Utilize senhas com:
  - mínimo de 8 caracteres
  - letras maiúsculas e minúsculas
  - números e símbolos

- Não compartilhe suas credenciais

- Evite acessar o sistema em redes públicas

- Sempre realize logout após o uso

- Altere sua senha periodicamente
---

## 16. Solução de Problemas

### 16.1 Esqueci minha senha
Entre em contato com o administrador do sistema para resetar sua senha.

### 16.2 Usuário bloqueado
O sistema bloqueia automaticamente após 3 tentativas incorretas. Aguarde 12 horas ou entre em contato com o administrador.

### 16.3 Não consigo acessar uma funcionalidade
Verifique se seu perfil de usuário tem permissão para acessar aquela funcionalidade. Entre em contato com o administrador se necessário.

### 16.4 Dados não aparecem
Verifique se você tem permissão de acesso. Alguns dados podem estar filtrados por perfil.

---
## 17. Problemas Comuns e Soluções

### ❌ Não consigo salvar o aluno
- Verifique campos obrigatórios
- Confirme autorização de menor (se aplicável)

---

### ❌ CEP não preenche automaticamente
- Verifique conexão com internet
- Preencha manualmente os dados

---

### ❌ Usuário bloqueado
- O sistema bloqueia após 3 tentativas
- Aguarde 12 horas ou solicite desbloqueio

---

### ❌ Dados não aparecem
- Verifique filtros ativos
- Confirme permissões do usuário

---

### ❌ Não consigo excluir escola
- Pode haver alunos vinculados
- Remova vínculos antes de excluir

---

## 18. Contato e Suporte

Para dúvidas ou problemas técnicos, entre em contato com o administrador do sistema.

### 18.1 Identificação da versão

A versão atual da aplicação é exibida na tela de login, na área de créditos e nas configurações administrativas.

O formato possui três partes, como em `1.4.8`:

- primeira parte: versão principal;
- segunda parte: atualização ou etapa funcional;
- terceira parte: contagem incremental de alterações. Ao passar de `99`, o segundo componente é incrementado; se ele também passar de `99`, o primeiro componente é incrementado.

Essa identificação é mantida pela equipe responsável pelo desenvolvimento. O usuário não deve alterar a versão pelas configurações do sistema.

---

**Versão do Manual**: 1.1
**Sistema**: Sistema BMCM - Banda Marcial Municipal de Marília
**Data de Criação**: 2026

---
