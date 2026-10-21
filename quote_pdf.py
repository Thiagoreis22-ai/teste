"""Gerador de propostas comerciais A4 — identidade Thiago Reis preto e ouro."""
from io import BytesIO
from pathlib import Path
import re
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

W, H = 595.28, 841.89
DARK=HexColor('#0B1019')
GOLD=HexColor('#DEAC4A')
GOLD_LIGHT=HexColor('#F7DA91')
INK=HexColor('#1C2938')
MUTED=HexColor('#687485')
GRID=HexColor('#DFE4EA')
PALE=HexColor('#F6F7F9')
WHITE=HexColor('#FFFFFF')

def safe(value,limit=240):
    s=re.sub(r'\s+',' ',str(value if value is not None else '—')).strip()
    return (s or '—')[:limit]

def brl(value):
    try: n=float(value or 0)
    except (TypeError,ValueError): n=0
    if not -1e12<n<1e12: n=0
    return 'R$ '+f'{n:,.2f}'.replace(',','X').replace('.',',').replace('X','.')

def wrap(value,width,font='Helvetica',size=9,max_lines=4):
    s=safe(value,700);lines=[]
    for raw in s.split(' '):
        word=raw
        while word and stringWidth(word,font,size)>width:
            k=1
            while k<len(word) and stringWidth(word[:k+1],font,size)<=width:k+=1
            lines.append(word[:k]);word=word[k:]
        if not word:continue
        if lines and stringWidth(lines[-1]+' '+word,font,size)<=width:lines[-1]+=' '+word
        else:lines.append(word)
    if len(lines)>max_lines:
        lines=lines[:max_lines]
        while len(lines[-1])>1 and stringWidth(lines[-1]+'…',font,size)>width:lines[-1]=lines[-1][:-1]
        lines[-1]+='…'
    return lines or ['—']

def build_quote_pdf(quote,client,settings,assets_dir=None):
    out=BytesIO();c=canvas.Canvas(out,pagesize=(W,H),pageCompression=1)
    c.setTitle('Orçamento Comercial | Thiago Reis')
    c.setAuthor(safe(settings.get('company') or 'Thiago Reis',100))
    page=0;LEFT=33;RIGHT=W-33
    def rect(x,top,w,h,fill,stroke=None,radius=0):
        c.setFillColor(fill)
        if stroke:c.setStrokeColor(stroke)
        if radius:c.roundRect(x,H-top-h,w,h,radius,stroke=bool(stroke),fill=1)
        else:c.rect(x,H-top-h,w,h,stroke=bool(stroke),fill=1)
    def line(x1,y1,x2,y2,color=GRID,width=.8):
        c.setStrokeColor(color);c.setLineWidth(width);c.line(x1,H-y1,x2,H-y2)
    def tx(value,x,top,size=9,bold=False,color=INK,align='left'):
        c.setFillColor(color);c.setFont('Helvetica-Bold' if bold else 'Helvetica',size)
        draw={'left':c.drawString,'right':c.drawRightString,'center':c.drawCentredString}[align]
        draw(x,H-top-size,safe(value,350))
    def write(value,x,top,width,size=9,color=INK,max_lines=3,bold=False,leading=None):
        font='Helvetica-Bold' if bold else 'Helvetica'
        lines=wrap(value,width,font,size,max_lines)
        for i,row in enumerate(lines):tx(row,x,top+i*(leading or size*1.45),size,bold,color)
        return len(lines)*(leading or size*1.45)
    def heading(title,top):
        rect(LEFT,top,4,19,GOLD)
        tx(title,LEFT+14,top+2,10,True,DARK)
        line(LEFT+14,top+20,RIGHT,top+20)
    def footer():
        line(LEFT,797,RIGHT,797,GOLD,1.1)
        tx('THIAGO REIS',LEFT,805,8.8,True,DARK)
        tx('ELÉTRICA  •  CÂMERAS  •  CONFIANÇA',128,805,7.9,False,MUTED)
        tx('PÁGINA '+str(page),RIGHT,805,8,False,MUTED,'right')
        tx('Documento comercial. Não substitui a Nota Fiscal de Serviço Eletrônica (NFS-e).',LEFT,821,7.4,False,MUTED)
    def header(continued=False):
        nonlocal page
        page+=1
        rect(0,0,W,153,DARK)
        c.setFillColor(HexColor('#111C2A'))
        poly=c.beginPath();poly.moveTo(470,H);poly.lineTo(510,H);poly.lineTo(580,H-153);poly.lineTo(540,H-153);poly.close();c.drawPath(poly,stroke=0,fill=1)
        c.setFillColor(HexColor('#76501F'))
        poly=c.beginPath();poly.moveTo(540,H);poly.lineTo(559,H);poly.lineTo(W,H-102);poly.lineTo(W,H-146);poly.close();c.drawPath(poly,stroke=0,fill=1)
        rect(0,149,W,4,GOLD)
        rect(27,23,91,94,HexColor('#141B27'),HexColor('#8F6B30'),9)
        logo=Path(assets_dir or Path(__file__).resolve().parent/'thiago-reis-pro')/'icon-512.png'
        if logo.exists():c.drawImage(ImageReader(str(logo)),33,H-110,79,79,mask='auto',preserveAspectRatio=True)
        else:tx('TR',43,51,30,True,GOLD_LIGHT)
        tx('THIAGO',135,34,28,True,WHITE)
        tx('REIS',267,34,28,True,GOLD_LIGHT)
        tx('ELÉTRICA PREDIAL  •  CÂMERAS  •  SEGURANÇA',136,70,9.35,True,GOLD_LIGHT)
        tx('INSTALAÇÃO  •  MANUTENÇÃO  •  CFTV',136,91,8,False,HexColor('#D2D6DE'))
        for idx,name in enumerate(['ELÉTRICA PREDIAL','CFTV & CÂMERAS','REDES & INTERNET','MANUTENÇÃO']):
            x=33+idx*135.3
            rect(x,124,126.5,19,HexColor('#27303C'),HexColor('#45413B'),3)
            tx(name,x+8,128.5,7.7,True,GOLD_LIGHT)
        if continued:tx('CONTINUAÇÃO DA PROPOSTA',35,163,8,True,MUTED)
    def next_page(continued=False):
        if page:footer();c.showPage()
        header(continued)
    def th(top):
        rect(LEFT,top,529,31,DARK)
        tx('ITEM',42,top+8.1,8.1,True,GOLD_LIGHT)
        tx('SERVIÇO / MATERIAL',83,top+8.1,8.1,True,WHITE)
        tx('QTD.',362,top+8.1,8.1,True,WHITE,'right')
        tx('UNITÁRIO',457,top+8.1,8.1,True,WHITE,'right')
        tx('VALOR',551,top+8.1,8.1,True,WHITE,'right')
        return top+31

    next_page()
    tx(safe(settings.get('company') or 'Thiago Reis',40).upper(),33,168,12.4,True,DARK)
    tx('CNPJ: '+safe(settings.get('cnpj') or 'Não informado',34),33,187,9.6,True,INK)
    tx('WhatsApp: '+safe(settings.get('phone') or 'Não informado',30),33,204,9.1,False,MUTED)
    tx(safe(settings.get('address') or settings.get('city') or 'Iacanga/SP e região',58),33,220,8.7,False,MUTED)
    if settings.get('email'):tx(safe(settings.get('email'),48),33,235,8.6,False,MUTED)
    rect(370,169,193,78,DARK,None,6);rect(370,169,4,78,GOLD)
    tx('ORÇAMENTO COMERCIAL',385,180,11.3,True,GOLD_LIGHT)
    date=safe(quote.get('date') or '',15)
    if re.match(r'^\d{4}-\d{2}-\d{2}$',date):date=date[8:10]+'/'+date[5:7]+'/'+date[:4]
    tx('Emissão: '+date,385,205,9.4,False,WHITE)
    validity=max(1,min(365,int(settings.get('quoteValidity') or 15)))
    tx('Validade: '+str(validity)+' dias',385,223,9.4,False,WHITE)

    heading('INFORMAÇÕES DO CLIENTE',261)
    rect(LEFT,289,529,76,PALE,GRID,5)
    tx('CLIENTE',44,296,8,True,MUTED)
    write(client.get('name') or 'Não informado',44,309,285,10,INK,2,True,12)
    tx('CPF / CNPJ',350,296,8,True,MUTED)
    write(client.get('document') or 'Não informado',350,309,194,9.5,INK,2,False,11.5)
    tx('CONTATO',44,333,8,True,MUTED)
    tx(safe(client.get('phone') or 'Não informado',30),44,346,9,False,INK)
    tx('LOCAL DO SERVIÇO',350,333,8,True,MUTED)
    write(client.get('address') or 'Não informado',350,346,198,8.6,INK,2,False,10.5)

    heading('DESCRIÇÃO DOS SERVIÇOS',378)
    write(quote.get('title') or 'Serviços elétricos e câmeras',45,407,503,10,INK,2,True,13)
    y=th(443)
    items=quote.get('items') or []
    for idx,item in enumerate(items):
        if not isinstance(item,dict):continue
        rows=wrap(item.get('desc') or 'Serviço / material',258,'Helvetica',9.1,4)
        height=max(32,14+len(rows)*13)
        if y+height>685:
            next_page(True);heading('ITENS DO ORÇAMENTO',186);y=th(225)
        rect(LEFT,y,529,height,WHITE if idx%2 else PALE,GRID)
        tx(f'{idx+1:02}',42,y+8,9,False,MUTED)
        for j,row in enumerate(rows):tx(row,83,y+8+j*12.5,9.1,False,INK)
        try:qty=float(item.get('qty') or 0)
        except (ValueError,TypeError):qty=0
        try:unit=float(item.get('price') or 0)
        except (ValueError,TypeError):unit=0
        tx(f'{qty:g}'.replace('.',','),362,y+8,9,False,INK,'right')
        tx(brl(unit),457,y+8,9,False,INK,'right')
        tx(brl(unit*qty),551,y+8,9,True,DARK,'right')
        y+=height
    if not items:
        rect(LEFT,y,529,38,WHITE,GRID);tx('Nenhum item informado.',46,y+12,9,False,MUTED);y+=38
    remarks=[safe(v,400) for v in [quote.get('notes'),settings.get('documentNotes')] if v and str(v).strip()]
    notes=[row for note in remarks[:2] for row in wrap(note,506,'Helvetica',8.9,3)]
    try:discount=max(0,float(quote.get('discount') or 0))
    except (ValueError,TypeError):discount=0
    # Reserva espaço para total, condições e observações, sem criar página vazia.
    if y+143+len(notes)*13+(17 if discount else 0)>775:next_page(True);y=194
    y+=15
    if discount:
        tx('Desconto aplicado',348,y-4,9,False,MUTED)
        tx('- '+brl(discount),551,y-4,9.5,True,INK,'right');y+=17
    total=sum((float(item.get('qty') or 0)*float(item.get('price') or 0) for item in items if isinstance(item,dict)),0)-discount
    rect(LEFT,y,529,54,DARK,None,4);rect(LEFT,y,4,54,GOLD)
    tx('VALOR TOTAL DA PROPOSTA',49,y+15,11.1,True,WHITE)
    tx(brl(total),548,y+10,20,True,GOLD_LIGHT,'right')
    y+=73;heading('CONDIÇÕES COMERCIAIS',y);y+=31
    tx('Validade da proposta: '+str(validity)+' dias',43,y,8.7,False,INK)
    tx('Execução e pagamento: a combinar',296,y,8.7,False,INK)
    y+=17
    tx('Materiais e deslocamento: conforme os itens descritos no orçamento.',43,y,8.6,False,MUTED)
    y+=16
    for row in notes:
        if y>744:next_page(True);y=197
        tx('• '+row,43,y,8.9,False,INK);y+=13
    y+=20
    if y+31<789:
        line(349,y,554,y,MUTED,.9)
        tx(safe(settings.get('company') or 'Thiago Reis',40),452,y+6,9,True,DARK,'center')
        tx('Responsável técnico / comercial',452,y+20,7.6,False,MUTED,'center')
    footer();c.save();out.seek(0)
    return out.getvalue()
