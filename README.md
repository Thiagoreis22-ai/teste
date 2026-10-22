# MobilityPro — Plataforma de Mobilidade Urbana

**Código-fonte de uma primeira versão funcional integrada, NÃO uma operação comercial pronta.**

Um backend SQL central, três interfaces web conectadas e dois projetos-fonte para apps Android/iOS. O software foi criado com dados reais persistidos: não contém passageiros, motoristas, viagens, notas ou ganhos fictícios no banco entregue.

## Abrir no Windows — passo a passo

1. Extraia o ZIP para uma pasta normal, por exemplo `C:\MOBILITYPRO`.
2. Instale **Python 3.11 ou superior** se não tiver. Marque **Add Python to PATH** no instalador oficial.
3. Execute duas vezes `INICIAR_MOBILITYPRO_WINDOWS.bat`.
4. Na primeira execução, aguarde instalar as dependências (precisa internet). Crie seu usuário **proprietário** e senha forte.
5. **Não feche a janela preta.** Abra no Chrome:
   - **Admin:** <http://127.0.0.1:8080/admin>
   - **Passageiro:** <http://127.0.0.1:8080/passageiro>
   - **Motorista:** <http://127.0.0.1:8080/motorista>
   - **Documentação interativa da API:** <http://127.0.0.1:8080/docs>
6. Para encerrar, use `Ctrl+C` na janela do servidor.

**Observação:** o iniciador cria `.env` com segredo aleatório, banco persistente `mobilitypro.db` e a opção **TESTE LOCAL de distância em linha reta**. Essa modalidade **não calcula trajeto viário** e é exclusivamente para exercitar o fluxo de viagens em ambiente de desenvolvimento. Não publique `APP_ENV=development` na internet. Em `APP_ENV=production`, a aproximação é obrigatoriamente desativada e um roteador real torna-se necessário.

## Como testar o primeiro ciclo

1. Entre como proprietário em `/admin`, vá em **Tarifas** e configure tarifa `economico` para Iacanga. Não existem preços inventados pré-cadastrados.
2. Crie um perfil de motorista em `/motorista` com documentos e informações reais; faça upload de CNH e CRLV em **Conta**.
3. No Admin > Motoristas, confira os documentos e aprove manualmente, apenas se válidos.
4. No celular, com HTTPS configurado, o motorista deve autorizar GPS real, ficar **online** e estar na área operacional. **GPS do navegador pode parar em segundo plano.**
5. Cadastre passageiro em `/passageiro`, autorize origem via GPS, marque o destino tocando no mapa, escolha categoria e consulte estimativa.
6. Solicite viagem. O backend busca motoristas elegíveis com localização atualizada há, no máximo, 90 segundos e a até 12 km do embarque.
7. No motorista > Ofertas, aceite; prossiga por **Cheguei → Iniciar → Concluir**.
8. O sistema grava os eventos e cria lançamentos financeiros da viagem em dinheiro. O motorista pode declarar recebimento, sem simular liquidação bancária.
9. O administrador consulta corridas, operações e auditoria.

**Para testar sem GPS real**, utilize exclusivamente a suíte de testes automatizados (que prepara um banco isolado com usuários temporários). Não há botão administrativo para falsificar a localização de motoristas.

## Ambiente de desenvolvimento no Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

### Variáveis de ambiente

O arquivo `.env` criado na primeira execução é carregado pelo `run.py`. Alternativamente configure variáveis de ambiente do processo ao iniciar com `uvicorn`.

| Variável | Função |
|---|---|
| `JWT_SECRET` | Obrigatório em produção, pelo menos 48 caracteres aleatórios |
| `DATABASE_URL` | Conexão SQL; SQLite local ou PostgreSQL |
| `APP_ENV` | `development`, `test` ou `production` |
| `ROUTING_URL` | Servidor OSRM de rotas viárias autorizado para uso comercial |
| `ALLOW_DEV_DIRECT_DISTANCE` | Habilita estimativa em linha reta somente `development/test` |
| `ALLOWED_ORIGINS` | Origens autorizadas em CORS |
| `PRIVATE_DOCS` | Diretório protegido de documentos de motoristas |

A `.env` nunca deve ser enviada ao GitHub nem compartilhada.

## Segurança de dados

- Senhas protegidas por PBKDF2-HMAC-SHA256 com sal individual e 400.000 iterações.
- JWT assinado, validade 8 horas; validações de perfis em todas as ações principais.
- Arquivos privados (CNH/CRLV) limitados a 5 MB, MIME verificado pelo cabeçalho, gravação fora do diretório público.
- Acesso a detalhes da corrida restrito a passageiro, motorista atribuído e administração.
- Aceitação de corrida com atualização SQL condicional atômica, evitando dupla atribuição.
- Histórico da corrida, versão tarifária e registros de auditoria persistentes.
- A localização do motorista só é registrada após autorização GPS, com validade de até 90 segundos.
- Nunca enviar login ou senha por mensagem ou e-mail.

A versão local não tem mecanismos operacionais suficientes para suportar lançamentos comerciais (ex.: controles antifraude aprofundados, verificação externa de documentos, hospedagem HTTPS certificada, backups validados e adequação LGPD). Não exponha a instância SQLite do PC à internet.

## Projetos Android e iOS

Em `native/passenger` e `native/driver` há aplicativos fonte **Expo/React Native** que consomem a mesma API, com SecureStore, GPS nativo e telas próprias. O projeto motorista tem tarefa de localização de fundo para permissões aprovadas pela plataforma. **Esses aplicativos não foram compilados ou publicados** neste ambiente, pois não há acesso a npm/credenciais de assinatura. Para compilar em computador conectado à internet:

```bash
cd native/passenger  # ou native/driver
npm install
# Edite extra.apiBaseUrl em app.json: endereço HTTPS público e REAL do backend
npx expo run:android
# No macOS com Xcode: npx expo run:ios
```

Confirme versões e suporte do SDK Expo, permissões no Android/iOS e assinatura. O código nativo é uma base de integração, **não um binário de loja pronto**. O app do motorista exige testes físicos específicos para GPS em segundo plano, bateria e reconexão.

## Implantação em servidor

Amostra de infraestrutura PostgreSQL/PostGIS e API Docker: `infra/docker-compose.dev.yml`. É exemplo local com loopback, não hospedagem pública pronta. Produção exige proxy reverso HTTPS, DNS, monitoramento, rotação de segredos, firewall, backups testados, validação de documentos, políticas LGPD e gestão de credenciais.

Para a rota viária de produção, preencha `ROUTING_URL` com serviço OSRM dedicado e autorizado. Sem ele, solicitações reais retornam **503 explícito**, em vez de apresentar trajetos inventados.

## Testes executados

```bash
python -m pytest -q tests/test_integration.py
# Windows: execute TESTAR_MOBILITYPRO_WINDOWS.bat
```

Abrangem cadastro, login, RBAC, aprovação, GPS autorizado, tarifas, solicitação, despacho, oferta, aceitação, transições, conclusão, pagamentos em dinheiro, livro-razão, avaliações, suporte, cancelamento e bloqueio de roteamento em produção.

## Estrutura

```
backend/              API FastAPI + SQLAlchemy + modelos + versionamento esquema
apps/passenger/       Aplicativo passageiro web responsivo
apps/driver/          Aplicativo motorista web responsivo
apps/admin/           Painel administrativo web
apps/common/          Identidade visual e cliente de API compartilhados
native/passenger/     Projeto Android/iOS React Native Expo
native/driver/        Projeto Android/iOS React Native Expo + GPS em segundo plano
infra/                Docker/PostgreSQL exemplo
requirements.txt      Dependências Python
.env.example          Variáveis exigidas / serviços externos
run.py                Iniciador portátil / primeiro acesso
INICIAR_MOBILITYPRO_WINDOWS.bat
TESTAR_MOBILITYPRO_WINDOWS.bat
```

Leia `docs/STATUS_DE_ENTREGA.md` antes de considerar a plataforma pronta para clientes.

## Publicação web com HTTPS (servidor próprio)

A configuração de implantação está em [`docs/PUBLICAR_NA_WEB.md`](docs/PUBLICAR_NA_WEB.md).
No Linux com Docker, configure `infra/.env.production` a partir do exemplo,
aponte o DNS de seu domínio e execute `infra/INICIAR_SERVIDOR_PRODUCAO.sh`.
Crie o proprietário com `infra/CRIAR_PROPRIETARIO.sh`.
O acesso será `https://SEU_DOMINIO/admin` depois que a implantação for
realizada no servidor e o HTTPS estiver ativo. **Nenhum site é publicado
simplesmente por baixar o ZIP.** Pagamentos Pix/cartão e SMS ainda dependem
de contratos e integração com provedores reais.
