# MobilityPro — publicar com banco e três interfaces

**Não confundir com o aplicativo Thiago Reis de elétrica**. Este projeto atende /passageiro, /motorista e /admin.

## Hospedagem Render + banco externo PostgreSQL

1. Crie um banco PostgreSQL separado para o MobilityPro no Neon ou Supabase, com SSL habilitado. Nunca use o banco do app de elétrica e nunca compartilhe senha/connection string nesta conversa.
2. Publicação: Render Blueprint desta branch `mobilitypro`, serviço `mobilitypro-iacanga`.
3. Na criação, preencha a variável secreta `DATABASE_URL` com a URI do seu PostgreSQL. Render cria `JWT_SECRET` e `SETUP_TOKEN` aleatórios. A configuração da sua URL pública (`RENDER_EXTERNAL_URL` e `RENDER_EXTERNAL_HOSTNAME`) é automática.
4. Depois de `Live`, abra **https://SEU-RENDER/instalar**. Revele o `SETUP_TOKEN` somente em Render → Environment, cole no formulário e crie seu usuário proprietário com senha >= 12 caracteres.
5. Os portais são `/admin`, `/passageiro`, `/motorista`; tudo usa o mesmo banco e HTTPS.

## Segurança na avaliação

`PUBLIC_REGISTRATION=false`: não permite cadastrar passageiros/motoristas até você confirmar documentação, políticas, SMS e prevenção a fraude. Os dados existentes nunca são substituídos por dados falsos. `PRIVATE_DOCS_PERSISTENT=false`: impede carregar CNH/CRLV em disco que desaparece em reinicializações do Render Free. Para documentos reais configure storage privado persistente e auditado e só então ative a opção, preferivelmente numa instância com disco persistente ou armazenamento S3 dedicado com implementação própria.

## Integrações

- `ROUTING_URL`: serviço OSRM privado/com licença, URL HTTPS; ou `MAPBOX_ACCESS_TOKEN`: token do provedor Mapbox Directions. A aplicação calcula percursos e estimativas via rotas reais com o provedor configurado. **Não usar serviço de demonstração como rota comercial.**
- GPS: o navegador/telefone envia localização real do motorista conforme permissão. Dependendo do sistema, navegador em segundo plano pode parar o envio; app Expo ainda precisa ser compilado e testado.
- Pagamentos: atualmente apenas dinheiro com confirmação declaratória. **Pix, cartão e split não estão conectados** — exigem credenciais de comerciante, webhooks validados, testes de reembolso/idempotência e conciliação.
- SMS/OTP, push FCM/APNs, mapas com contrato comercial e lojas de apps ainda exigem fornecedores, credenciais e homologação. Nunca divulgar que estão conectados sem testes.
- Administração: cidades, tarifas, restrições, documentos, motoristas, corridas, relatórios e auditoria.

## Obrigatório antes de uso comercial

Termos e privacidade, cumprimento LGPD, parecer local de legislação municipal, validação documental real, pen test, backup/restauração, monitoramento, integração de roteamento e validações em campo com Android/iOS. Render grátis e banco grátis são apenas para avaliação, não para operação comercial.
