"""THIAGO REIS PRO | Proposta comercial A4.
Layout inspirado na referência do proprietário; dados sempre do cadastro real.
"""
from io import BytesIO
from math import cos, sin, pi
from pathlib import Path
import re

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.lib.utils import ImageReader

W,H=595.276,841.89
NAVY=HexColor("#061426")
DEEP=HexColor("#020A14")
BLUE=HexColor("#0874C5")
SKY=HexColor("#179BEA")
GOLD=HexColor("#DEA937")
WHITE=HexColor("#FFFFFF")
INK=HexColor("#132234")
MUTED=HexColor("#647082")
LIGHT=HexColor("#EDEFF3")
GRID=HexColor("#CCD5DF")

def clean(v,limit=220):
    txt=re.sub(r"\s+"," ",str(v if v is not None else "")).strip()
    return txt[:limit]

def price(v):
    try:n=float(v or 0)
    except (TypeError,ValueError,OverflowError):n=0.0
    if n!=n or abs(n)>1e11:n=0
    return "R$ "+f"{n:,.2f}".replace(",","@").replace(".",",").replace("@",".")

def lines_for(text,width,font="Helvetica",size=9,max_lines=3):
    words=clean(text,1000).split()
    out=[];line=""
    for word in words:
        if stringWidth(word,font,size)>width:
            while stringWidth(word,font,size)>width and len(word)>1:
                split=max(1,len(word)-1)
                while split>1 and stringWidth(word[:split],font,size)>width:split-=1
                if line:out.append(line);line=""
                out.append(word[:split]);word=word[split:]
        test=(line+" "+word).strip()
        if line and stringWidth(test,font,size)>width:
            out.append(line);line=word
        else:line=test
    if line:out.append(line)
    if len(out)>max_lines:
        out=out[:max_lines]
        tail=out[-1]
        while tail and stringWidth(tail+"...",font,size)>width:tail=tail[:-1]
        out[-1]=tail+"..."
    return out or ["-"]

def date_br(iso):
    s=clean(iso,10)
    return s[8:10]+"/"+s[5:7]+"/"+s[:4] if re.fullmatch(r"\d{4}-\d{2}-\d{2}",s) else s

def build_quote_pdf(quote,client,settings,assets_dir=None):
    out=BytesIO()
    c=canvas.Canvas(out,pagesize=(W,H),pageCompression=1)
    c.setTitle("Orçamento Comercial | Thiago Reis")
    c.setAuthor(clean(settings.get("company") or "Thiago Reis",80))
    cl=client or {};st=settings or {};q=quote or {}
    company=clean(st.get("company") or "Thiago Reis",44)
    phone=clean(st.get("phone") or "14996600996",24)
    digits=re.sub(r"\D","",phone)
    digits=digits[2:] if len(digits)==13 and digits.startswith("55") else digits
    wa="https://wa.me/55"+digits if len(digits)>=10 else ""
    cnpj=clean(st.get("cnpj") or "Não informado",26)
    issue=date_br(q.get("date"))
    validity=min(365,max(1,int(st.get("quoteValidity") or 15)))
    entries=[it for it in (q.get("items") or []) if isinstance(it,dict)]
    def num(v):
        try:return float(v or 0)
        except (TypeError,ValueError):return 0
    discount=max(0,num(q.get("discount")))
    total=max(0,sum(num(it.get("qty"))*num(it.get("price")) for it in entries)-discount)
    page=0
    L=22;R=W-22
    def y(top):return H-top
    def box(x,top,w,h,bg,border=None,r=0):
        c.setFillColor(bg)
        if border:c.setStrokeColor(border);c.setLineWidth(.65)
        if r:c.roundRect(x,H-top-h,w,h,r,stroke=int(bool(border)),fill=1)
        else:c.rect(x,H-top-h,w,h,stroke=int(bool(border)),fill=1)
    def rule(x1,t1,x2,t2,col=GRID,w=.65):
        c.setStrokeColor(col);c.setLineWidth(w);c.line(x1,y(t1),x2,y(t2))
    def text(value,x,top,size=9,bold=False,color=INK,align="left",font=None):
        font=font or ("Helvetica-Bold" if bold else "Helvetica")
        c.setFont(font,size);c.setFillColor(color)
        fn={"left":c.drawString,"right":c.drawRightString,"center":c.drawCentredString}[align]
        fn(x,y(top+size),clean(value,300))
    def wrap(value,x,top,width,size=9,bold=False,color=INK,max_lines=3,step=12):
        font="Helvetica-Bold" if bold else "Helvetica"
        ln=lines_for(value,width,font,size,max_lines)
        for idx,row in enumerate(ln):text(row,x,top+idx*step,size,bold,color)
        return len(ln)
    def poly(points,col):
        p=c.beginPath();p.moveTo(points[0][0],y(points[0][1]))
        for a,b in points[1:]:p.lineTo(a,y(b))
        p.close();c.setFillColor(col);c.drawPath(p,stroke=0,fill=1)
    def badge_icon(kind,cx,cy):
        c.setLineWidth(1.7);c.setStrokeColor(WHITE)
        if kind=="energy":
            poly([(cx,cy-10),(cx-3,cy),(cx+2,cy),(cx-2,cy+12),(cx+9,cy-2),(cx+3,cy-2),(cx+6,cy-10)],GOLD)
        elif kind=="camera":
            box(cx-9,cy-5,18,11,NAVY,WHITE,2)
            c.circle(cx+1,y(cy+1),3,stroke=1,fill=0)
            rule(cx-4,cy+7,cx+5,cy+7,WHITE,1.2)
        elif kind=="internet":
            c.circle(cx,y(cy),9,stroke=1,fill=0)
            rule(cx-9,cy,cx+9,cy,WHITE,1)
            rule(cx,cy-9,cx,cy+9,WHITE,1)
            c.ellipse(cx-4,y(cy+9),cx+4,y(cy-9),stroke=1,fill=0)
        else:
            rule(cx-9,cy-8,cx+8,cy+9,WHITE,2)
            rule(cx-8,cy+9,cx+9,cy-8,WHITE,2)
    def draw_header(continuation=False):
        nonlocal page
        page+=1
        # Banner ultramarino, texturas e sobreposições diagonais.
        for j in range(50):
            f=j/49;col=HexColor("#%02x%02x%02x"%(int(2+f*2),int(12+f*8),int(28+f*22)))
            box(0,j*3.18,W,3.3,col)
        poly([(329,0),(388,0),(467,159),(407,159)],HexColor("#05386D"))
        poly([(345,0),(386,0),(467,159),(448,159)],HexColor("#0B5C9D"))
        poly([(460,0),(479,0),(552,159),(528,159)],HexColor("#06305B"))
        # Visor fotográfico opcional; desenho vetorial de câmera caso não exista arquivo.
        worker=Path(assets_dir or Path(__file__).resolve().parent/"thiago-reis-pro")/"quote-worker.jpg"
        if worker.exists():
            try:
                c.drawImage(ImageReader(str(worker)),W-207,H-110,207,110,preserveAspectRatio=False)
            except Exception:pass
        else:
            # Painel de equipamentos industriais, reflexos e câmera tubular.
            box(470,7,125,128,HexColor("#081522"))
            for x in (473,508,543,578):
                rule(x,5,x,134,HexColor("#253746"),.75)
            for t in range(15,132,24):
                rule(470,t,595,t,HexColor("#22394E"),.7)
            poly([(421,36),(483,31),(496,45),(481,71),(414,73)],HexColor("#A6B2BF"))
            poly([(420,40),(476,36),(478,65),(418,68)],HexColor("#E5EAF0"))
            c.setFillColor(HexColor("#22384D"));c.setStrokeColor(HexColor("#6C7C8D"));c.setLineWidth(4)
            c.circle(455,y(50),14,stroke=1,fill=1)
            c.setFillColor(HexColor("#0A1724"));c.circle(455,y(50),7,stroke=0,fill=1)
            c.setFillColor(HexColor("#182534"));c.circle(541,y(38),13,stroke=0,fill=1)
            poly([(522,57),(570,59),(591,140),(500,140)],HexColor("#111E2D"))
            poly([(503,73),(513,70),(529,105),(522,115)],HexColor("#273C52"))
        # Logomarca TR com camadas simulando relevo metálico.
        for dx,dy,col in [(3,3,HexColor("#0B3658")),(1.5,1.5,HexColor("#268CE0")),(0,0,WHITE)]:
            text("T",29+dx,8+dy,63,True,col)
        for dx,dy,col in [(3,3,HexColor("#073C72")),(1,1,HexColor("#0D5DA8")),(0,0,HexColor("#24A5FF"))]:
            text("R",74+dx,8+dy,62,True,col)
        poly([(78,37),(60,70),(70,70),(64,93),(91,58),(78,58),(87,37)],GOLD)
        text("THIAGO",138,27,26,True,WHITE)
        text("REIS",263,27,26,True,SKY)
        text("SERVIÇOS ELÉTRICOS E CÂMERAS",139,60,10.5,True,WHITE)
        # Quatro segmentos de especialidade.
        names=[("energy","ELÉTRICA","PREDIAL"),("camera","CFTV","E CÂMERAS"),("internet","REDES E","INTERNET"),("tools","MANUTENÇÃO","EM GERAL")]
        for i,(icon,a,b) in enumerate(names):
            cx=57+i*93
            badge_icon(icon,cx,98)
            text(a,cx,116,7.9,True,WHITE,"center")
            text(b,cx,127,7.7,True,WHITE,"center")
        # Dados de contato: somente contatos cadastrados/confirmados.
        box(412,115,183,39,HexColor("#04101F"))
        text("(14) 99660-0996" if digits=="14996600996" else phone,426,118,9.9,True,WHITE)
        text(clean(st.get("city") or "Iacanga - SP e região",29),426,134,8.3,False,WHITE)
        box(0,154,W,4,GOLD)
        if continuation:text("CONTINUAÇÃO DO ORÇAMENTO",22,163,8,True,MUTED)
    def draw_footer():
        box(0,815,W,27,NAVY)
        for i,lab in enumerate(("✓  SERVIÇO COM QUALIDADE","ATENDIMENTO PERSONALIZADO","SOLUÇÕES COMPLETAS","SUPORTE PÓS-SERVIÇO")):
            text(lab,15+i*149,823,6.8,True,WHITE)
    def finish_page():
        draw_footer()
        c.setFillColor(HexColor("#76879B"))
        c.setFont("Helvetica",7)
        c.drawRightString(W-17,y(804),"Página "+str(page))
        c.showPage()
    def new_page(continuation=False):
        if page:finish_page()
        draw_header(continuation)
    def section(title,t,icon=None):
        box(L,t,W-2*L,21,HexColor("#E8ECF1"),GRID,3)
        text(title,L+12,t+3,10.2,True,NAVY)
    def qr_at(x,top,size=70):
        if not wa:return
        try:
            qr=QrCodeWidget(wa)
            bounds=qr.getBounds()
            sx=size/(bounds[2]-bounds[0])
            sy=size/(bounds[3]-bounds[1])
            d=Drawing(size,size,transform=[sx,0,0,sy,0,0]);d.add(qr)
            renderPDF.draw(d,c,x,H-top-size)
        except Exception:pass
    def gallery(top):
        # Galeria fotográfica opcional; caso ausente, mini-ilustrações técnicas.
        photo=Path(assets_dir or Path(__file__).resolve().parent/"thiago-reis-pro")/"quote-gallery.jpg"
        if photo.exists():
            try:c.drawImage(ImageReader(str(photo)),L,H-top-55,W-2*L,55)
            except Exception:pass
        else:
            for k in range(6):
                x=L+k*93
                box(x,top,86,55,HexColor("#DCE2E7"),GRID,5)
                c.setStrokeColor(HexColor("#7A8895"));c.setLineWidth(1.2)
                if k in (0,5):
                    box(x+25,top+15,35,18,HexColor("#DEE9EE"),HexColor("#617486"),3)
                    c.circle(x+42,y(top+24),7,stroke=1,fill=0)
                    rule(x+42,top+33,x+42,top+45,HexColor("#70808D"),2)
                elif k in (1,3):
                    for n in range(5):
                        box(x+15+n*11,top+10,9,32,WHITE,GRID,1)
                        box(x+17+n*11,top+26,5,10,HexColor("#1E6BAA"))
                elif k==2:
                    for n in range(4):
                        for m in range(2):
                            box(x+10+n*15,top+9+m*19,12,12,HexColor("#184D73"))
                            c.setStrokeColor(SKY);c.line(x+17+n*15,y(top+13+m*19),x+17+n*15,y(top+25+m*19))
                else:
                    box(x+18,top+13,50,27,WHITE,HexColor("#6A7785"),4)
                    box(x+32,top+17,20,19,HexColor("#BBCBD7"),GRID,2)
    def seal(cx,cy):
        # Selo circular triplo, com faixas do modelo de referência.
        for radius,col in ((40,GOLD),(35,NAVY),(31,GOLD),(28,NAVY)):
            c.setFillColor(col);c.circle(cx,y(cy),radius,stroke=0,fill=1)
        text("QUALIDADE",cx,cy-19,8.9,True,GOLD,"center")
        text("SEGURANÇA",cx,cy-6,8.9,True,GOLD,"center")
        text("CONFIANÇA",cx,cy+7,8.9,True,GOLD,"center")
        text("★ ★ ★",cx,cy+22,9,True,GOLD,"center")
    def table_header(t):
        box(L,t,W-2*L,24,NAVY)
        for x in (67,323,382,468):rule(x,t,x,t+24,HexColor("#50708A"),.7)
        text("ITEM",L+10,t+6,8.8,True,WHITE)
        text("DESCRIÇÃO DO SERVIÇO",85,t+6,8.9,True,WHITE)
        text("QUANT.",361,t+6,8.5,True,WHITE,"right")
        text("VALOR UNIT. (R$)",457,t+6,8.5,True,WHITE,"right")
        text("VALOR TOTAL (R$)",W-30,t+6,8.5,True,WHITE,"right")
        return t+24
    new_page()
    # Bloco de identidade/emitente — sem endereço ou email fictícios.
    text(company.upper(),L+2,166,12.3,True,NAVY)
    text("CNPJ: "+cnpj,L+2,183,9.9,False,INK)
    text("WhatsApp: "+phone,L+2,199,8.8,False,INK)
    locality=st.get("address") or st.get("city") or "Iacanga - SP e região"
    text(clean(locality,49),L+2,213,8.7,False,INK)
    if st.get("email"):text(clean(st.get("email"),48),L+2,227,8.2,False,INK)
    box(414,166,159,64,WHITE,GRID,5)
    box(414,166,159,24,NAVY)
    text("ORÇAMENTO COMERCIAL",423,171,9.6,True,WHITE)
    text("Data: "+issue,423,195,9.2,True,INK)
    text("Validade: "+str(validity)+" dias",423,211,9.1,True,INK)
    section("DADOS DO CLIENTE",242)
    box(L,265,W-2*L,69,WHITE,GRID,5)
    text("Nome:",L+15,270,9,True,INK)
    wrap(cl.get("name") or "Não informado",L+58,270,235,9.1,False,INK,2,12)
    text("CPF/CNPJ:",340,270,8.5,True,INK)
    wrap(cl.get("document") or "Não informado",408,270,153,8.7,False,INK,1)
    text("Endereço:",L+15,291,9,True,INK)
    wrap(cl.get("address") or "Não informado",L+82,291,449,8.9,False,INK,2,11)
    text("Telefone:",L+15,314,9,True,INK)
    text(clean(cl.get("phone") or "Não informado",28),L+77,314,8.9)
    heading=clean(q.get("title") or "Serviços elétricos, câmeras e manutenção",120)
    text(heading,L+3,341,10.2,True,NAVY)
    t=table_header(360)
    for idx,it in enumerate(entries):
        desc=lines_for(it.get("desc") or "Serviço / material",227,"Helvetica",8.8,3)
        hh=max(22,9+len(desc)*11.5)
        if t+hh>535:
            new_page(True)
            t=table_header(183)
        box(L,t,W-2*L,hh,WHITE if idx%2 else HexColor("#F4F6F8"),GRID)
        text(f"{idx+1:02}",L+12,t+6,8.9)
        for li,row in enumerate(desc):text(row,85,t+5+li*11.5,8.8)
        qty=num(it.get("qty"));rate=num(it.get("price"))
        text((f"{qty:g}").replace(".",","),361,t+6,9,False,INK,"right")
        text(price(rate).replace("R$ ",""),457,t+6,8.9,False,INK,"right")
        text(price(qty*rate).replace("R$ ",""),W-30,t+6,9,True,INK,"right")
        t+=hh
    # O rodapé rico ocupa área fixa. Se couberem muitos itens, primeira página
    # vira tabela de continuação; resumo fica na última.
    if t>535:
        new_page(True);t=185
    bottom=max(t+9,550 if page==1 else 215)
    if discount:
        text("Desconto: -"+price(discount),W-28,bottom-16,8.9,True,MUTED,"right")
    box(L,bottom,W-2*L,43,NAVY,None,5)
    poly([(W-170,bottom),(W-149,bottom),(W-183,bottom+43),(W-205,bottom+43)],BLUE)
    text("TOTAL DO ORÇAMENTO",L+16,bottom+9,13,True,WHITE)
    text(price(total),W-17,bottom+7,19,True,GOLD,"right")
    t=bottom+49
    if page>1:
        # Continuations keep monetary details intact and final notes.
        section("CONDIÇÕES COMERCIAIS",t)
        t+=27
        text("Validade: "+str(validity)+" dias. Prazo de execução e pagamento: a combinar.",L+8,t,8.7)
        t+=18
        for row in lines_for(q.get("notes") or st.get("documentNotes") or "",530,"Helvetica",8.4,3):
            text(row,L+8,t,8.4);t+=12
        finish_page();out.seek(0)
        c.save()
        return out.getvalue()
    # Duas colunas de condições e informações, como a referência.
    t=max(t+9,607)
    text("CONDIÇÕES",L+2,t,10.4,True,NAVY)
    text("INFORMAÇÕES IMPORTANTES",W/2+12,t,10.4,True,NAVY)
    conditions=[
        "Validade do orçamento: "+str(validity)+" dias",
        "Prazo de execução: a combinar",
        "Forma de pagamento: a combinar",
        "Materiais: conforme orçamento"
    ]
    important=[
        "Este orçamento contempla os itens descritos.",
        "Alterações serão informadas previamente.",
        clean(q.get("notes") or st.get("documentNotes") or "Serviço sujeito à confirmação técnica.",140),
        "Atendimento em "+clean(st.get("city") or "Iacanga/SP e região",40)
    ]
    for idx,condition in enumerate(conditions):
        wrap("• "+condition,L+4,t+18+idx*13,263,7.7,False,INK,1)
    for idx,remark in enumerate(important):
        wrap("• "+remark,W/2+12,t+18+idx*13,252,7.7,False,INK,1)
    gallery(686)
    # WhatsApp QR é gerado de verdade com os dados reais da empresa.
    qr_at(L+3,751,57)
    box(89,749,162,61,NAVY,None,3)
    text("FALE COMIGO",99,756,11,True,WHITE)
    text("Solicite seu orçamento",99,772,8.6,False,WHITE)
    text("pelo WhatsApp",99,785,8.6,False,WHITE)
    text(phone,99,798,9,True,GOLD)
    text("Thiago Reis",366,756,19,False,HexColor("#153F76"),"center",font="Helvetica-Oblique")
    rule(275,783,458,783,NAVY,.9)
    text(company.upper(),366,787,8.8,True,NAVY,"center")
    text("Responsável técnico / comercial",366,800,7.8,False,MUTED,"center")
    seal(530,769)
    draw_footer();c.save();out.seek(0)
    return out.getvalue()
