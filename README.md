# Thiago Reis PRO — elétrica e câmeras

**[🚀 IMPLANTAR APLICATIVO E BANCO NO RENDER](https://render.com/deploy?repo=https://github.com/Thiagoreis22-ai/teste)**

Esse botão abre a criação do servidor (Flask + HTTPS) e banco PostgreSQL no Render com o arquivo `render.yaml`. É necessário entrar no Render e aprovar a implantação em sua própria conta. Só depois será gerado um endereço do tipo `https://thiago-reis-pro-web.onrender.com` (o nome final será determinado pelo Render).

**⚠️ ATENÇÃO:** o banco PostgreSQL gratuito do Render expira **30 dias** após a criação e não inclui backups. Para uso real, escolha/atualize um plano persistente antes do vencimento e configure backups, para não perder cadastros e orçamentos. Não trate o ambiente gratuito como armazenamento definitivo de clientes.

## Primeiro acesso
1. Abra a URL publicada pelo Render (não o GitHub Pages, que é somente uma cópia local).
2. Acesse as variáveis de ambiente do serviço Render e revele/copiei o valor de `SETUP_TOKEN` (é gerado automaticamente na implantação). **Não coloque esse token no repositório ou WhatsApp.**
3. No formulário do primeiro acesso, insira esse código de ativação e crie **duas senhas diferentes, com pelo menos 8 caracteres**: uma de proprietário e outra de funcionário.
4. O proprietário vê orçamentos, catálogo, financeiro e configurações. O funcionário vê apenas clientes, serviços e agenda.
5. Para trazer dados da versão anterior, no acesso de proprietário use a exportação da cópia local e restaure o backup no sistema hospedado. Não importe os mesmos dados de várias fontes sem conferência.

O sistema usa HTTPS da hospedagem, sessões HttpOnly e senhas com hash scrypt. O app não emite nota fiscal (NFS-e). Orçamentos e comprovantes são documentos comerciais não fiscais.

Código: [interface](./thiago-reis-pro/index.html) · [servidor](./server.py) · [testes](./tests/test_api.py) · [instruções detalhadas](./DEPLOY.md).

A versão só para um aparelho já foi publicada no GitHub Pages: https://thiagoreis22-ai.github.io/teste/ — ela **não sincroniza** dados com outros telefones.
