# CONTEXTO E DIRETRIZES DO PROJETO — BMCM

## 1. Visão geral

O BMCM — Sistema de Gerenciamento da Banda Marcial Cidade de Marília — é uma aplicação web desenvolvida como Projeto Integrador (PI) da UNIVESP.

O sistema já possui uma base funcional desenvolvida em Python utilizando o framework Flask, banco de dados SQLite e interface web responsiva baseada em HTML, CSS, Bootstrap e JavaScript.

O objetivo desta nova etapa do projeto não é reconstruir o sistema do zero, nem substituir sua arquitetura sem necessidade.

O objetivo é **dar continuidade ao sistema existente**, evoluindo suas funcionalidades para atender simultaneamente:

1. às necessidades reais da Banda Marcial Cidade de Marília;
2. às novas exigências acadêmicas do Projeto Integrador;
3. aos conceitos de desenvolvimento web, banco de dados, APIs, computação em nuvem, acessibilidade, usabilidade, controle de versão e testes.

A regra fundamental do desenvolvimento é:

> **Preservar o que já funciona e evoluir a aplicação de forma incremental, organizada e tecnicamente justificável.**

---

# 2. Estado atual do sistema

O BMCM já possui ou possui em desenvolvimento os seguintes recursos:

* Aplicação web em Flask;
* Banco de dados;
* Sistema de autenticação;
* Login de usuários;
* Cadastro e gerenciamento de usuários;
* Controle de permissões;
* Painel administrativo;
* Dashboard;
* Cards informativos;
* Interface responsiva;
* JavaScript;
* Personalização visual;
* Tema claro e escuro;
* Personalização de cores da interface;
* Ajustes iniciais de acessibilidade e contraste;
* Estrutura preparada para acessibilidade;
* Controle de versão utilizando Git/GitHub;
* Estrutura de API;
* Sistema de gerenciamento relacionado à banda;
* Central de comunicações administrativa com públicos, anexos, histórico e consentimento externo auditável, validada por testes automatizados;
* Fluxo OAuth 2.0 do Google e envio de mensagens pelo Gmail;
* Persistência local do token OAuth;
* Controle manual de presença atualmente relacionado a ensaios e eventos;
* Calendário interno mensal do BMCM, agregando ensaios, eventos e atividades avulsas;
* Base para indicadores de presença e análise de frequência.

O OAuth solicita escopos para Gmail, Calendar e Drive. Gmail, sincronização unidirecional inicial do Calendar e upload/listagem de backups no Drive estão conectados a operações do sistema. Calendar e Drive foram validados com a conta Google configurada no ambiente.

Esses recursos devem ser considerados parte da evolução do projeto e não devem ser descartados ou reimplementados desnecessariamente.

---

# 3. Diretriz arquitetural

O projeto utiliza Flask e **não deve ser migrado para Django apenas por preferência tecnológica**.

Qualquer proposta de mudança estrutural deverá primeiro verificar:

* se existe exigência acadêmica explícita;
* se existe benefício técnico real;
* impacto sobre funcionalidades existentes;
* impacto sobre banco de dados;
* impacto sobre autenticação;
* impacto sobre segurança;
* impacto sobre o cronograma do PI.

Se Flask atender aos requisitos, deve permanecer como framework principal.

O sistema deve evoluir de forma incremental.

---

# 4. Escopo do PI II

O PI II deve ampliar o BMCM principalmente nas seguintes áreas:

## 4.1 Sistema de presença

Desenvolver um sistema de controle de presença **manual**, integrado ao cadastro dos integrantes da banda.

O sistema deverá permitir, conforme as regras definidas pelo projeto:

* registrar presença;
* registrar ausência;
* identificar o integrante;
* relacionar presença com a atividade correspondente, incluindo ensaio, evento, apresentação, treinamento ou outra atividade válida;
* consultar histórico;
* visualizar frequência;
* permitir consultas administrativas;
* possibilitar futuramente geração de relatórios.

O controle de presença manual é o escopo atual.

## 4.2 Modelo operacional de atividades, presença e passes

Esta seção registra regras de negócio da rotina da Banda Marcial Cidade de Marília. Ela deve ser considerada a referência principal para interpretar os conceitos de atividade, ensaio, presença e passe. Descrições mais antigas que limitem a presença somente a ensaios e eventos devem ser lidas em conjunto com estas regras.

### Atividades

O conceito de atividade é mais amplo que o de ensaio previamente agendado. Durante o período em que a Banda estiver efetivamente funcionando em determinado dia, um integrante pode comparecer e iniciar uma atividade de treinamento ou aperfeiçoamento sem que exista um compromisso previamente cadastrado.

Os horários de funcionamento mencionados em conversas são apenas referências contextuais, não requisitos do modelo. O sistema não deve criar horário semanal, expediente padrão ou validar atividades com base em horas de abertura. Horários de início e fim pertencem somente ao registro individual de uma atividade quando forem informados.

As atividades podem incluir:

* ensaio oficial;
* evento ou apresentação;
* treinamento ou atividade individual;
* atividade orientada por responsável;
* outra atividade válida da Banda.

Sempre que uma atividade gerar controle de frequência, o registro deverá permitir identificar, quando disponível, o integrante, a data, o horário, o tipo de atividade, a área ou finalidade, o responsável e a relação com ensaio ou evento previamente cadastrado.

A implementação atual utiliza a entidade `Atividade`, com um campo de tipo, para atividades avulsas. Os tipos disponíveis nesse fluxo são `TREINAMENTO`, `APRESENTACAO` e `OUTRA`. Ensaios e eventos existentes permanecem compatíveis em suas entidades próprias enquanto a evolução do modelo não for concluída.

### Presença

Presença representa o comparecimento efetivo do integrante a uma atividade da Banda. Ela deve permanecer conceitualmente independente do calendário externo e pode estar relacionada a ensaio, evento, apresentação, treinamento ou outra atividade válida.

O Google Calendar é uma integração de organização e comunicação. O registro oficial da atividade e da presença pertence ao BMCM. O sistema não deve exigir que toda atividade tenha sido previamente criada no Google Calendar para permitir o registro de uma presença.

### Passes de transporte

A Banda disponibiliza mensalmente uma cota de passes por integrante. A cota deve ser controlada por integrante e por mês de referência.

O administrador do sistema deverá possuir uma rotina para cadastrar ou atualizar a cota mensal de cada integrante que possua cartão de passe cadastrado. O número de controle do cartão será associado ao integrante e deverá ser único. Integrantes que não recebem cartão podem permanecer sem esse cadastro; o cartão não é um campo obrigatório do integrante.

A cota inicial poderá receber **uma única recarga extra no mesmo mês** quando a quantidade de ensaios ou atividades superar os passes disponíveis. A recarga deverá possuir quantidade maior que zero e motivo obrigatório informado pelo administrador. O sistema deverá registrar essa recarga como movimento separado, com data e administrador responsável, e impedir uma segunda recarga extra para o mesmo integrante no mesmo mês.

Toda presença diária registrada para um integrante consome exatamente **2 passes**, independentemente de a atividade ser ensaio, evento, apresentação, treinamento ou outra atividade válida:

* 1 passe para a ida;
* 1 passe para a volta.

Quando o integrante não possuir cartão de passe cadastrado, a presença deverá ser registrada normalmente e não haverá desconto de passes. Essa situação representa uma decisão administrativa ou operacional externa ao sistema; o motivo da ausência do cartão não será documentado no BMCM.

O controle deve permitir consultar passes disponibilizados, recarregados, consumidos e restantes. O saldo não deve depender somente de um número manual: cada disponibilização, recarga e consumo deve possuir histórico, relacionado à presença ou atividade que originou o movimento quando aplicável.

Conceitualmente, o modelo poderá utilizar uma cota mensal e movimentos de passe, por exemplo:

```text
COTA_MENSAL_PASSES
integrante_id, mes_referencia, quantidade_disponibilizada

MOVIMENTO_PASSE
cota_id, atividade_id, presenca_id, data_hora, quantidade, tipo
```

O consumo de cada presença será registrado como movimento de quantidade `-2`, ou em representação equivalente que preserve o histórico e permita calcular o saldo.

Antes de registrar uma presença de integrante com cartão, o sistema deverá verificar se existem pelo menos 2 passes disponíveis. Com apenas 0 ou 1 passe, o registro da presença deverá ser impedido e a situação informada claramente. Integrantes sem cartão não entram nessa validação e não geram movimento de passe. O sistema não deve criar saldo negativo silenciosamente.

O controle de passes está implementado no fluxo atual para ensaios,
eventos e atividades. O sistema controla cartão, cota mensal, recarga
extra, consumo de 2 passes por presença, estorno e histórico de movimentos.
A disponibilização inicial permanece no campo da cota para compatibilidade,
mas também é registrada como movimento auditável individual. Cotas antigas
sem esse movimento continuam sendo calculadas pelo formato legado. Esta regra
deve orientar a análise e a implementação futura, inclusive testes de saldo,
histórico e integridade transacional.

### Calendário e futuras integrações

O calendário interno mensal do BMCM agrega ensaios, eventos e atividades avulsas já cadastrados. A seleção de um dia oferece acesso à chamada de cada registro, ao relatório diário e à criação de um registro naquela data, com o formulário pré-preenchido. O calendário não cria expediente ou horário de funcionamento e não presume horários ausentes. A integração com o Google Calendar é separada, unidirecional e manual: publica registros do BMCM, não substitui o banco de dados e não importa alterações feitas diretamente no Google Calendar. A publicação de atividades avulsas foi implementada e validada por testes automatizados; ainda requer validação com uma conta Google real.

Uma futura integração RFID/NFC ou outra solução IoT poderá identificar o integrante e chamar uma API do BMCM. A API deverá continuar responsável por validar a atividade, verificar a cota, registrar a presença e consumir os 2 passes. RFID, NFC e IoT não fazem parte do escopo atual do PI II.


# 5. Integração com serviços Google

O sistema deverá explorar APIs do Google como parte da integração com serviços externos e do conceito de computação em nuvem. A Central de Comunicações foi concluída funcionalmente e validada por testes automatizados. A sincronização Calendar de atividades avulsas está implementada e testada automaticamente; sua validação com conta real permanece pendente. Os MVPs de Calendar para ensaios/eventos e Drive foram validados com a conta Google configurada no ambiente.

As três integrações principais previstas são:

## 5.1 Google Drive — backup e nuvem

O MVP atual permite enviar backups ZIP locais e consultar arquivos da pasta `BMCM Backups` no Google Drive. A integração deve ser validada com uma conta Google real. A evolução poderá utilizar o Drive como componente de armazenamento em nuvem para:

* backup dos dados do sistema;
* armazenamento de arquivos relevantes;
* eventual armazenamento de relatórios;
* demonstração prática do conceito de computação em nuvem.

O escopo OAuth `drive.file` limita o acesso aos arquivos e à pasta criados pela aplicação. A restauração diretamente a partir do Drive ainda não está implementada.

As credenciais do Google devem ser armazenadas em variáveis de ambiente e nunca em código-fonte, arquivos de texto do projeto ou GitHub. O projeto usa o arquivo local `.env` como mecanismo de configuração local e este arquivo deve permanecer fora do controle de versão.

---

## 5.2 Google Calendar — ensaios, eventos e atividades

O MVP de sincronização unidirecional do BMCM para o Google Calendar está implementado para ensaios, eventos e atividades avulsas. A sincronização é acionada manualmente nas listagens, exige autorização do escopo `calendar.events` e atualiza o vínculo existente quando repetida. Ensaios e eventos foram validados com conta Google real. A nova publicação de atividades avulsas passou nos testes automatizados e ainda precisa ser validada com uma conta real.

O comportamento inicial é:

* ensaios com horário são enviados com duração padrão de uma hora e fuso `America/Sao_Paulo`;
* ensaios sem horário e eventos, que não possuem horário no cadastro atual, são enviados como eventos de dia inteiro;
* cada atividade mantém um vínculo local com o ID do evento Google para evitar duplicidades;
* cancelamentos são propagados somente se a atividade já tiver sido sincronizada;
* alterações feitas diretamente no Google Calendar não são importadas para o BMCM.

A integração auxilia no gerenciamento de:

* ensaios;
* apresentações;
* eventos;
* compromissos da banda;
* atividades futuras.

A ideia é que o sistema BMCM possa utilizar o calendário como recurso externo de organização e comunicação.

A integração deverá ser planejada para evitar duplicidade desnecessária de informações e preservar a coerência entre o banco de dados do BMCM e o calendário externo.

---

## 5.3 Gmail — comunicação

Utilizar a integração com Gmail para apoiar a comunicação relacionada à banda.

A implementação atual contempla fluxo de autorização Google OAuth 2.0 por variáveis de ambiente, armazenamento local do token em `instance/google_oauth_token.json`, renovação automática via refresh token e envio de mensagens com anexos. O sistema também permite configurar o remetente a partir das configurações administrativas. O Gmail é a integração Google operacional atualmente.

Possíveis utilizações:

* comunicação com integrantes;
* avisos sobre ensaios;
* comunicação sobre eventos;
* notificações administrativas;
* comunicação com responsáveis, quando aplicável;
* contato com outras instituições ou prefeituras;
* comunicação relacionada a apresentações e eventos externos.

A funcionalidade deve ser desenvolvida respeitando limites, segurança, autenticação e políticas da API utilizada.

O sistema não deve ser transformado em uma plataforma de e-mail completa. O Gmail deve funcionar como um serviço integrado ao sistema.

---

## 5.4 WhatsApp — canal alternativo de comunicação

O BMCM poderá utilizar o WhatsApp como canal alternativo ao e-mail, especialmente quando não houver autorização para comunicação por e-mail e existir autorização específica para WhatsApp.

A integração será realizada por meio de um módulo externo independente, consumido pelo BMCM através de API HTTP. O módulo `zapapi`, originalmente desenvolvido para experimentos com n8n, poderá ser reutilizado como serviço intermediário em outros projetos, inclusive no BMCM, desde que receba as adequações de segurança necessárias.

O BMCM não deverá importar diretamente o código do módulo externo. A comunicação deverá ocorrer por um adaptador de integração, por exemplo `app/integrations/whatsapp_service.py`, responsável por:

* validar o consentimento específico para WhatsApp;
* validar o telefone do destinatário;
* enviar somente mensagens autorizadas;
* tratar indisponibilidade, timeout e desconexão do serviço;
* registrar o resultado da operação;
* impedir que a chave da API seja exposta ao navegador.

O uso inicial deverá ser restrito ao envio controlado de mensagens de texto. Não fazem parte do primeiro estágio:

* leitura de conversas;
* consulta de contatos e chats;
* gerenciamento de grupos;
* catálogo, etiquetas e respostas automáticas;
* envio de mídia;
* exposição pública da API.

A integração não oficial deverá ser identificada claramente na documentação acadêmica e técnica, incluindo os riscos de instabilidade, desconexão e bloqueio da conta pelo provedor. O módulo externo deve possuir, no mínimo:

* autenticação por chave de API;
* acesso restrito à rede interna ou ao localhost;
* limitação de frequência e fila de envios;
* validação de número e conteúdo;
* logs técnicos sem exposição desnecessária de dados pessoais;
* proteção da sessão persistida do WhatsApp;
* configuração por variáveis de ambiente;
* endpoint mínimo e específico para o BMCM.

O WhatsApp não será substituto automático do e-mail. A seleção de canal deverá seguir esta ordem:

1. verificar se o destinatário possui contato válido;
2. verificar autorização para o canal escolhido;
3. utilizar e-mail quando houver autorização e o serviço estiver disponível;
4. utilizar WhatsApp somente quando houver autorização específica;
5. bloquear o envio quando nenhum canal estiver autorizado;
6. registrar o canal, o resultado e eventual erro.

Autorizações de e-mail e WhatsApp devem ser independentes, com registro de data, origem e eventual revogação.

---

# 6. Conceito de computação em nuvem

A utilização atual do Gmail e os MVPs de integração com Google Calendar e Google Drive devem ser compreendidos como parte da aplicação do conceito de **computação em nuvem**, sujeitos à validação com contas reais.

O objetivo não é apenas "usar serviços do Google".

O projeto deve demonstrar conceitualmente que uma aplicação web pode:

* utilizar serviços externos;
* armazenar informações remotamente;
* integrar diferentes sistemas através de APIs;
* utilizar infraestrutura e serviços disponíveis na nuvem;
* manter o sistema local integrado a serviços externos.

Essa característica deve ser devidamente documentada no projeto acadêmico.

---

# 7. Central de comunicações e relacionamento externo

O BMCM deverá possuir uma Central de Comunicações simples, administrativa e multicanal. A central não deverá se transformar em um CRM ou em uma plataforma completa de e-mail ou mensagens.

## 7.1 Funcionalidades da central

A central já possui implementação funcional para:

* criar uma comunicação;
* informar assunto e mensagem;
* selecionar o público-alvo;
* enviar para um integrante, responsável, grupo de integrantes ou contatos externos autorizados;
* vincular a comunicação a um ensaio, evento ou apresentação;
* revisar e confirmar o envio;
* consultar o histórico de comunicações;
* visualizar status `rascunho`, `enviado`, `parcial` ou `falhou`;
* registrar usuário responsável, data, canal e resultado por destinatário.

A funcionalidade de modelos de mensagem, quando adicionada, deve ser tratada como evolução incremental e não como requisito obrigatório para a etapa atual.

Públicos inicialmente previstos:

* integrante específico;
* responsáveis de um integrante;
* integrantes ativos;
* integrantes de determinado naipe;
* participantes de um evento;
* contatos institucionais e organizadores autorizados.

## 7.2 Canais e consentimento

A central deverá trabalhar com canais independentes:

* Gmail, quando houver autorização de e-mail;
* WhatsApp externo, quando houver autorização específica de WhatsApp;
* outros canais somente mediante justificativa e implementação futura.

O sistema não deverá enviar automaticamente por outro canal apenas porque o primeiro falhou ou não foi autorizado. O usuário deverá visualizar a situação do contato e confirmar o canal alternativo quando permitido.

Cada destinatário deverá possuir, quando aplicável, informações de contato, autorização, data da autorização, origem do consentimento e data de revogação.

## 7.3 Modelo conceitual

Podem ser criadas as entidades `Comunicacao`, `ComunicacaoDestinatario` e `ContatoComunicacao`.

`Comunicacao` deverá armazenar assunto, corpo, tipo, status, vínculo opcional com evento ou ensaio, usuário criador e datas de criação e envio.

`ComunicacaoDestinatario` deverá armazenar canal, destino, status individual, data de envio e erro retornado.

`ContatoComunicacao` deverá armazenar canal, destino, autorização, data de autorização, origem do consentimento e revogação.

Os modelos de mensagem poderão utilizar variáveis controladas, como nome do destinatário, data, horário, local e nome do evento.

O BMCM deverá evoluir para também apoiar a comunicação institucional da banda.

Além da comunicação interna entre administração e integrantes, o sistema deverá apoiar, de forma simples e controlada, contatos relacionados a:

* apresentações;
* eventos municipais;
* eventos de outras cidades;
* solicitações de apresentações;
* comunicação com prefeituras;
* comunicação com organizadores de eventos;
* instituições parceiras.

Essa funcionalidade deve ser mantida simples e compatível com o objetivo do projeto.

Não criar um CRM completo, caixa de entrada corporativa ou sistema de conversas internas.

---

# 8. Acessibilidade

A acessibilidade deve ser tratada como requisito real da aplicação e não apenas como item documental.

Considerar:

* navegação por teclado;
* uso adequado de foco visível;
* textos legíveis;
* tamanho ajustável das fontes;
* contraste adequado;
* tema claro e escuro;
* personalização de contrastes e paleta visual em painel administrativo;
* elementos HTML semanticamente apropriados;
* identificação adequada de campos de formulário;
* mensagens de erro compreensíveis;
* compatibilidade com diferentes tamanhos de tela;
* responsividade;
* atalhos de teclado quando forem realmente úteis;
* controle de foco em modais, abas e menus;
* indicadores visuais acessíveis para botões, links e estados ativos;
* uso de labels, legends e descrições para leitores de tela;
* suporte a reduções de movimento e melhor legibilidade em telas sensíveis ao contraste.

A personalização de cores deve considerar contraste suficiente para preservar a legibilidade. O sistema deve permitir ajustes visuais sem comprometer uso em condições de baixa visão, contraste reduzido ou leitura assistida.

O sistema não deve permitir que uma configuração visual torne a interface inutilizável. A ferramenta de personalização deve incluir, quando possível, opções seguras para contraste, cor de fundo, cor de destaques e tamanho de texto, mantendo acessibilidade mínima e consistência visual.

---

# 9. UX — experiência do usuário

O sistema deve priorizar simplicidade.

A aplicação será utilizada por pessoas com diferentes níveis de conhecimento tecnológico.

Portanto:

* telas devem ser objetivas;
* informações importantes devem ser facilmente encontradas;
* operações frequentes devem exigir poucos passos;
* mensagens devem ser claras;
* erros devem explicar o que aconteceu e, quando possível, como corrigir;
* menus devem possuir organização consistente;
* a interface deve funcionar em computadores, tablets e celulares.

## 9.1 Organização prevista do menu principal

O menu principal deverá ser reorganizado para reduzir a quantidade de itens visíveis e melhorar a navegação em telas pequenas.

### Cadastro

Deverá reunir as rotinas de manutenção de dados:

* usuários;
* integrantes;
* instrumentos;
* escolas;
* naipes;
* tipos e demais cadastros auxiliares.

### Atividades

Deverá reunir as operações da rotina da banda:

* ensaios;
* eventos;
* controle de presença;
* relatórios diretamente relacionados às atividades.

### Utilitários

Deverá reunir ferramentas de apoio:

* central de comunicações, somente quando o remetente `@gmail.com` e a autorização Google Workspace estiverem válidos;
* Google Calendar, quando o escopo estiver autorizado;
* relatórios gerais e ferramentas auxiliares que não pertençam ao cadastro ou às atividades.

### Menu do usuário

As funções administrativas deverão permanecer no menu do usuário e não no menu principal:

* configurações do sistema, somente para administradores;
* backup e restauração, somente para administradores;
* logs administrativos, conforme a permissão do usuário;
* encerramento da sessão.

O agrupamento deverá respeitar as permissões existentes. Ocultar um item no menu não substitui a proteção da rota, que deverá continuar sendo validada no servidor.

Em telas pequenas, os grupos deverão utilizar dropdowns ou seções expansíveis compatíveis com o menu hamburguer. Os controles deverão possuir foco visível, área de toque adequada, indicação do grupo aberto e comportamento acessível por teclado.

## 9.2 Alterações previstas na navegação

As seguintes alterações deverão ser executadas como evolução da interface:

1. criar os grupos `Cadastro`, `Atividades` e `Utilitários`;
2. mover comunicações e, futuramente, Calendar para `Utilitários`;
3. manter backup, configurações e logs administrativos no menu do usuário;
4. ocultar comunicações quando as pré-condições de remetente Gmail e OAuth não forem atendidas;
5. exibir Calendar somente após a integração estar implementada e autorizada;
6. preservar autorização por perfil e proteção de todas as rotas;
7. revisar o comportamento dos dropdowns no menu hamburguer em celulares;
8. validar a navegação por teclado, foco, contraste e leitura por tecnologias assistivas.

Não implementar funcionalidades apenas porque são tecnicamente interessantes.

Cada funcionalidade deve possuir uma justificativa relacionada à necessidade da banda ou às exigências acadêmicas.

---

# 10. Segurança

A segurança deve continuar sendo uma preocupação central do projeto.

Considerar:

* senhas armazenadas com hash seguro;
* controle de autenticação;
* controle de autorização;
* proteção de rotas;
* validação de entradas;
* proteção contra SQL Injection;
* proteção contra XSS;
* proteção contra CSRF quando aplicável;
* gerenciamento seguro de sessões;
* proteção das credenciais das APIs;
* utilização de variáveis de ambiente para segredos;
* não armazenar tokens, senhas ou chaves no GitHub;
* backups protegidos por ZIP AES-256, com senha de ambiente ou chave aleatória local em `instance/.backup_password`;
* cadastro da senha de backup com confirmação e senha atual do administrador; gravação em `.env` com permissão `0600` e revelação mascarada até nova reautenticação na guia Sistema/Manutenção;
* registros de eventos importantes do sistema quando necessário.

A senha ou o arquivo-chave dos backups deve ser preservado separadamente dos arquivos ZIP. Perder essa chave impede a restauração dos backups criptografados.

A interface não permite trocar uma chave já usada por backups: o administrador pode apenas registrar no `.env` a mesma chave existente, evitando tornar cópias anteriores irrecuperáveis. Senhas administradas externamente por variável de ambiente continuam fora da edição pela interface.

Não implementar mecanismos de segurança apenas superficialmente para "cumprir requisito".

---

# 11. Banco de dados

O banco de dados existente deve ser preservado sempre que tecnicamente possível.

Alterações no modelo devem ser planejadas.

Antes de alterar tabelas existentes:

1. verificar dependências;
2. verificar funcionalidades que utilizam a tabela;
3. preservar dados existentes;
4. evitar duplicação de informações;
5. documentar alterações importantes.

Novas entidades podem ser criadas quando necessárias, por exemplo:

* eventos;
* ensaios;
* atividades e seus tipos;
* presenças;
* cartões de passe opcionais por integrante;
* cotas mensais de passes;
* movimentos/consumos de passes vinculados às presenças;
* registros de comunicação;
* configurações de integração;
* logs.

---

# 12. APIs

A utilização de APIs deve ser tratada como parte importante da evolução do BMCM.

O projeto deve demonstrar:

* consumo de APIs externas;
* autenticação em APIs quando necessário;
* tratamento de erros;
* tratamento de indisponibilidade do serviço;
* armazenamento seguro de credenciais;
* integração entre sistemas;
* documentação das integrações.

O estado e a ordem de prioridade das integrações são:

1. Gmail API: fluxo OAuth e envio implementados; Central de Comunicações validada por testes automatizados, com envio real dependente da conta Google configurada no ambiente;
2. Google Calendar API: sincronização unidirecional de ensaios/eventos validada com conta real; publicação de atividades avulsas implementada e testada automaticamente, com validação real pendente;
3. Google Drive API: MVP de upload e listagem de backups validado com conta Google real;
4. API HTTP do módulo externo de WhatsApp: possibilidade futura, condicionada à autorização e aos requisitos de segurança.

O módulo externo de WhatsApp deverá permanecer desacoplado do Flask. O BMCM deverá consumi-lo por um cliente de serviço com timeout, tratamento de erros, autenticação e registro de auditoria.

As integrações do BMCM devem manter escopo mínimo e controlado:

* Google Calendar: sincronização em uma direção, do BMCM para o calendário;
* Google Drive: backup remoto e consulta de arquivos;
* Gmail: envio de comunicações autorizadas, já disponível;
* WhatsApp: envio alternativo de mensagens de texto autorizadas através de serviço externo, como possibilidade futura.

Integrações bidirecionais, leitura de conversas, automações de grupo e envio de mídia deverão ser consideradas extensões posteriores, condicionadas a testes, segurança e justificativa para a Banda.

Não adicionar APIs externas sem necessidade.

---

# 13. Testes

O projeto deverá estruturar uma estratégia de testes.

Priorizar inicialmente:

* autenticação;
* permissões;
* cadastro de usuários;
* controle de presença;
* eventos;
* integrações;
* invariantes de passes implementados: consumo de 2, estorno mesmo após desativação do cartão, idempotência, saldo não negativo e rollback coletivo;
* migrações de presença preservando registros, movimentos associados e índices parciais;
* validações;
* operações críticas do banco de dados;
* acessibilidade básica em telas críticas;
* navegação por teclado e foco visual em formulários e menus.

Testes devem ser automatizados sempre que possível.

Também devem existir testes manuais documentados para funcionalidades que dependem de serviços externos ou interação visual.

---

# 13.1 Análise opcional de presença e indicadores de dados

A análise de dados de presença deve ser tratada como uma evolução opcional, mas com forte valor para gestão da banda.

Indicadores que podem ser implementados no futuro:

* frequência individual por mês;
* percentual médio de presença por aluno;
* percentual médio de presença por grupo ou naipe;
* comparação entre ensaios e eventos;
* alunos com presença abaixo de um limite mínimo;
* tendência de faltas por período;
* volume de presenças e ausências por mês;
* indicadores de assiduidade e desempenho de frequência.

Esses dados podem alimentar relatórios e gráficos simples, sem exigir uma estrutura de BI complexa. O objetivo principal é transformar registros operacionais em informações úteis para gestão, acompanhamento e tomada de decisão administrativa.

A análise de dados não deve substituir a operação principal do sistema, mas deve ampliar seu valor estratégico como ferramenta de acompanhamento institucional.

---

# 14. Git e GitHub

O Git/GitHub deve continuar sendo utilizado como controle de versão.

Boas práticas:

* commits objetivos;
* mensagens de commit claras;
* branches quando necessário;
* evitar armazenar arquivos sensíveis;
* não armazenar `.env`;
* documentação do projeto;
* histórico compreensível das alterações.

O GitHub deve funcionar também como evidência do processo de desenvolvimento do PI.

---

# 15. Regra para Codex / GitHub Copilot

Antes de alterar qualquer parte do sistema, analisar:

1. a arquitetura existente;
2. as rotas existentes;
3. os modelos existentes;
4. os templates existentes;
5. os arquivos JavaScript;
6. os estilos CSS;
7. os mecanismos de autenticação;
8. as dependências atuais;
9. os requisitos deste documento.

**Não substituir código funcional sem necessidade.**

**Não criar uma nova arquitetura paralela quando uma funcionalidade puder ser integrada à arquitetura existente.**

**Não instalar dependências sem justificar sua necessidade.**

**Não modificar banco de dados sem analisar impacto.**

**Não remover funcionalidades existentes para implementar uma nova funcionalidade.**

Sempre preferir alterações pequenas, testáveis e reversíveis.

---

# 16. Princípio geral do desenvolvimento

O BMCM deve ser tratado como um sistema real em evolução, e não como um projeto descartável criado exclusivamente para avaliação acadêmica.

A implementação deve buscar equilíbrio entre:

**Necessidade real da banda + requisitos acadêmicos + simplicidade + segurança + manutenção futura.**

O objetivo final é entregar uma aplicação funcional que possa continuar sendo utilizada e evoluída depois do encerramento do PI.

---

# 17. Funcionalidades previstas para esta etapa

### Núcleo do sistema

* autenticação;
* usuários;
* permissões;
* administração;
* dashboard;
* cadastro e gerenciamento dos integrantes.

### Gestão da banda

* integrantes;
* ensaios;
* eventos;
* apresentações;
* controle manual de presença;
* histórico de frequência.

### Integrações externas e comunicação

* Gmail e Central de Comunicações: fluxo implementado e validado por testes automatizados, incluindo consentimento externo e revogação;
* Google Calendar: MVP unidirecional para ensaios/eventos validado com conta real; atividades avulsas também são publicadas manualmente e passaram nos testes automatizados, aguardando validação real;
* Google Drive: MVP de upload e listagem implementado e validado com conta real;
* WhatsApp: possibilidade futura como módulo externo independente e canal alternativo autorizado.

### Requisitos técnicos

* Flask;
* banco de dados;
* JavaScript;
* APIs;
* computação em nuvem;
* Git/GitHub;
* testes;
* segurança;
* acessibilidade;
* responsividade;
* UX.


As funcionalidades centrais do PI II devem ser implementadas de forma incremental. Integrações externas e canais adicionais devem começar por um MVP seguro e controlado, sem impedir o funcionamento do núcleo local do BMCM.

---

# 18. Critério para novas funcionalidades

Antes de implementar uma nova funcionalidade, responder:

> **Qual problema ela resolve para a Banda?**

e/ou:

> **Qual requisito do PI ela atende?**

Se não houver uma resposta clara para nenhuma das duas perguntas, a funcionalidade deve ser considerada opcional e não deve ser adicionada apenas para aumentar a complexidade do sistema.

---

# 19. Atualização controlada da aplicação

Como evolução futura, o BMCM poderá possuir um mecanismo de atualização assistida para reduzir a necessidade de intervenção presencial em cada computador instalado.

Esse mecanismo deverá ser tratado como um conceito planejado, não como uma funcionalidade atualmente disponível. A atualização somente poderá ser autorizada por um administrador do sistema.

## 19.1 Empacotamento das versões

Cada versão publicada deverá ser empacotada fora do ambiente de produção, preferencialmente por uma rotina de publicação ou CI/CD. O pacote deverá conter somente arquivos da aplicação, como código Python, templates, arquivos estáticos e dependências/documentação necessárias.

Não poderão ser incluídos no pacote:

* banco de dados de produção;
* arquivo `.env`;
* uploads de usuários;
* tokens, senhas ou chaves de API;
* logs locais;
* configurações específicas de cada instalação.

Cada pacote deverá possuir versão, notas de alteração e checksum SHA-256. O uso de assinatura digital deverá ser considerado para uma etapa posterior.

## 19.2 Consulta e instalação

O sistema poderá consultar um manifesto de versão publicado no GitHub e informar ao administrador quando houver atualização disponível. O download deverá preferencialmente utilizar um pacote de GitHub Releases, e não arquivos individuais obtidos diretamente do Raw do GitHub.

O fluxo previsto será:

1. consultar a versão instalada;
2. consultar o manifesto remoto por HTTPS;
3. exibir a versão e as notas da atualização;
4. solicitar confirmação explícita do administrador;
5. criar backup do banco e da versão atual;
6. baixar o pacote em diretório temporário;
7. validar checksum e, futuramente, assinatura digital;
8. colocar o sistema em manutenção;
9. instalar os arquivos permitidos;
10. executar migrações de banco necessárias;
11. reiniciar ou solicitar reinício do serviço;
12. validar a inicialização e permitir rollback em caso de falha.

A atualização deverá usar rota `POST` protegida por autenticação, autorização administrativa e CSRF. O processo deverá impedir duas atualizações simultâneas e registrar versão anterior, versão nova, usuário autorizador, datas, status e erros.

O mecanismo deverá preservar banco de dados, uploads, configurações locais e demais dados específicos da instalação. Atualizações automáticas não deverão substituir o banco de produção.

---

# 20. Regra pétrea de versionamento

O controle de versão da aplicação é uma regra permanente e obrigatória do projeto BMCM.

Toda correção, nova rotina, novo formulário, alteração estrutural, migração de banco ou melhoria relevante deverá atualizar a versão da aplicação antes de ser considerada concluída.

A versão deverá sempre utilizar três componentes no formato:

```text
principal.atualizacao.contagem
```

Exemplo:

```text
1.4.5
```

A contagem deve ser atualizada a cada evolução concluída, conforme definido pelo processo de versionamento do projeto.

As partes possuem os seguintes significados:

* `principal`: versão estrutural principal do sistema;
* `atualizacao`: etapa, ciclo ou evolução funcional;
* `contagem`: quantidade incremental de alterações realizadas.

Regras obrigatórias:

1. cada alteração concluída deve incrementar o terceiro componente;
2. a contagem não é reiniciada por data: cada nova alteração parte da versão já existente;
3. ao passar de `99` no terceiro componente, ele volta a `0` e o segundo componente é incrementado;
4. ao passar de `99` no segundo componente, ele volta a `0` e o primeiro componente é incrementado;
5. uma nova etapa funcional pode incrementar diretamente o segundo componente; mudanças estruturais incompatíveis podem incrementar diretamente o primeiro;
6. a versão deve ser alterada no código-fonte, em `config.py`, nas constantes `APP_VERSION_MAJOR`, `APP_VERSION_UPDATE` e `APP_VERSION_COUNT`;
7. a versão não pode ser alterada pelas configurações administrativas da aplicação;
8. a versão exibida nas telas deve ser a mesma versão oficial registrada no código;
9. toda publicação ou atualização deve registrar a nova versão e suas alterações no histórico do projeto.

Essa regra não deve ser removida, ignorada ou substituída por numeração independente em módulos. Nenhuma nova implementação estará concluída sem a atualização correspondente da versão.
