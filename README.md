# Sistema de Gestão de Integrantes da Banda Marcial Municipal de Marília - SP

<div align="center">

![Logo UNIVESP](./assets/imgs/logo-univesp.png)

[![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat\&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-blue?style=flat)](https://flask.palletsprojects.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5-purple?style=flat)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

</div>

---

## Sumário

- [Sistema de Gestão de Integrantes da Banda Marcial Municipal de Marília - SP](#sistema-de-gestão-de-integrantes-da-banda-marcial-municipal-de-marília---sp)
  - [Sumário](#sumário)
- [Nome do Projeto](#nome-do-projeto)
- [Contexto e Justificativa](#contexto-e-justificativa)
- [Evolução do Projeto - PI I e PI II](#evolução-do-projeto---pi-i-e-pi-ii)
- [Objetivos](#objetivos)
  - [Objetivo Geral](#objetivo-geral)
  - [Objetivos Específicos](#objetivos-específicos)
- [Escopo Funcional](#escopo-funcional)
  - [Funcionalidades Implementadas](#funcionalidades-implementadas)
    - [Autenticação e contas](#autenticação-e-contas)
    - [Gestão de integrantes](#gestão-de-integrantes)
    - [Gestão de escolas](#gestão-de-escolas)
    - [Gestão de instrumentos](#gestão-de-instrumentos)
    - [Relatórios](#relatórios)
    - [Endereço por CEP](#endereço-por-cep)
- [Funcionalidades em Desenvolvimento](#funcionalidades-em-desenvolvimento)
  - [Controle de presença](#controle-de-presença)
  - [Ensaios](#ensaios)
  - [Eventos e apresentações](#eventos-e-apresentações)
- [Integrações Planejadas](#integrações-planejadas)
  - [Google Drive](#google-drive)
  - [Google Calendar](#google-calendar)
  - [Gmail](#gmail)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Arquitetura e Estrutura do Projeto](#arquitetura-e-estrutura-do-projeto)
- [Modelo de Dados](#modelo-de-dados)
- [Regras de Negócio Relevantes](#regras-de-negócio-relevantes)
  - [Acesso](#acesso)
  - [Bloqueio de login](#bloqueio-de-login)
  - [Dados de integrantes](#dados-de-integrantes)
  - [Documento](#documento)
  - [Consentimento de imagem de menor](#consentimento-de-imagem-de-menor)
- [Acessibilidade e Experiência do Usuário](#acessibilidade-e-experiência-do-usuário)
- [Segurança e Privacidade](#segurança-e-privacidade)
- [APIs e Serviços Externos](#apis-e-serviços-externos)
- [Computação em Nuvem](#computação-em-nuvem)
- [Instalação e Configuração](#instalação-e-configuração)
  - [Pré-requisitos](#pré-requisitos)
  - [Passos](#passos)
    - [Windows - PowerShell](#windows---powershell)
    - [Windows - CMD](#windows---cmd)
    - [Linux/Mac](#linuxmac)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
    - [Windows - PowerShell](#windows---powershell-1)
    - [Windows - CMD](#windows---cmd-1)
    - [Linux/Mac](#linuxmac-1)
- [Execução do Sistema](#execução-do-sistema)
- [Credencial Inicial](#credencial-inicial)
- [Manual do Usuário](#manual-do-usuário)
- [Testes Automatizados](#testes-automatizados)
    - [Windows](#windows)
    - [Linux/Mac](#linuxmac-2)
- [Controle de Versão](#controle-de-versão)
- [Evidências de Interface](#evidências-de-interface)
- [Integrantes](#integrantes)
- [Facilitadora UNIVESP](#facilitadora-univesp)
- [Licença](#licença)
- [Bibliografia](#bibliografia)
  - [Documentos institucionais UNIVESP](#documentos-institucionais-univesp)
  - [Metodologia e desenvolvimento de software](#metodologia-e-desenvolvimento-de-software)
  - [Desenvolvimento Web](#desenvolvimento-web)
  - [APIs e serviços externos](#apis-e-serviços-externos-1)
- [Status do Projeto](#status-do-projeto)
    - [Principais objetivos da evolução](#principais-objetivos-da-evolução)
  - [Princípio de evolução](#princípio-de-evolução)

---

# Nome do Projeto

**Sistema de Gestão de Integrantes da Banda Marcial Municipal de Marília - SP**

Sistema web desenvolvido para apoiar a gestão administrativa e operacional da Banda Marcial Municipal de Marília - SP.

O projeto foi desenvolvido inicialmente no contexto do **Projeto Integrador I (PI I) da UNIVESP** e encontra-se em processo de evolução no **Projeto Integrador II (PI II)**.

A proposta do PI II é dar continuidade ao sistema existente, preservando suas funcionalidades e arquitetura sempre que tecnicamente adequado, incorporando novos recursos relacionados à gestão de integrantes, presença, ensaios, eventos, comunicação, acessibilidade, integração por APIs e utilização de serviços em nuvem.

---

# Contexto e Justificativa

A gestão de integrantes de uma banda marcial envolve informações cadastrais, escolares, familiares, instrumentos, uniformes, ensaios, apresentações, eventos e registros históricos.

Quando essas informações são mantidas de forma manual ou distribuídas em diferentes arquivos e sistemas, podem ocorrer:

* retrabalho administrativo;
* inconsistências cadastrais;
* dificuldade de atualização das informações;
* perda de histórico;
* dificuldade na elaboração de relatórios;
* dificuldade de acompanhamento da frequência;
* problemas de comunicação entre administração e integrantes.

O sistema BMCM foi concebido para centralizar essas informações em uma aplicação web, proporcionando maior organização, padronização e rastreabilidade.

A evolução do projeto no PI II busca ampliar essa proposta, transformando o sistema em uma ferramenta de apoio mais abrangente à gestão cotidiana da banda.

---

# Evolução do Projeto - PI I e PI II

O desenvolvimento do BMCM é tratado como um processo contínuo.

O **PI I** concentrou-se principalmente na construção da estrutura inicial da aplicação, incluindo:

* autenticação;
* gerenciamento de usuários;
* cadastro de integrantes;
* cadastro de escolas;
* cadastro de instrumentos;
* banco de dados relacional;
* relatórios;
* regras de negócio;
* segurança básica;
* validações;
* interface web responsiva.

O **PI II** não tem como objetivo reconstruir o sistema.

A proposta é **evoluir a aplicação existente**, acrescentando funcionalidades que atendam às necessidades atuais da banda e aos requisitos acadêmicos do novo projeto.

Entre os principais eixos de evolução estão:

* controle manual de presença;
* gestão de ensaios;
* gestão de eventos e apresentações;
* integração com Google Calendar;
* utilização do Google Drive para backup e armazenamento em nuvem;
* integração com Gmail para comunicação;
* utilização de APIs externas;
* aplicação prática do conceito de computação em nuvem;
* melhoria da acessibilidade;
* aprimoramento da experiência do usuário;
* ampliação dos testes automatizados;
* manutenção da segurança e da privacidade dos dados.

A evolução será realizada de forma incremental, preservando funcionalidades existentes sempre que possível.

## Atualizações realizadas no PI II

As seguintes melhorias já foram incorporadas ao sistema existente:

* criação de ambiente virtual em `venv/` e organização das dependências;
* inclusão do `pytest` na lista de dependências de desenvolvimento;
* proteção CSRF para requisições `POST` e formulários;
* correção de compatibilidade com SQLAlchemy 2 nas rotinas de manutenção;
* proteção dos caminhos de restauração e exclusão de backups;
* uso de chave secreta configurável por variável de ambiente;
* associação de instrumentos aos integrantes, com histórico de empréstimo e devolução;
* exibição do instrumento associado nas listagens e relatórios;
* criação de ensaios com data, horário, local, observações e status;
* criação e gerenciamento de eventos e apresentações;
* folha de chamada agrupada pelo instrumento do integrante;
* marcação de presença, ausência e justificativa;
* histórico de presença e cálculo de frequência;
* impressão da folha de chamada e do histórico;
* preservação do histórico ao editar ou cancelar ensaios e eventos;
* migrações incrementais para adequar bancos existentes às novas tabelas e colunas;
* correção dos relacionamentos duplicados entre eventos e autorizações de viagem.

As integrações com Google Drive, Google Calendar, Gmail e o módulo externo de WhatsApp ainda fazem parte das próximas etapas do PI II.

## Controle de versão da aplicação

O sistema utiliza uma versão de três partes no formato `principal.atualização.contagem`.

Exemplo:

```text
1.4.6
```

Nesse formato:

* `1`: versão principal da aplicação;
* `4`: etapa ou atualização funcional;
* `6`: quantidade de alterações contabilizadas no dia.

A versão oficial fica centralizada em `config.py`, nas constantes `APP_VERSION_MAJOR`, `APP_VERSION_UPDATE` e `APP_VERSION_DAILY_COUNT`. Ao criar uma nova rotina, formulário ou correção, o responsável pelo desenvolvimento deve atualizar a contagem final. Ao iniciar uma nova etapa funcional, o segundo componente deve ser incrementado; mudanças estruturais maiores podem incrementar o primeiro.

A versão é exibida no login, na área de créditos e nas configurações administrativas. A contagem representa o controle de alterações do desenvolvimento e não é alterada automaticamente pelo uso do sistema em produção.

---

# Objetivos

## Objetivo Geral

Desenvolver e evoluir uma aplicação web para apoio à gestão administrativa e operacional da Banda Marcial Municipal de Marília - SP, permitindo o gerenciamento de integrantes, informações cadastrais, presença, ensaios, eventos e comunicação, utilizando banco de dados, APIs, serviços em nuvem, recursos de acessibilidade e boas práticas de desenvolvimento de software.

## Objetivos Específicos

* Implementar autenticação e controle de acesso por perfil.
* Estruturar e manter banco de dados relacional para as entidades da banda.
* Disponibilizar operações de cadastro, consulta, atualização e gerenciamento das principais entidades.
* Preservar o histórico dos integrantes por meio de inativação quando aplicável.
* Implementar controle manual de presença.
* Permitir o acompanhamento histórico da frequência dos integrantes.
* Gerenciar ensaios, eventos e apresentações.
* Integrar o sistema a serviços externos por meio de APIs.
* Utilizar serviços Google como parte da integração com recursos de nuvem.
* Utilizar o Google Drive para backup e armazenamento de arquivos relacionados ao sistema.
* Utilizar o Google Calendar para apoio ao gerenciamento de ensaios e eventos.
* Utilizar o Gmail como recurso de apoio à comunicação.
* Aprimorar a acessibilidade e a experiência de uso.
* Implementar e ampliar testes automatizados.
* Aplicar boas práticas de segurança e proteção de dados.
* Utilizar Git e GitHub para controle de versão e acompanhamento do desenvolvimento.

---

# Escopo Funcional

## Funcionalidades Implementadas

### Autenticação e contas

* Login de usuários.
* Bloqueio temporário após tentativas inválidas.
* Troca obrigatória de senha no primeiro acesso do administrador padrão.
* Gestão de usuários.
* Criação de usuários.
* Edição de usuários.
* Ativação e inativação de usuários.
* Reset de senha.
* Controle de acesso conforme perfil.

### Gestão de integrantes

* Cadastro de integrantes.
* Edição de integrantes.
* Inativação de integrantes.
* Listagem com filtros.
* Dados pessoais.
* Dados de contato.
* Endereço.
* Responsáveis.
* Vinculação escolar.
* Upload de foto.
* Máscara de documentos no formulário.

### Gestão de escolas

* Cadastro.
* Edição.
* Exclusão.
* Listagem.
* Relatórios por escola.

### Gestão de instrumentos

* Cadastro.
* Edição.
* Ativação e inativação.
* Exclusão.
* Estado do instrumento.
* Patrimônio.
* Marca.
* Modelo.
* Observações.

### Relatórios

* Relatório geral de integrantes.
* Relatório individual de integrante.
* Relatório de integrantes por escola.

### Endereço por CEP

* Busca local em base de logradouros.
* Fallback para ViaCEP quando o endereço não é encontrado localmente.

---

# Funcionalidades em Desenvolvimento

As seguintes funcionalidades fazem parte da evolução prevista para o PI II.

## Controle de presença

Será desenvolvido um sistema de controle **manual** de presença dos integrantes.

O sistema deverá permitir:

* registrar presença;
* registrar ausência;
* relacionar a presença a um ensaio ou evento;
* consultar histórico;
* visualizar frequência individual;
* visualizar informações gerais de frequência;
* realizar consultas administrativas;
* gerar futuramente relatórios relacionados à frequência.

O controle manual foi escolhido para manter o sistema simples, acessível e alinhado às necessidades atuais da banda.

## Ensaios

O sistema deverá permitir o gerenciamento dos ensaios da banda, incluindo informações como:

* data;
* horário;
* local;
* observações;
* situação do ensaio;
* integrantes relacionados;
* registro de presença.

## Eventos e apresentações

O sistema deverá permitir registrar eventos e apresentações, incluindo informações como:

* data;
* horário;
* local;
* descrição;
* finalidade;
* observações;
* participantes;
* informações de contato quando necessário.

Esses registros poderão posteriormente ser integrados ao Google Calendar.

---

# Integrações Planejadas

O PI II prevê a integração com três serviços principais do ecossistema Google.

## Google Drive

O Google Drive será utilizado como serviço de armazenamento em nuvem para:

* backup do banco de dados;
* armazenamento de arquivos relevantes;
* armazenamento de relatórios quando aplicável;
* apoio à recuperação de informações.

A implementação deverá utilizar autenticação adequada e manter tokens e credenciais fora do código-fonte.

## Google Calendar

O Google Calendar será utilizado para apoiar o gerenciamento de:

* ensaios;
* eventos;
* apresentações;
* compromissos da banda.

A integração deverá permitir que informações relevantes do sistema sejam utilizadas no calendário externo, evitando a necessidade de manter manualmente os mesmos compromissos em diferentes locais.

## Gmail

O Gmail será utilizado como recurso de apoio à comunicação da banda.

Entre as possibilidades estão:

* envio de avisos;
* comunicação sobre ensaios;
* comunicação sobre eventos;
* notificações administrativas;
* comunicação com integrantes;
* comunicação com responsáveis, quando aplicável;
* comunicação institucional com organizadores de eventos;
* contato com outras prefeituras e instituições para apresentações.

A integração não tem como objetivo criar um novo sistema de e-mail, mas utilizar o Gmail como serviço externo integrado ao BMCM.

---

# Tecnologias Utilizadas

![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat\&logo=python)

![Flask](https://img.shields.io/badge/Flask-3.1.3-blue?style=flat)

![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-orange)

![SQLite](https://img.shields.io/badge/SQLite-3-silver)

![Bootstrap](https://img.shields.io/badge/Bootstrap-5-purple?style=flat)

![Pytest](https://img.shields.io/badge/Pytest-8.x-blueviolet)

Principais tecnologias e bibliotecas utilizadas:

* Python 3.12+
* Flask 3.1.3
* Flask-Login
* Flask-SQLAlchemy
* SQLAlchemy
* SQLite
* Bootstrap 5
* HTML5
* CSS3
* JavaScript
* Jinja2
* Requests
* BeautifulSoup4
* Pytest
* Waitress
* Git
* GitHub

Integrações externas previstas:

* Google Drive API
* Google Calendar API
* Gmail API
* ViaCEP

---

# Arquitetura e Estrutura do Projeto

O sistema utiliza uma arquitetura em camadas leves baseada no framework Flask.

A arquitetura existente deve ser preservada sempre que atender aos requisitos do projeto.

A migração para outro framework não faz parte do escopo atual.

Principais componentes:

* `app/__init__.py`: factory da aplicação, inicialização do banco, login manager e seed inicial.
* `app/auth.py`: rotas de autenticação.
* `app/routes.py`: rotas de domínio.
* `app/models.py`: modelos SQLAlchemy.
* `app/utils.py`: funções auxiliares, normalização, seed e regras relacionadas a consentimentos.
* `templates/`: páginas HTML utilizando Jinja2 e Bootstrap.
* `static/`: arquivos estáticos, CSS, imagens e uploads.
* `tests/`: testes automatizados.
* `run.py`: ponto de entrada para execução local.
* `config.py`: configurações da aplicação.

Estrutura resumida:

```text
.
├── app/
│   ├── __init__.py
│   ├── auth.py
│   ├── models.py
│   ├── routes.py
│   └── utils.py
├── templates/
├── static/
├── tests/
│   └── test_aluno_fluxo.py
├── assets/
│   └── imgs/
├── config.py
├── run.py
└── requirements.txt
```

À medida que as integrações do PI II forem implementadas, novos módulos poderão ser adicionados para manter separadas as responsabilidades relacionadas a:

* presença;
* eventos;
* calendário;
* backup;
* comunicação;
* APIs externas.

---

# Modelo de Dados

Banco principal:

`SQLite (instance/database.db)`

Entidades atualmente mapeadas:

* `User`
* `Aluno`
* `Responsavel`
* `Escola`
* `AlunoEscola`
* `Instrumento`
* `AlunoInstrumento`
* `Uniforme`
* `Presenca`
* `Cidade`
* `Logradouro`
* `AutorizacaoFotoMenor`
* `AutorizacaoViagem`
* `Evento`

Tabelas de referência:

* `Naipe`
* `TipoInstrumento`
* `FuncaoBanda`

A evolução do PI II poderá acrescentar ou ajustar entidades relacionadas a:

* ensaios;
* eventos;
* presença;
* integração com serviços externos;
* configurações;
* registros de comunicação;
* logs.

As alterações no modelo de dados deverão preservar a compatibilidade com os dados existentes sempre que possível.

Observações:

* `Aluno.cin_rg` é único.
* O sistema cria automaticamente dados iniciais de tipos, naipes e funções.
* Há importação automática de municípios/logradouros quando o arquivo `municipios.sql` está presente.

---

# Regras de Negócio Relevantes

## Acesso

* Rotas administrativas exigem usuário autenticado.
* Operações administrativas podem exigir perfil de administrador.

## Bloqueio de login

Após três tentativas inválidas de autenticação, o usuário é bloqueado temporariamente por 12 horas.

## Dados de integrantes

* Integrantes podem ser inativados para preservar histórico.
* Campos textuais são normalizados em pontos específicos.
* Telefone é normalizado para padrão nacional.

## Documento

* O campo `cin_rg` aceita formato de CIN/RG e CPF no frontend.
* O backend persiste o valor informado no campo `cin_rg`.

## Consentimento de imagem de menor

* Para menores de 18 anos, conforme a regra adotada pelo sistema, é exigida autorização quando houver utilização de fotografia.
* O consentimento inclui aceite e assinatura digital desenhada no navegador.

---

# Acessibilidade e Experiência do Usuário

A acessibilidade e a experiência do usuário fazem parte da evolução do sistema.

Entre os recursos e melhorias considerados estão:

* interface responsiva;
* suporte a diferentes tamanhos de tela;
* tema claro;
* tema escuro;
* personalização visual;
* contraste adequado;
* navegação por teclado;
* foco visual;
* tamanho ajustável de caracteres;
* elementos de formulário identificados adequadamente;
* mensagens de erro compreensíveis;
* organização consistente dos menus;
* atalhos de teclado quando aplicáveis.

A personalização visual deverá respeitar critérios de legibilidade e contraste.

A possibilidade de personalizar cores não deve resultar em combinações que dificultem a utilização do sistema.

O objetivo é permitir que o sistema seja utilizado por pessoas com diferentes níveis de familiaridade com tecnologia.

---

# Segurança e Privacidade

A segurança dos dados é uma preocupação permanente do projeto.

Medidas implementadas ou consideradas:

* senhas armazenadas utilizando hash seguro;
* autenticação utilizando Flask-Login;
* controle de autorização;
* bloqueio temporário após tentativas inválidas;
* validação de dados;
* proteção das rotas administrativas;
* preservação histórica por inativação;
* consentimento para utilização de imagem de menores;
* proteção de credenciais de serviços externos;
* utilização de variáveis de ambiente para informações sensíveis;
* não armazenamento de tokens e chaves de API no GitHub.

Para utilização em ambiente de produção, recomenda-se:

* `SECRET_KEY` forte;
* HTTPS;
* servidor WSGI;
* proxy reverso;
* política adequada de backup;
* controle de acesso ao servidor;
* atualização periódica das dependências.

---

# APIs e Serviços Externos

A utilização de APIs constitui uma das etapas importantes da evolução do projeto.

O sistema deverá demonstrar a capacidade de integração com serviços externos por meio de interfaces de programação de aplicações.

As principais integrações previstas são:

| Serviço             | Finalidade                       |
| ------------------- | -------------------------------- |
| Google Drive API    | Backup e armazenamento em nuvem  |
| Google Calendar API | Ensaios, eventos e apresentações |
| Gmail API           | Comunicação e notificações       |
| ViaCEP              | Consulta de endereços            |

Cada integração deverá possuir:

* autenticação adequada;
* tratamento de erros;
* tratamento de indisponibilidade;
* controle das credenciais;
* documentação;
* testes quando tecnicamente possível.

---

# Computação em Nuvem

A utilização de serviços externos do Google permitirá demonstrar, na prática, conceitos relacionados à computação em nuvem.

O sistema poderá utilizar recursos remotos para:

* armazenamento;
* backup;
* gerenciamento de calendário;
* comunicação;
* integração entre diferentes serviços.

O conceito adotado é de uma aplicação web que combina recursos locais, banco de dados e serviços disponibilizados por provedores externos.

O Google Drive, Google Calendar e Gmail não são considerados apenas funcionalidades isoladas, mas componentes de uma arquitetura integrada por APIs.

---

# Instalação e Configuração

## Pré-requisitos

* Python 3.12 ou superior;
* `venv` habilitado;
* Git, quando o projeto for obtido por meio do repositório.

## Passos

```bash
# Clonar o repositório
git clone <URL_DO_REPOSITORIO>

# Acessar o diretório
cd sistemaBMCM

# Criar ambiente virtual
python -m venv venv
```

### Windows - PowerShell

```powershell
.\venv\Scripts\Activate
```

### Windows - CMD

```cmd
venv\Scripts\activate.bat
```

### Linux/Mac

```bash
source venv/bin/activate
```

Depois:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

O projeto utiliza **Waitress** como servidor WSGI.

---

# Variáveis de Ambiente

As seguintes variáveis podem ser utilizadas:

* `SECRET_KEY`: chave utilizada para proteção das sessões Flask.
* `DATABASE_URL`: URL de conexão com o banco de dados.

Exemplo:

### Windows - PowerShell

```powershell
$env:SECRET_KEY="sua_chave_forte"
$env:DATABASE_URL="sqlite:///instance/database.db"
```

### Windows - CMD

```cmd
set SECRET_KEY=sua_chave_forte
set DATABASE_URL=sqlite:///instance/database.db
```

### Linux/Mac

```bash
export SECRET_KEY="sua_chave_forte"
export DATABASE_URL="sqlite:///instance/database.db"
```

As futuras integrações com serviços Google deverão utilizar variáveis de ambiente ou mecanismos seguros de armazenamento para suas credenciais.

**Credenciais, tokens e chaves de API não devem ser versionados no GitHub.**

---

# Execução do Sistema

Com o ambiente virtual ativo:

```bash
python run.py
```

Por padrão, o sistema cria tabelas e dados iniciais automaticamente durante a inicialização.

---

# Credencial Inicial

Quando não existe usuário administrador no banco, o sistema cria inicialmente:

```text
Usuário: admin
Senha: 123456
```

No primeiro acesso, a alteração da senha é obrigatória.

> **Importante:** essa credencial deve ser considerada exclusivamente uma credencial inicial de desenvolvimento. Em ambiente real, deve ser substituída imediatamente por uma senha forte e exclusiva.

---

# Manual do Usuário

Para instruções detalhadas de utilização do sistema:

📄 [Manual do Usuário](./MANUAL_USUARIO.md)

O manual deverá ser atualizado à medida que novas funcionalidades do PI II forem incorporadas.

---

# Testes Automatizados

A aplicação possui o **Pytest** configurado como ferramenta de testes. A suíte automatizada ainda está em expansão e deve acompanhar a implementação das funcionalidades do PI II.

Execução:

### Windows

```bash
python -m pytest -q
```

### Linux/Mac

```bash
./venv/bin/python -m pytest -q
```

Durante o PI II, a cobertura de testes deverá ser ampliada para funcionalidades críticas, especialmente:

* autenticação;
* autorização;
* presença;
* eventos;
* ensaios;
* integrações com APIs;
* validações;
* operações de banco de dados.

---

# Controle de Versão

O desenvolvimento utiliza **Git e GitHub** para controle de versão.

O controle de versão permite:

* acompanhar a evolução do projeto;
* identificar alterações;
* recuperar versões anteriores;
* trabalhar de maneira colaborativa;
* documentar a evolução do sistema;
* apoiar a realização do Projeto Integrador.

Recomenda-se utilizar commits objetivos e descritivos.

Arquivos contendo senhas, tokens, chaves de API ou outras informações sensíveis não devem ser adicionados ao repositório.

---

# Evidências de Interface

Imagens presentes no repositório:

| Tela                   | Arquivo                                      | Descrição                                  |
| ---------------------- | -------------------------------------------- | ------------------------------------------ |
| Login                  | `assets/imgs/Login.png`                      | Página de autenticação                     |
| Bloqueio               | `assets/imgs/bloq.png`                       | Tela de bloqueio após tentativas inválidas |
| Dashboard              | `assets/imgs/Dash.png`                       | Painel principal                           |
| Menu                   | `assets/imgs/tela-menu.png`                  | Menu principal                             |
| Usuários               | `assets/imgs/tela-admin-usuarios.png`        | Administração de usuários                  |
| Novo usuário           | `assets/imgs/tela-criar-usuario.png`         | Cadastro de usuário                        |
| Integrantes            | `assets/imgs/tela-admin-alunos.png`          | Administração de integrantes               |
| Cadastro de integrante | `assets/imgs/tela-cadastrar-aluno.png`       | Cadastro de integrante                     |
| Relatório individual   | `assets/imgs/tela-relatorio-aluno.png`       | Relatório de integrante                    |
| Escolas                | `assets/imgs/tela-admin-escolas.png`         | Administração de escolas                   |
| Nova escola            | `assets/imgs/tela-cadastrar-escola.png`      | Cadastro de escola                         |
| Relatório de escolas   | `assets/imgs/tela-relatorio-escolas.png`     | Relatório por escola                       |
| Instrumentos           | `assets/imgs/tela-admin-instrumentos.png`    | Administração de instrumentos              |
| Novo instrumento       | `assets/imgs/tela-cadastrar-instrumento.png` | Cadastro de instrumento                    |
| Tipos                  | `assets/imgs/tela-admin-tipos.png`           | Tipos de instrumentos                      |
| Naipes                 | `assets/imgs/tela-admin-naipes.png`          | Naipes                                     |
| Backup                 | `assets/imgs/tela-admin-backup.png`          | Área relacionada ao backup                 |
| Alteração de senha     | `assets/imgs/tela-alterar-senha.png`         | Alteração de senha                         |

Exemplos:

![Tela de Login](./assets/imgs/Login.png)

![Tela de bloqueio](./assets/imgs/bloq.png)

![Dashboard](./assets/imgs/Dash.png)

![Menu](./assets/imgs/tela-menu.png)

---

# Integrantes

1. Adriano Guedes Ferraz
2. Alessandra da Silva Zanirato Garcia
3. Aparecido Fernandes de Souza
4. David Miguel Soares Junior
5. Fabiane Fernanda de Barros Ranke
6. Felipe Oldani dos Santos
7. Kelly Cristina Ferreira da Costa
8. Rafael Veranelli Scalzo Moraes
9. Renato de Abreu Mantovanelli

---

# Facilitadora UNIVESP

* David Miguel Soares Junior

---

# Licença

[![Licença](https://img.shields.io/badge/LICENCA-MIT-green)](LICENSE)

Este projeto está disponibilizado sob a licença MIT.

Consulte o arquivo [LICENSE](LICENSE) para obter os termos completos.

---

# Bibliografia

## Documentos institucionais UNIVESP

* UNIVESP. *Orientações para alunos de Projeto Integrador*. São Paulo: UNIVESP, 2023.
* UNIVESP. *Orientações para avaliação do Projeto Integrador*. São Paulo: UNIVESP, 2021.

## Metodologia e desenvolvimento de software

* SOMMERVILLE, I. *Engenharia de software*. 10. ed.
* PRESSMAN, R. S. *Engenharia de software: uma abordagem profissional*. 9. ed.
* LAUDON, K. C.; LAUDON, J. P. *Sistemas de informação gerenciais*.

## Desenvolvimento Web

* Flask Documentation.
* SQLAlchemy Documentation.
* Bootstrap Documentation.
* Python Documentation.
* SQLite Documentation.
* Pytest Documentation.

## APIs e serviços externos

* Google Developers Documentation.
* Google Drive API Documentation.
* Google Calendar API Documentation.
* Gmail API Documentation.
* ViaCEP Documentation.

---

# Status do Projeto

**PI I:** Base funcional implementada.

**PI II:** Evolução em desenvolvimento.

### Principais objetivos da evolução

* [x] Manutenção da aplicação web existente
* [x] Banco de dados relacional
* [x] Autenticação e controle de acesso
* [x] Gestão de integrantes
* [x] Gestão de escolas
* [x] Gestão de instrumentos
* [x] Relatórios
* [x] Controle de versão
* [x] Interface responsiva
* [x] Controle manual de presença
* [x] Gestão de ensaios
* [x] Gestão de eventos e apresentações
* [ ] Integração com Google Drive
* [ ] Integração com Google Calendar
* [ ] Integração com Gmail
* [ ] Ampliação dos testes automatizados
* [ ] Ampliação dos recursos de acessibilidade
* [ ] Documentação das integrações e serviços em nuvem
* [ ] Atualizador controlado de versões da aplicação

---

## Princípio de evolução

O BMCM deve ser tratado como um sistema real em evolução, e não como uma aplicação descartável desenvolvida exclusivamente para fins acadêmicos.

As novas funcionalidades devem seguir o princípio:

> **Necessidade real da banda + requisito acadêmico + simplicidade + segurança + manutenção futura.**

A evolução do projeto deverá preservar as funcionalidades existentes sempre que possível e evitar alterações estruturais que não apresentem benefício técnico ou acadêmico justificável.

Funcionalidades futuras, como RFID e automação de presença utilizando IoT, poderão ser desenvolvidas posteriormente, mas não fazem parte do escopo principal do PI II.
