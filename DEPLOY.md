# Thiago Reis PRO — modo online compartilhado

A versão HTML permanece local ao abrir via GitHub Pages. O servidor `server.py` foi preparado para a publicação segura e compartilhada por hospedagem Python + PostgreSQL.

**Para entrar em produção:**
1. Criar um banco PostgreSQL persistente na hospedagem.
2. Implantar este repositório via Dockerfile, com HTTPS público.
3. Definir as variáveis `APP_ENV=production`, `DATABASE_URL` e `SETUP_TOKEN` (aleatório com pelo menos 24 caracteres).
4. Abrir a URL da hospedagem (a página detecta o backend pelo meta `tr-cloud` inserido pelo servidor).
5. No primeiro acesso, informar o SETUP_TOKEN e criar as senhas diferentes de proprietário e funcionário. Não fornecer a senha do proprietário ao funcionário.
6. Se os dados foram criados antes no navegador, exportar o backup da versão local e importar na versão online somente com a conta de proprietário. Faça backup antes de migrar.

**Importante:** sem conectar/autorizar uma hospedagem e um PostgreSQL, não há backend online. Nunca salve banco, `.env`, senhas nem dados pessoais no repositório público. A aplicação usa autenticação via cookie HttpOnly, hash scrypt para senhas, verificação de permissões no servidor e atualização por revisão. Consulte as políticas do provedor para backups e segurança antes de inserir clientes reais.
