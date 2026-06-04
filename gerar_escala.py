# -*- coding: utf-8 -*-
"""
Motor de escala 24h - Centro de Operacoes (sistema de LETRAS).
- Manha (so de manha): 6x3, letras A/B/C defasadas.
- Tarde (so de tarde): 6x3, letras A/B/C defasadas.
- Madrugada (letra D): ciclo 2M-2T-2N-4F (10 dias). Postos fixos no dia,
  cobre os 5 postos noturnos consolidados. Dia que sai 7h conta como trabalhado.
- Projecao de 2 anos, visoes amigaveis, substituicao ranqueada, banco de pesos, HE.
Saida: Escala_Centro_Operacoes.xlsx
"""
import openpyxl, random
from datetime import date, timedelta
from collections import defaultdict
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule, CellIsRule

random.seed(7)

# ----------------------------------------------------------- paleta / estilos
C_TIT="1F4E2E"; C_HDR="2E7D32"; C_MANHA="C8E6C9"; C_TARDE="BBDEFB"
C_MAD ="455A64"; C_FOLGA="E0E0E0"; C_FERIAS="FFF59D"; C_RES="DCEDC8"
C_HE ="FFCC80"; C_AMAR="FFF2CC"; C_VERM="EF9A9A"; C_BAND="F1F8E9"
def P(h): return PatternFill("solid", fgColor=h)
WB_=Font(bold=True,color="FFFFFF"); B_=Font(bold=True)
TIT=Font(bold=True,size=16,color="FFFFFF"); SUB=Font(bold=True,size=11,color="FFFFFF")
THIN=Side(style="thin",color="C8C8C8")
BORDA=Border(left=THIN,right=THIN,top=THIN,bottom=THIN)
CEN=Alignment(horizontal="center",vertical="center",wrap_text=True)
ESQ=Alignment(horizontal="left",vertical="center",wrap_text=True)
def sr(ws,rng,fill=None,font=None,border=BORDA,align=CEN):
    for row in ws[rng]:
        for c in row:
            if fill: c.fill=fill
            if font: c.font=font
            if border: c.border=border
            if align: c.alignment=align

# ----------------------------------------------------------- nomes ficticios
PRI=["Alexandre","Bruna","Caio","Daniela","Eduardo","Fernanda","Gustavo","Helena","Igor",
"Juliana","Kleber","Larissa","Marcos","Natalia","Otavio","Patricia","Rafael","Sabrina",
"Thiago","Vanessa","Wagner","Yasmin","Bernardo","Camila","Diego","Elaine","Fabio","Gabriela",
"Henrique","Isabela","Joao","Karina","Lucas","Mariana","Nelson","Olivia","Paulo","Renata",
"Sergio","Tatiana","Ulisses","Viviane","Wesley","Adriana","Breno","Cintia","Davi","Erika",
"Felipe","Giovana","Hugo","Ines","Jonas","Keila","Leandro","Monica","Nicolas","Priscila",
"Ramon","Silvia","Tarcisio","Ursula","Vitor","Wanda","Anderson","Beatriz","Cesar","Debora",
"Emerson","Flavia","Gilberto","Heloisa","Ivan","Jaqueline","Kaua","Luana","Mateus","Nadia",
"Osmar","Poliana","Rodrigo","Simone","Tomas","Ulisses2","Valeria","Wilson","Amanda","Bruno",
"Carla","Denis","Edna","Fabricio","Gisele","Hamilton","Iara","Jefferson","Lia","Murilo",
"Noemia","Octavio","Paula","Quesia","Rebeca","Saulo","Talita","Vagner"]
SOB=["Silva","Souza","Oliveira","Pereira","Costa","Almeida","Nunes","Carvalho","Rocha","Gomes",
"Martins","Araujo","Ribeiro","Barbosa","Teixeira","Cardoso","Moraes","Lima","Freitas","Pinto",
"Moreira","Cavalcanti","Dias","Castro","Campos","Macedo","Andrade","Vieira","Mendes","Tavares",
"Correia","Ramos","Azevedo","Batista","Fonseca","Cunha","Brandao","Siqueira","Pacheco","Reis"]
def gen_nomes(n):
    res=[]; seen=set(); i=0
    while len(res)<n:
        nm=f"{PRI[i%len(PRI)]} {SOB[(i*7)%len(SOB)]}"
        if nm not in seen: seen.add(nm); res.append(nm)
        i+=1
    return res

# ----------------------------------------------------------- postos
DIURNOS=["BH/NL","SG/AR","BT","SL","GV","RA/PO","TO/PR","IP/AG","DV/IJ","FM/CL","IA/CR",
"MO/SI","PT/AL","JN/BC","JB/PI","JF/OP","PN/LV","LF/BD","UL/IR","PM/PS","TB/AF"]   # 21
REGIONAIS=["RG1-Centro","RG2-Leste","RG3-Oeste","RG4-Norte","RG5-Sul"]            # 5 (24h)
APOIO=["AP-1","AP-2"]
NPD=len(DIURNOS)  # 21

# ----------------------------------------------------------- efetivos
N_MANHA=36; N_TARDE=36; N_MAD=33; N_APOIO=3
TOTAL=N_MANHA+N_TARDE+N_MAD+N_APOIO
NOMES=gen_nomes(TOTAL)

emp=[]; idx=0
def add(grupo, letra, home, turno):
    global idx
    emp.append({"id":idx+1,"nome":NOMES[idx],"grupo":grupo,"letra":letra,
                "home":home,"turno":turno}); idx+=1
# Manha: letras A/B/C defasadas 3 dias; home posto distribui entre os 21
for i in range(N_MANHA):
    letra="ABC"[(i+i//NPD)%3]
    add("Manha", letra, DIURNOS[i%NPD], "07:00-15:30")
for i in range(N_TARDE):
    letra="ABC"[(i+i//NPD)%3]
    add("Tarde", letra, DIURNOS[i%NPD], "15:00-23:30")
# Madrugada letra D: home = um regional
for i in range(N_MAD):
    add("Madrugada","D",REGIONAIS[i%5],"Rod. 2M-2T-2N-4F")
# Apoio
for i in range(N_APOIO):
    add("Apoio","-",APOIO[i%2],"Apoio seg-sex 07h-15h")

emp_by_id={e["id"]:e for e in emp}
LET_OFF={"A":0,"B":3,"C":6}   # defasagem das letras no ciclo 9 dias (6x3)

# ----------------------------------------------------------- conhecimento
pts={}; last={}
for e in emp:
    pts[(e["id"],e["home"])]=random.randint(160,420); last[(e["id"],e["home"])]=-2
def eff(eid,p,day):
    if (eid,p) not in pts: return 0
    return max(0, pts[(eid,p)]-max(0,(day-last[(eid,p)])-180))
def credita(eid,p,day):
    pts[(eid,p)]=pts.get((eid,p),0)+1; last[(eid,p)]=day

# ferias: 2 janelas de 30 dias por pessoa, escalonadas
for e in emp:
    base=20+(e["id"]*11)%310
    e["ferias"]=set(d for w in (base,base+365) for d in range(w,w+30) if 0<=d<730)

# ----------------------------------------------------------- motor
D0=date(2026,6,4); DIAS=730
status=[["" for _ in range(DIAS)] for _ in range(TOTAL)]  # texto por pessoa/dia
he_events=[]; descobertos=0
he_month=defaultdict(float)   # (eid, "MM/YYYY") -> horas no mes
def mes_de(day): return (D0+timedelta(days=day)).strftime("%m/%Y")
manha=[e for e in emp if e["grupo"]=="Manha"]
tarde=[e for e in emp if e["grupo"]=="Tarde"]
mad  =[e for e in emp if e["grupo"]=="Madrugada"]
apoio=[e for e in emp if e["grupo"]=="Apoio"]

def working_6x3(e,day):           # True se trabalha (6x3 conforme letra)
    return ((day-LET_OFF[e["letra"]])%9)<6

def mad_pos(e,day):               # posicao no ciclo 2M2T2N4F -> 'M','T','N','F'
    ph=(day-(e["id"]%10))%10
    return "MM TT NN FFFF".replace(" ","")[ph]  # MMTTNNFFFF

def fill(seats, candidatos, day, prefix):
    """seats: lista de postos a cobrir; candidatos: pessoas disponiveis.
       prioriza home posto, depois quem estava ontem, depois conhecimento."""
    global descobertos
    assigned={}; pool=list(candidatos); used=set()
    # 1) quem esta no proprio home e disponivel
    for e in list(pool):
        if e["home"] in seats and e["home"] not in assigned:
            assigned[e["home"]]=e["id"]; used.add(e["id"]); pool.remove(e)
    # 2) demais seats por conhecimento+ontem
    for s in [x for x in seats if x not in assigned]:
        if not pool: break
        def sc(e):
            ont=1 if day>0 and status[e["id"]-1][day-1].endswith(s) else 0
            return (eff(e["id"],s,day),ont,-e["id"])
        best=max(pool,key=sc); assigned[s]=best["id"]; used.add(best["id"]); pool.remove(best)
    leftover=pool
    return assigned, leftover

def aplica(assigned, seats, prefix, day, folga_pool):
    """grava status + credita; cobre buracos com HE."""
    global descobertos
    for s in seats:
        if s in assigned:
            eid=assigned[s]; status[eid-1][day]=f"{prefix} {s}"; credita(eid,s,day)
        else:
            cand=[e for e in folga_pool if status[e["id"]-1][day]=="FOLGA"]
            if cand:
                mes=mes_de(day)
                # prioriza quem tem MENOS HE no mes (respeita teto 52h), depois conhecimento
                sob=[e for e in cand if he_month[(e["id"],mes)]+8.5<=52]
                escolha=sob if sob else cand
                best=max(escolha,key=lambda e:(-he_month[(e["id"],mes)],eff(e["id"],s,day),-e["id"]))
                status[best["id"]-1][day]=f"{prefix} {s} *HE"
                he_month[(best["id"],mes)]+=8.5
                he_events.append((day,s,best["id"])); credita(best["id"],s,day)
            else:
                descobertos+=1

for day in range(DIAS):
    wd=(D0+timedelta(days=day)).weekday()
    # ---- MANHA (21 diurnos)
    disp=[]; folg=[]
    for e in manha:
        if day in e["ferias"]: status[e["id"]-1][day]="FERIAS"
        elif working_6x3(e,day): disp.append(e)
        else: status[e["id"]-1][day]="FOLGA"; folg.append(e)
    a,left=fill(DIURNOS,disp,day,"M"); aplica(a,DIURNOS,"M",day,folg)
    for e in left:
        if not status[e["id"]-1][day]: status[e["id"]-1][day]="RESERVA"
    # ---- TARDE (21 diurnos)
    disp=[]; folg=[]
    for e in tarde:
        if day in e["ferias"]: status[e["id"]-1][day]="FERIAS"
        elif working_6x3(e,day): disp.append(e)
        else: status[e["id"]-1][day]="FOLGA"; folg.append(e)
    a,left=fill(DIURNOS,disp,day,"T"); aplica(a,DIURNOS,"T",day,folg)
    for e in left:
        if not status[e["id"]-1][day]: status[e["id"]-1][day]="RESERVA"
    # ---- MADRUGADA letra D (5 regionais, 3 turnos)
    pos={e["id"]:mad_pos(e,day) for e in mad}
    for e in mad:
        if day in e["ferias"]: status[e["id"]-1][day]="FERIAS"
    # marca folga (posicao F) antes, para servir de pool de hora extra
    folga_d=[e for e in mad if pos[e["id"]]=="F" and day not in e["ferias"]]
    for e in folga_d: status[e["id"]-1][day]="FOLGA"
    for turno in ("M","T","N"):
        disp=[e for e in mad if pos[e["id"]]==turno and day not in e["ferias"] and not status[e["id"]-1][day]]
        a,left=fill(REGIONAIS,disp,day,turno); aplica(a,REGIONAIS,turno,day,folga_d)
        for e in left:
            if not status[e["id"]-1][day]: status[e["id"]-1][day]="RESERVA"
    for e in mad:
        if not status[e["id"]-1][day]: status[e["id"]-1][day]="FOLGA"
    # ---- APOIO (seg-sex, manha)
    for j,e in enumerate(apoio):
        if wd>=5: status[e["id"]-1][day]="FOLGA"
        elif day in e["ferias"]: status[e["id"]-1][day]="FERIAS"
        elif (day%3)==j: status[e["id"]-1][day]="FOLGA"   # rod. simples
        else:
            s=APOIO[j%2]; status[e["id"]-1][day]=f"M {s}"; credita(e["id"],s,day)

# ============================================================ WORKBOOK
wb=openpyxl.Workbook()
DATAS=[D0+timedelta(days=d) for d in range(DIAS)]

# ---------------- ABA INICIO (dashboard)
wi=wb.active; wi.title="INICIO"; wi.sheet_view.showGridLines=False
for c in "ABCDEFGH": wi.column_dimensions[c].width=15
wi.column_dimensions["A"].width=3
wi.merge_cells("B2:H2"); wi["B2"]="CONTROLE DE ESCALA  -  CENTRO DE OPERACOES 24h"
wi["B2"].fill=P(C_TIT); wi["B2"].font=TIT; wi["B2"].alignment=CEN; wi.row_dimensions[2].height=34
wi.merge_cells("B3:H3"); wi["B3"]="Projecao de 2 anos | Sistema de letras (A/B/C de dia + D na madrugada)"
wi["B3"].fill=P(C_HDR); wi["B3"].font=SUB; wi["B3"].alignment=CEN
# cards
cards=[("EFETIVO TOTAL",TOTAL,C_HDR),("MANHA (A/B/C)",N_MANHA,C_MANHA),
       ("TARDE (A/B/C)",N_TARDE,C_TARDE),("MADRUGADA (D)",N_MAD,C_MAD),("APOIO",N_APOIO,C_AMAR)]
col=2
for nome,val,cor in cards:
    wi.merge_cells(start_row=5,start_column=col,end_row=5,end_column=col+1)
    wi.merge_cells(start_row=6,start_column=col,end_row=7,end_column=col+1)
    tcol="FFFFFF" if cor in (C_HDR,C_MAD) else "1F4E2E"
    h=wi.cell(5,col,nome); h.fill=P(cor); h.font=Font(bold=True,color=tcol); h.alignment=CEN
    v=wi.cell(6,col,val); v.fill=P(cor); v.font=Font(bold=True,size=22,color=tcol); v.alignment=CEN
    for rr in (5,6,7):
        for cc in (col,col+1): wi.cell(rr,cc).border=BORDA; wi.cell(rr,cc).fill=P(cor)
    col+=2
wi.row_dimensions[6].height=30
# como usar
wi.merge_cells("B9:H9"); wi["B9"]="COMO USAR ESTE ARQUIVO (abas na ordem)"; wi["B9"].font=B_; wi["B9"].fill=P(C_BAND)
guia=[
 ("Dimensionamento","Quantos funcionarios e por que."),
 ("Funcionarios","Cadastro: grupo, letra e posto fixo de cada pessoa."),
 ("Postos","Lista dos 21 postos diurnos + 5 regionais 24h + 2 de apoio."),
 ("Calendario","Grade de 2 anos: cada pessoa x cada dia (com cores)."),
 ("Visao do Dia","Escolha uma DATA e veja quem esta em cada posto, por turno."),
 ("Visao por Pessoa","Escolha a PESSOA e veja a escala e os totais dela."),
 ("Substituicao","Faltou alguem? Veja o melhor substituto ja ranqueado."),
 ("Banco Conhecimento","Pontos de cada pessoa em cada posto (com decaimento)."),
 ("Horas Extras","Controle mensal com limite de 52h/mes."),
]
r=10
for nome,desc in guia:
    wi.cell(r,2,nome).font=B_; wi.cell(r,2).fill=P(C_MANHA); wi.cell(r,2).border=BORDA
    wi.merge_cells(start_row=r,start_column=3,end_row=r,end_column=8)
    wi.cell(r,3,desc).alignment=ESQ; wi.cell(r,3).border=BORDA; r+=1
# legenda de cores
r+=1; wi.cell(r,2,"LEGENDA DE CORES").font=B_; wi.cell(r,2).fill=P(C_BAND); r+=1
leg=[("Manha (07:00-15:30)",C_MANHA),("Tarde (15:00-23:30)",C_TARDE),
     ("Madrugada (23:00-07:30)",C_MAD),("Folga",C_FOLGA),("Ferias",C_FERIAS),
     ("Reserva",C_RES),("Hora Extra (*HE)",C_HE)]
for nome,cor in leg:
    wi.cell(r,2).fill=P(cor); wi.cell(r,2).border=BORDA
    tcol="FFFFFF" if cor==C_MAD else "000000"; wi.cell(r,2,"").font=Font(color=tcol)
    wi.merge_cells(start_row=r,start_column=3,end_row=r,end_column=5)
    wi.cell(r,3,nome).alignment=ESQ; wi.cell(r,3).border=BORDA; r+=1
# regras
r+=1; wi.cell(r,2,"REGRAS DO SISTEMA DE LETRAS").font=B_; wi.cell(r,2).fill=P(C_BAND); r+=1
regras=[
 "Manha e Tarde: pessoas fixas no turno, regime 6x3 (6 dias trabalha, 3 folga). 3 letras A/B/C defasadas 3 dias.",
 "Madrugada (letra D): ciclo de 10 dias 2 manha + 2 tarde + 2 madrugada + 4 folga. O dia que sai 07h conta como trabalhado.",
 "Cada pessoa tem POSTO FIXO; quando ela folga/ferias, o sistema cobre priorizando quem mais conhece o posto.",
 "Faltas sao cobertas por Hora Extra (limite 52h/mes) - marcado com *HE no calendario.",
]
for t in regras:
    wi.merge_cells(start_row=r,start_column=2,end_row=r,end_column=8)
    wi.cell(r,2,t).alignment=ESQ; wi.cell(r,2).font=Font(italic=True,size=9); wi.row_dimensions[r].height=24; r+=1

# ---------------- ABA Dimensionamento
wd_=wb.create_sheet("Dimensionamento"); wd_.sheet_view.showGridLines=False
for c,w in zip("ABCDEFG",[3,40,12,12,14,12,16]): wd_.column_dimensions[c].width=w
wd_.merge_cells("B2:G2"); wd_["B2"]="DIMENSIONAMENTO"; wd_["B2"].fill=P(C_TIT); wd_["B2"].font=TIT; wd_["B2"].alignment=CEN
heads=["Grupo / Turno","Postos","Dias/ano","Pessoa-dias","Disp./ano","Funcionarios"]
for i,h in enumerate(heads): wd_.cell(4,2+i,h)
sr(wd_,"B4:G4",P(C_HDR),WB_)
linhas=[("Manha 07:00-15:30 (21 postos)",21,365,223,N_MANHA),
        ("Tarde 15:00-23:30 (21 postos)",21,365,223,N_TARDE),
        ("Madrugada letra D (5 regionais 24h)",15,365,201,N_MAD),
        ("Apoio seg-sex (2 postos)",2,261,223,N_APOIO)]
r=5
for nm,po,di,dp,real in linhas:
    wd_.cell(r,2,nm).alignment=ESQ; wd_.cell(r,3,po); wd_.cell(r,4,di)
    wd_.cell(r,5,f"=C{r}*D{r}"); wd_.cell(r,6,dp); wd_.cell(r,7,real)
    sr(wd_,f"B{r}:G{r}",P(C_BAND) if r%2 else None); wd_.cell(r,7).font=B_; r+=1
wd_.cell(r,2,"TOTAL DE FUNCIONARIOS").font=B_; wd_.cell(r,7,f"=SUM(G5:G{r-1})").font=Font(bold=True,size=12)
sr(wd_,f"B{r}:G{r}",P(C_AMAR),B_); r+=2
wd_.merge_cells(f"B{r}:G{r}")
wd_.cell(r,2,("Obs.: Madrugada (letra D) cobre os 5 postos regionais nos 3 turnos (manha+tarde+madrugada), "
 "por isso conta 15 'postos-turno'/dia. Disponibilidade menor (201) pelo ciclo 2-2-2-4. "
 "Faltas pontuais sao cobertas por hora extra.")).alignment=ESQ
wd_.cell(r,2).font=Font(italic=True,size=9); wd_.row_dimensions[r].height=42

# ---------------- ABA Funcionarios
wf=wb.create_sheet("Funcionarios"); wf.sheet_view.showGridLines=False
for c,w in zip("ABCDE",[6,24,14,8,16]): wf.column_dimensions[c].width=w
wf.merge_cells("A1:E1"); wf["A1"]="FUNCIONARIOS"; wf["A1"].fill=P(C_TIT); wf["A1"].font=TIT; wf["A1"].alignment=CEN
for i,h in enumerate(["ID","Nome","Grupo","Letra","Posto fixo"]): wf.cell(2,1+i,h)
sr(wf,"A2:E2",P(C_HDR),WB_)
cor_grp={"Manha":C_MANHA,"Tarde":C_TARDE,"Madrugada":C_MAD,"Apoio":C_AMAR}
for i,e in enumerate(emp):
    r=3+i
    wf.cell(r,1,e["id"]); wf.cell(r,2,e["nome"]).alignment=ESQ
    wf.cell(r,3,e["grupo"]); wf.cell(r,4,e["letra"]); wf.cell(r,5,e["home"])
    fill=cor_grp[e["grupo"]]; sr(wf,f"A{r}:E{r}",P(fill))
    if e["grupo"]=="Madrugada":
        for cc in range(1,6): wf.cell(r,cc).font=Font(color="FFFFFF")
    wf.cell(r,2).alignment=ESQ
wf.freeze_panes="A3"
wf.auto_filter.ref=f"A2:E{2+TOTAL}"

# ---------------- ABA Postos
wp=wb.create_sheet("Postos"); wp.sheet_view.showGridLines=False
for c,w in zip("ABC",[8,18,28]): wp.column_dimensions[c].width=w
wp.merge_cells("A1:C1"); wp["A1"]="POSTOS"; wp["A1"].fill=P(C_TIT); wp["A1"].font=TIT; wp["A1"].alignment=CEN
for i,h in enumerate(["Tipo","Posto","Observacao"]): wp.cell(2,1+i,h)
sr(wp,"A2:C2",P(C_HDR),WB_)
r=3
for p in DIURNOS:
    wp.cell(r,1,"Diurno"); wp.cell(r,2,p); wp.cell(r,3,"Manha + Tarde (6x3 A/B/C)")
    sr(wp,f"A{r}:C{r}",P(C_MANHA)); wp.cell(r,3).alignment=ESQ; r+=1
for p in REGIONAIS:
    wp.cell(r,1,"Regional 24h"); wp.cell(r,2,p); wp.cell(r,3,"Manha+Tarde+Madrugada (letra D)")
    sr(wp,f"A{r}:C{r}",P(C_TARDE)); wp.cell(r,3).alignment=ESQ; r+=1
for p in APOIO:
    wp.cell(r,1,"Apoio"); wp.cell(r,2,p); wp.cell(r,3,"Seg a sex, manha")
    sr(wp,f"A{r}:C{r}",P(C_AMAR)); wp.cell(r,3).alignment=ESQ; r+=1

# ---------------- ABA Calendario (grade mestra)
wc=wb.create_sheet("Calendario"); wc.sheet_view.showGridLines=False
wc.cell(1,1,"ID"); wc.cell(1,2,"Funcionario")
wc.column_dimensions["A"].width=4; wc.column_dimensions["B"].width=22
for d in range(DIAS):
    c=wc.cell(1,3+d,DATAS[d]); c.number_format="dd/mm"; c.font=Font(bold=True,size=8); c.alignment=CEN
    wc.column_dimensions[get_column_letter(3+d)].width=7
sr(wc,"A1:B1",P(C_HDR),WB_)
for i,e in enumerate(emp):
    r=2+i; wc.cell(r,1,e["id"]); wc.cell(r,2,e["nome"]).alignment=ESQ
    for d in range(DIAS):
        c=wc.cell(r,3+d,status[i][d]); c.font=Font(size=8); c.alignment=CEN
wc.freeze_panes="C2"
LASTCOL=get_column_letter(2+DIAS)
rng=f"C2:{LASTCOL}{1+TOTAL}"
addcf=wc.conditional_formatting.add
addcf(rng,FormulaRule(formula=['LEFT(C2,2)="M "'],fill=P(C_MANHA)))
addcf(rng,FormulaRule(formula=['LEFT(C2,2)="T "'],fill=P(C_TARDE)))
addcf(rng,FormulaRule(formula=['LEFT(C2,2)="N "'],fill=P(C_MAD),font=Font(color="FFFFFF",size=8)))
addcf(rng,FormulaRule(formula=['C2="FOLGA"'],fill=P(C_FOLGA)))
addcf(rng,FormulaRule(formula=['C2="FERIAS"'],fill=P(C_FERIAS)))
addcf(rng,FormulaRule(formula=['C2="RESERVA"'],fill=P(C_RES)))
addcf(rng,FormulaRule(formula=['ISNUMBER(SEARCH("*HE",C2))'],fill=P(C_HE)))

# ---------------- ABA Visao do Dia
vd=wb.create_sheet("Visao do Dia"); vd.sheet_view.showGridLines=False
for c,w in zip("ABCDE",[4,16,26,14,12]): vd.column_dimensions[c].width=w
vd.merge_cells("A1:E1"); vd["A1"]="VISAO DO DIA"; vd["A1"].fill=P(C_TIT); vd["A1"].font=TIT; vd["A1"].alignment=CEN
vd["B3"]="Escolha a data:"; vd["B3"].font=B_
vd["C3"]=D0; vd["C3"].number_format="dd/mm/yyyy"; vd["C3"].fill=P(C_AMAR); vd["C3"].font=Font(bold=True,size=12)
dvd=DataValidation(type="date"); vd.add_data_validation(dvd); dvd.add(vd["C3"])
vd["B4"]="(col. interna)"; vd["C4"]="=MATCH(C3,Calendario!$1:$1,0)-1"
vd["B4"].font=Font(italic=True,size=8); vd["C4"].font=Font(italic=True,size=8)
RANGE=f"Calendario!$B$2:${LASTCOL}${1+TOTAL}"
def add_secao(r0,titulo,seats,prefixos):
    vd.merge_cells(f"A{r0}:E{r0}"); vd.cell(r0,1,titulo).fill=P(C_HDR); vd.cell(r0,1).font=SUB; vd.cell(r0,1).alignment=CEN
    vd.cell(r0+1,1,"#"); vd.cell(r0+1,2,"Posto"); vd.cell(r0+1,3,"Funcionario"); vd.cell(r0+1,4,"Situacao")
    sr(vd,f"A{r0+1}:E{r0+1}",P(C_BAND),B_)
    r=r0+2; n=1
    for s in seats:
        vd.cell(r,1,n); vd.cell(r,2,s)
        # procura na coluna do dia algum texto que termine no posto s (qualquer prefixo do turno)
        # monta o alvo "prefixo s"
        alvo=f'"{prefixos} "&$B{r}'
        f=(f'=IFERROR(INDEX({RANGE},MATCH({alvo},INDEX({RANGE},0,$C$4),0),1),'
           f'IFERROR(INDEX({RANGE},MATCH({alvo}&" *HE",INDEX({RANGE},0,$C$4),0),1),"-- vago --"))')
        vd.cell(r,3,f).alignment=ESQ
        vd.cell(r,4,"=IF(ISNUMBER(SEARCH(\"vago\",C"+str(r)+")),\"DESCOBERTO\",\"OK\")")
        sr(vd,f"A{r}:E{r}",None); r+=1; n+=1
    return r+1
r=6
r=add_secao(r,"MANHA (07:00 - 15:30)",DIURNOS+REGIONAIS,"M")
r=add_secao(r,"TARDE (15:00 - 23:30)",DIURNOS+REGIONAIS,"T")
r=add_secao(r,"MADRUGADA (23:00 - 07:30)",REGIONAIS,"N")
vd.freeze_panes="A6"

# ---------------- ABA Visao por Pessoa
vp=wb.create_sheet("Visao por Pessoa"); vp.sheet_view.showGridLines=False
for c,w in zip("ABCD",[14,16,18,14]): vp.column_dimensions[c].width=w
vp.merge_cells("A1:D1"); vp["A1"]="VISAO POR PESSOA"; vp["A1"].fill=P(C_TIT); vp["A1"].font=TIT; vp["A1"].alignment=CEN
vp["A3"]="ID da pessoa:"; vp["A3"].font=B_
vp["B3"]=1; vp["B3"].fill=P(C_AMAR); vp["B3"].font=Font(bold=True,size=12)
dvp=DataValidation(type="whole",operator="between",formula1=1,formula2=TOTAL); vp.add_data_validation(dvp); dvp.add(vp["B3"])
vp["A4"]="Nome:"; vp["A4"].font=B_; vp["B4"]="=IFERROR(INDEX(Funcionarios!B:B,MATCH(B3,Funcionarios!A:A,0)),\"\")"; vp["B4"].font=B_
vp["A5"]="Grupo / Letra:"; vp["B5"]="=IFERROR(INDEX(Funcionarios!C:C,MATCH(B3,Funcionarios!A:A,0))&\" / \"&INDEX(Funcionarios!D:D,MATCH(B3,Funcionarios!A:A,0)),\"\")"
vp["A6"]="Posto fixo:"; vp["B6"]="=IFERROR(INDEX(Funcionarios!E:E,MATCH(B3,Funcionarios!A:A,0)),\"\")"
vp["A7"]="Linha calend.:"; vp["B7"]="=MATCH(B3,Calendario!A:A,0)"; vp["A7"].font=Font(italic=True,size=8); vp["B7"].font=Font(italic=True,size=8)
# totais
vp["D3"]="Dias trabalhados (120d):"; vp["D3"].alignment=ESQ
vp["A9"]="Data"; vp["B9"]="Dia"; vp["C9"]="Posto / Situacao"
sr(vp,"A9:C9",P(C_HDR),WB_)
for k in range(120):
    r=10+k; col=get_column_letter(3+k)
    vp.cell(r,1,f"=Calendario!{col}$1"); vp.cell(r,1).number_format="dd/mm/yyyy"
    vp.cell(r,2,f'=TEXT(A{r},"ddd")')
    vp.cell(r,3,f"=INDEX(Calendario!{col}:{col},$B$7)").alignment=ESQ
    sr(vp,f"A{r}:C{r}",P(C_BAND) if k%2 else None)
vp.conditional_formatting.add("C10:C129",FormulaRule(formula=['LEFT(C10,2)="M "'],fill=P(C_MANHA)))
vp.conditional_formatting.add("C10:C129",FormulaRule(formula=['LEFT(C10,2)="T "'],fill=P(C_TARDE)))
vp.conditional_formatting.add("C10:C129",FormulaRule(formula=['LEFT(C10,2)="N "'],fill=P(C_MAD),font=Font(color="FFFFFF")))
vp.conditional_formatting.add("C10:C129",CellIsRule(operator="equal",formula=['"FOLGA"'],fill=P(C_FOLGA)))
vp.conditional_formatting.add("C10:C129",CellIsRule(operator="equal",formula=['"FERIAS"'],fill=P(C_FERIAS)))
vp.freeze_panes="A10"

# ---------------- ABA Banco Conhecimento
bc=wb.create_sheet("Banco Conhecimento"); bc.sheet_view.showGridLines=False
for c,w in zip("ABCDEFGHI",[6,22,14,12,14,12,12,14,14]): bc.column_dimensions[c].width=w
bc.merge_cells("A1:I1"); bc["A1"]="BANCO DE CONHECIMENTO (pesos)"; bc["A1"].fill=P(C_TIT); bc["A1"].font=TIT; bc["A1"].alignment=CEN
bc.merge_cells("A2:I2"); bc["A2"]="+1 ponto por dia despachado. Apos 180 dias sem despachar, perde 1/dia ate zerar."
bc["A2"].alignment=ESQ; bc["A2"].font=Font(italic=True,size=9)
bc["A3"]="HOJE:"; bc["B3"]="=TODAY()"; bc["B3"].number_format="dd/mm/yyyy"; bc["A3"].font=B_
for i,h in enumerate(["ID","Funcionario","Posto","Pontos brutos","Ultimo despacho","Dias parado","Decaimento","Pontos efetivos","Nivel"]):
    bc.cell(5,1+i,h)
sr(bc,"A5:I5",P(C_HDR),WB_)
pares=sorted([k for k in pts if pts[k]>0],key=lambda k:(k[0],-pts[k]))
nome_by={e["id"]:e["nome"] for e in emp}
r=6
for (eid,p) in pares:
    ult=D0+timedelta(days=last[(eid,p)]) if last[(eid,p)]>=0 else D0
    bc.cell(r,1,eid); bc.cell(r,2,nome_by[eid]).alignment=ESQ; bc.cell(r,3,p); bc.cell(r,4,pts[(eid,p)])
    c=bc.cell(r,5,ult); c.number_format="dd/mm/yyyy"
    bc.cell(r,6,f"=$B$3-E{r}"); bc.cell(r,7,f"=MAX(0,F{r}-180)"); bc.cell(r,8,f"=MAX(0,D{r}-G{r})")
    bc.cell(r,9,f'=IF(H{r}>=180,"Especialista",IF(H{r}>=60,"Apto",IF(H{r}>0,"Basico","Sem pratica")))')
    sr(bc,f"A{r}:I{r}",P(C_BAND) if r%2 else None); bc.cell(r,2).alignment=ESQ; r+=1
bc.freeze_panes="A6"; BC_LAST=r-1; bc.auto_filter.ref=f"A5:I{BC_LAST}"

# ---------------- ABA Substituicao
sb=wb.create_sheet("Substituicao"); sb.sheet_view.showGridLines=False
for c,w in zip("ABCDEFG",[6,22,12,14,16,12,14]): sb.column_dimensions[c].width=w
sb.merge_cells("A1:G1"); sb["A1"]="SUBSTITUICAO - melhor candidato"; sb["A1"].fill=P(C_TIT); sb["A1"].font=TIT; sb["A1"].alignment=CEN
sb["A3"]="Data:"; sb["B3"]=D0+timedelta(days=1); sb["B3"].number_format="dd/mm/yyyy"; sb["B3"].fill=P(C_AMAR); sb["B3"].font=B_; sb["A3"].font=B_
sb["A4"]="Posto:"; sb["B4"]=DIURNOS[0]; sb["B4"].fill=P(C_AMAR); sb["B4"].font=B_; sb["A4"].font=B_
dvs=DataValidation(type="list",formula1='"'+",".join(DIURNOS+REGIONAIS)+'"'); sb.add_data_validation(dvs); dvs.add(sb["B4"])
sb["A5"]="Turno (M/T/N):"; sb["B5"]="M"; sb["B5"].fill=P(C_AMAR); sb["B5"].font=B_; sb["A5"].font=B_
dvt=DataValidation(type="list",formula1='"M,T,N"'); sb.add_data_validation(dvt); dvt.add(sb["B5"])
sb["A6"]="Quem faltou (ID):"; sb["B6"]=1; sb["B6"].fill=P(C_AMAR); sb["B6"].font=B_; sb["A6"].font=B_
sb["D3"]="Col. dia:"; sb["E3"]="=MATCH(B3,Calendario!$1:$1,0)"
sb["D4"]="Col. ontem:"; sb["E4"]="=E3-1"
for cc in ("D3","D4","E3","E4"): sb[cc].font=Font(italic=True,size=8)
sb.merge_cells("A8:G8"); sb["A8"]=("Pontuacao = conhecimento no posto + 1000 se a pessoa ja estava NESTE posto ontem. "
 "So entram pessoas disponiveis (FOLGA ou RESERVA). Ordene por PONTUACAO (maior->menor): o melhor fica no topo.")
sb["A8"].alignment=ESQ; sb["A8"].font=Font(italic=True,size=9)
for i,h in enumerate(["ID","Funcionario","Situacao no dia","Estava no posto ontem?","Conhecimento","Bonus ontem","PONTUACAO"]):
    sb.cell(10,1+i,h)
sr(sb,"A10:G10",P(C_HDR),WB_)
for i,e in enumerate(emp):
    r=11+i; eid=e["id"]; rowcal=2+i
    sb.cell(r,1,eid); sb.cell(r,2,e["nome"]).alignment=ESQ
    sb.cell(r,3,f"=INDEX(Calendario!$A:${LASTCOL},{rowcal},$E$3)").alignment=ESQ
    sb.cell(r,4,f'=IF(INDEX(Calendario!$A:${LASTCOL},{rowcal},$E$4)=$B$5&" "&$B$4,1,0)')
    sb.cell(r,5,(f"=IFERROR(SUMIFS('Banco Conhecimento'!$H$6:$H${BC_LAST},"
                 f"'Banco Conhecimento'!$A$6:$A${BC_LAST},$A{r},"
                 f"'Banco Conhecimento'!$C$6:$C${BC_LAST},$B$4),0)"))
    sb.cell(r,6,f"=D{r}*1000")
    sb.cell(r,7,f'=IF(AND($A{r}<>$B$6,OR(C{r}="FOLGA",C{r}="RESERVA")),E{r}+F{r},-1)')
    sr(sb,f"A{r}:G{r}",P(C_BAND) if i%2 else None); sb.cell(r,2).alignment=ESQ
sb.freeze_panes="A11"; sb.auto_filter.ref=f"A10:G{10+TOTAL}"

# ---------------- ABA Horas Extras
he=wb.create_sheet("Horas Extras"); he.sheet_view.showGridLines=False
for c,w in zip("ABCDEFG",[6,22,12,16,10,10,14]): he.column_dimensions[c].width=w
he.merge_cells("A1:G1"); he["A1"]="HORAS EXTRAS (limite 52h/mes)"; he["A1"].fill=P(C_TIT); he["A1"].font=TIT; he["A1"].alignment=CEN
for i,h in enumerate(["ID","Funcionario","Mes/Ano","Horas realizadas","Limite","Saldo","Status"]): he.cell(3,1+i,h)
sr(he,"A3:G3",P(C_HDR),WB_)
agg=defaultdict(float)
for d,p,eid in he_events:
    agg[(eid,(D0+timedelta(days=d)).strftime("%m/%Y"))]+=8.5
rows=sorted(agg.items(),key=lambda x:-x[1])[:80]
r=4
for (eid,mes),h in rows:
    he.cell(r,1,eid); he.cell(r,2,nome_by[eid]).alignment=ESQ; he.cell(r,3,mes)
    he.cell(r,4,round(h,1)); he.cell(r,5,52); he.cell(r,6,f"=E{r}-D{r}")
    he.cell(r,7,f'=IF(D{r}>E{r},"EXCEDIDO",IF(D{r}>=E{r}*0.9,"ATENCAO","OK"))')
    sr(he,f"A{r}:G{r}",P(C_BAND) if r%2 else None); he.cell(r,2).alignment=ESQ; r+=1
he.conditional_formatting.add(f"G4:G{r-1}",CellIsRule(operator="equal",formula=['"EXCEDIDO"'],fill=P(C_VERM)))
he.conditional_formatting.add(f"G4:G{r-1}",CellIsRule(operator="equal",formula=['"ATENCAO"'],fill=P(C_AMAR)))
he.freeze_panes="A4"

wb.save("Escala_Centro_Operacoes.xlsx")
print(f"OK | Efetivo={TOTAL} (M{N_MANHA}/T{N_TARDE}/D{N_MAD}/Ap{N_APOIO}) | "
      f"HE={len(he_events)} | Descobertos={descobertos} | pares={len(pares)}")
