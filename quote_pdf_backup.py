"""Fallback A4 robusto para PDFs de orçamentos; dados reais, sem numeração pública."""
from io import BytesIO
from datetime import date
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth

W,H=595.276,841.89
DARK=HexColor("#071827"); GOLD=HexColor("#d7aa4f"); WHITE=HexColor("#ffffff"); INK=HexColor("#15273a"); GRAY=HexColor("#627080"); BLINE=HexColor("#e1e6ea")

def plain(value, max_chars=300):
    try:
        t=str(value or "").replace("\n"," ").replace("\r"," ").strip()
    except (ValueError,TypeError):
        t=""
    return t[:max_chars]

def numeric(value):
    try:
        if isinstance(value,str) and "," in value:
            value=value.replace(".","").replace(",",".")
        f=float(value or 0)
        if f!=f or abs(f)>1e12:return 0.
        return max(0.,f)
    except (TypeError,ValueError,OverflowError):
        return 0.

def brl(n):
    return "R$ "+f"{numeric(n):,.2f}".replace(",","_").replace(".",",").replace("_",".")

def wrap(text,width,font="Helvetica",size=9):
    t=plain(text,3000);out=[];current=""
    for word in t.split():
        while stringWidth(word,font,size)>width and len(word)>1:
            pivot=max(1,len(word)//2)
            while pivot>1 and stringWidth(word[:pivot],font,size)>width:pivot-=1
            if current:out.append(current);current=""
            out.append(word[:pivot]);word=word[pivot:]
        line=(current+" "+word).strip()
        if current and stringWidth(line,font,size)>width:
            out.append(current);current=word
        else:current=line
    if current:out.append(current)
    return out or ["-"]

def build_backup_quote_pdf(quote,client,settings):
    quote=quote if isinstance(quote,dict) else {}
    client=client if isinstance(client,dict) else {}
    settings=settings if isinstance(settings,dict) else {}
    out=BytesIO();c=canvas.Canvas(out,pagesize=(W,H),pageCompression=1)
    c.setTitle("Orçamento Comercial - Thiago Reis")
    c.setAuthor(plain(settings.get("company") or "Thiago Reis",80))
    page=0;top=0
    def rectangle(x,t,w,h,fill):
        c.setFillColor(fill);c.rect(x,H-t-h,w,h,stroke=0,fill=1)
    def txt(s,x,t,size=9,bold=False,color=INK,right=False):
        c.setFillColor(color);c.setFont("Helvetica-Bold" if bold else "Helvetica",size)
        method=c.drawRightString if right else c.drawString
        method(x,H-t-size,plain(s,400))
    def row(s,x,t,w,max_rows=3,size=9):
        for idx,line in enumerate(wrap(s,w,size=size)[:max_rows]):
            txt(line,x,t+idx*13,size)
        return max(1,min(max_rows,len(wrap(s,w,size=size))))*13
    def end():
        rectangle(0,806,W,36,DARK)
        txt("THIAGO REIS • ORÇAMENTO COMERCIAL",33,816,8,True,GOLD)
        txt("Documento comercial não fiscal  |  Página "+str(page),W-33,816,7,False,WHITE,True)
        c.showPage()
    def new_page(title="ORÇAMENTO COMERCIAL"):
        nonlocal page,top
        if page:end()
        page+=1;rectangle(0,0,W,120,DARK)
        rectangle(0,115,W,5,GOLD)
        txt("TR",32,18,47,True,GOLD)
        txt(plain(settings.get("company") or "THIAGO REIS",48).upper(),116,27,20,True,WHITE)
        txt("ELETRICISTA PREDIAL  •  CFTV  •  MANUTENÇÃO",117,60,9,False,GOLD)
        txt(title,33,131,14,True,DARK)
        top=158
    def section(label):
        nonlocal top
        rectangle(33,top,W-66,21,HexColor("#e7edf2"))
        rectangle(33,top,4,21,GOLD)
        txt(label,44,top+4,10,True,INK)
        top+=31
    new_page()
    txt("CNPJ: "+plain(settings.get("cnpj") or "Não informado"),33,162,9,True)
    txt("Telefone: "+plain(settings.get("phone") or "Não informado"),33,176,9)
    txt(plain(settings.get("address") or settings.get("city") or "Iacanga - SP e região"),33,190,9)
    top=214;section("DADOS DO CLIENTE")
    top+=row("Cliente: "+plain(client.get("name") or "Não informado"),42,top,498)
    top+=row("Documento: "+plain(client.get("document") or "Não informado"),42,top,498)
    top+=row("Telefone: "+plain(client.get("phone") or "Não informado"),42,top,498)
    top+=row("Endereço: "+plain(client.get("address") or "Não informado"),42,top,498,2)
    top+=12;section("SERVIÇOS E MATERIAIS")
    top+=row(quote.get("title") or "Serviços elétricos e câmeras",42,top,492,3,10)
    top+=6;rectangle(33,top,W-66,24,DARK)
    txt("SERVIÇO / MATERIAL",42,top+5,9,True,WHITE)
    txt("TOTAL",W-42,top+5,9,True,GOLD,True)
    top+=28
    rows=quote.get("items") or []
    subtotal=0.
    if not isinstance(rows,list):rows=[]
    for it in rows[:400]:
        if not isinstance(it,dict):continue
        qty=numeric(it.get("qty"));unit=numeric(it.get("price"))
        amount=qty*unit;subtotal+=amount
        details=wrap(plain(it.get("desc") or "Serviço")+" • "+str(qty).replace(".",",")+" x "+brl(unit),315, size=8.7)[:4]
        ht=max(29,len(details)*12+11)
        if top+ht>735:
            new_page("ORÇAMENTO • CONTINUAÇÃO");top=176
            rectangle(33,top,W-66,24,DARK)
            txt("SERVIÇO / MATERIAL",42,top+5,9,True,WHITE)
            txt("TOTAL",W-42,top+5,9,True,GOLD,True)
            top+=28
        if rows.index(it)%2==0:rectangle(33,top,W-66,ht,HexColor("#f3f6f8"))
        for idx,line in enumerate(details):txt(line,42,top+6+idx*12,8.7)
        txt(brl(amount),W-42,top+6,9,True,INK,True)
        top+=ht
    discount=numeric(quote.get("discount"))
    total=max(0,subtotal-discount)
    if top+140>760:new_page("ORÇAMENTO • RESUMO");top=179
    top+=10
    if discount:
        txt("Desconto aplicado: "+brl(discount),W-42,top,9,False,GRAY,True);top+=22
    rectangle(33,top,W-66,48,DARK)
    txt("TOTAL DO ORÇAMENTO",45,top+14,13,True,WHITE)
    txt(brl(total),W-44,top+10,18,True,GOLD,True)
    top+=65;section("CONDIÇÕES COMERCIAIS")
    days=plain(settings.get("quoteValidity") or 15)
    txt("Validade: "+days+" dias. Pagamento e execução: a combinar.",42,top,9)
    top+=17
    note=plain(quote.get("notes") or settings.get("documentNotes") or "Os itens estão sujeitos à aprovação do cliente.",400)
    top+=row(note,42,top,494,3,8.8)
    end();c.save()
    return out.getvalue()
