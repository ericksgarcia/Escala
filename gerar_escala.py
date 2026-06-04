# -*- coding: utf-8 -*-
"""
Motor de escala 24h - Centro de Operacoes.
Gera projecao de 2 anos (730 dias) dia-a-dia, nomes ficticios,
multiplas visoes e funcao de substituicao ranqueada (sem macros).
Saida: Escala_Centro_Operacoes.xlsx
"""
import openpyxl, random
from datetime import date, timedelta
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule, CellIsRule

random.seed(42)

# ---------------------------------------------------------------- estilos
VTIT = PatternFill("solid", fgColor="375623")
VMED = PatternFill("solid", fgColor="70AD47")
VCLR = PatternFill("solid", fgColor="C6E0B4")
VSUA = PatternFill("solid", fgColor="E2EFDA")
AZUL = PatternFill("solid", fgColor="DDEBF7")
CINZA= PatternFill("solid", fgColor="D9D9D9")
AMAR = PatternFill("solid", fgColor="FFF2CC")
VERM = PatternFill("solid", fgColor="F4CCCC")
LARJ = PatternFill("solid", fgColor="FCE4D6")
WB_  = Font(bold=True, color="FFFFFF")
B_   = Font(bold=True)
T_   = Font(bold=True, size=14, color="FFFFFF")
THIN = Side(style="thin", color="BFBFBF")
BORDA= Border(left=THIN,right=THIN,top=THIN,bottom=THIN)
CEN  = Alignment(horizontal="center", vertical="center", wrap_text=True)
ESQ  = Alignment(horizontal="left", vertical="center", wrap_text=True)

def sr(ws, rng, fill=None, font=None, border=BORDA, align=CEN):
    for row in ws[rng]:
        for c in row:
            if fill: c.fill=fill
            if font: c.font=font
            if border: c.border=border
            if align: c.alignment=align

# ---------------------------------------------------------------- nomes ficticios
PRI = ["Alexandre","Bruna","Caio","Daniela","Eduardo","Fernanda","Gustavo","Helena",
"Igor","Juliana","Kleber","Larissa","Marcos","Natalia","Otavio","Patricia","Rafael",
"Sabrina","Thiago","Vanessa","Wagner","Yasmin","Bernardo","Camila","Diego","Elaine",
"Fabio","Gabriela","Henrique","Isabela","Joao","Karina","Lucas","Mariana","Nelson",
"Olivia","Paulo","Renata","Sergio","Tatiana","Ulisses","Viviane","Wesley","Adriana",
"Breno","Cintia","Davi","Erika","Felipe","Giovana","Hugo","Ines","Jonas","Keila",
"Leandro","Monica","Nicolas","Priscila","Ramon","Silvia","Tarcisio","Ursula","Vitor",
"Wanda","Anderson","Beatriz","Cesar","Debora","Emerson","Flavia","Gilberto","Heloisa",
"Ivan","Jaqueline","Kaua","Luana","Mateus","Nadia","Osmar","Poliana","Rodrigo","Simone",
"Tomas"," Udo","Valeria","Wilson","Amanda","Bruno","Carla","Denis","Edna","Fabricio",
"Gisele","Hamilton","Iara","Jefferson","Lia","Murilo","Noemia"]
SOB = ["Silva","Souza","Oliveira","Pereira","Costa","Almeida","Nunes","Carvalho","Rocha",
"Gomes","Martins","Araujo","Ribeiro","Barbosa","Teixeira","Cardoso","Moraes","Lima",
"Freitas","Pinto","Moreira","Cavalcanti","Dias","Castro","Campos","Macedo","Andrade",
"Vieira","Mendes","Tavares","Correia","Ramos","Azevedo","Batista","Fonseca","Cunha",
"Brandao","Siqueira","Pacheco","Reis"]
def nomes(n):
    out=set(); res=[]
    i=0
    while len(res)<n:
        nm=f"{PRI[i%len(PRI)]} {SOB[(i*3)%len(SOB)]}"
        if nm not in out: out.add(nm); res.append(nm)
        i+=1
    return res
NOMES = nomes(98)

# ---------------------------------------------------------------- postos
P_DIURNO = ["BH/NL","SG/AR","BT","SL","GV","RA/PO","TO/PR","IP/AG","DV/IJ","FM/CL",
"IA/CR","MO/SI","PT/AL","JN/BC","JB/PI","JF/OP","PN/LV","LF/BD","UL/IR","PM/PS","TB/AF",
"UR/JM","PA/SJ","TC/FR","VR/AX","CN/MG"]                              # 26
MALHA = {p:m for p,m in zip(P_DIURNO,
 ["CENTRO"]*4+["LESTE"]*4+["OESTE"]*3+["NORTE"]*4+["MANTIQUEIRA"]*3+["TRIANGULO"]*4+["SUL"]*3+["CENTRO"])}
P_NOITE  = ["N1","N2","N3","N4","N5"]
P_APOIO  = ["AP-1","AP-2"]

SHIFTS = {  # shift: (lista_postos, qtd_titular, qtd_volante, label_turno)
 "D": (P_DIURNO, 26, 17, "07:00-15:30"),
 "T": (P_DIURNO, 26, 17, "15:00-23:30"),
 "N": (P_NOITE,   5,  4, "23:00-07:30"),
 "A": (P_APOIO,   2,  1, "Apoio seg-sex"),
}

# ---------------------------------------------------------------- funcionarios
emp=[]   # dict por funcionario
idx=0
for sh,(postos,nt,nv,lab) in SHIFTS.items():
    for k in range(nt+nv):
        titular = k < nt
        emp.append({
            "id": idx+1, "nome": NOMES[idx], "shift": sh, "turno": lab,
            "tipo": "Titular" if titular else "Volante",
            "posto": postos[k] if titular else "",
            "offset": k % 9,
        })
        idx+=1
N = len(emp)  # 98

# ferias: 2 janelas de 30 dias em 730 dias, escalonadas
for e in emp:
    base = 25 + (e["id"]*9) % 300
    e["ferias"] = set()
    for w in (base, base+365):
        for d in range(w, w+30):
            if 0<=d<730: e["ferias"].add(d)

# conhecimento inicial: titular ja domina seu posto
pts={}; last={}    # pts[(eid,posto)], last[(eid,posto)] = dia
for e in emp:
    if e["tipo"]=="Titular":
        pts[(e["id"],e["posto"])] = random.randint(150,400)
        last[(e["id"],e["posto"])] = -2

def eff(eid,posto,day):
    if (eid,posto) not in pts: return 0
    parado = day - last[(eid,posto)]
    return max(0, pts[(eid,posto)] - max(0, parado-180))

# ---------------------------------------------------------------- motor diario
D0 = date(2026,6,4)
status = [["" for _ in range(730)] for _ in range(N)]  # status[eid-1][dia]
he_events=[]      # (dia, posto, eid)
descobertos=0

by_shift={sh:[e for e in emp if e["shift"]==sh] for sh in SHIFTS}

for day in range(730):
    dt = D0 + timedelta(days=day)
    weekday = dt.weekday()  # 0=seg ... 6=dom
    for sh,(postos,nt,nv,lab) in SHIFTS.items():
        team = by_shift[sh]
        postos_dia = postos if sh!="A" else (postos if weekday<5 else [])
        # disponibilidade
        avail=[]; folga=[]
        for e in team:
            eid=e["id"]
            if day in e["ferias"]:
                status[eid-1][day]="FERIAS"; continue
            working = ((day - e["offset"]) % 9) < 6
            if sh=="A" and weekday>=5:
                status[eid-1][day]="FOLGA"; continue
            if working: avail.append(e)
            else: folga.append(e); status[eid-1][day]="FOLGA"
        assigned={}            # posto -> eid
        used=set()
        # 1) titular no proprio posto (continuidade)
        for e in avail:
            if e["tipo"]=="Titular" and e["posto"] in postos_dia and e["posto"] not in assigned:
                assigned[e["posto"]]=e["id"]; used.add(e["id"])
        # 2) postos descobertos -> melhor candidato por conhecimento + ontem
        livres=[p for p in postos_dia if p not in assigned]
        pool=[e for e in avail if e["id"] not in used]
        for p in livres:
            if not pool: break
            def score(e):
                ontem = 1 if day>0 and status[e["id"]-1][day-1]==p else 0
                return (eff(e["id"],p,day), ontem, -e["id"])
            best=max(pool, key=score)
            assigned[p]=best["id"]; used.add(best["id"]); pool.remove(best)
        # 3) ainda descoberto -> hora extra (chama alguem de folga)
        for p in postos_dia:
            if p not in assigned:
                cand=[e for e in folga if e["id"] not in used]
                if cand:
                    best=max(cand, key=lambda e:(eff(e["id"],p,day), -e["id"]))
                    assigned[p]="HE_"+str(best["id"])
                    he_events.append((day,p,best["id"]))
                    used.add(best["id"])
                else:
                    assigned[p]="DESCOBERTO"; descobertos+=1
        # registra status e pontua conhecimento
        for p,who in assigned.items():
            if isinstance(who,str) and who.startswith("HE_"):
                eid=int(who[3:])
                status[eid-1][day]=f"{p} (HE)"
            elif who=="DESCOBERTO":
                continue
            else:
                eid=who
                # se nao era seu posto titular marca como cobertura
                e=emp[eid-1]
                status[eid-1][day]=p
            pts[(eid,p)]=pts.get((eid,p),0)+1
            last[(eid,p)]=day
        # quem sobrou disponivel = reserva
        for e in pool:
            if not status[e["id"]-1][day]:
                status[e["id"]-1][day]="RESERVA"

# ================================================================ WORKBOOK
wb=openpyxl.Workbook()

# ---------- ABA Instrucoes
ws=wb.active; ws.title="Instrucoes"; ws.sheet_view.showGridLines=False
ws.column_dimensions["B"].width=110
ws.merge_cells("B2:B2"); ws["B2"]="CONTROLE DE ESCALA - CENTRO DE OPERACOES 24h"
ws["B2"].fill=VTIT; ws["B2"].font=T_; ws["B2"].alignment=ESQ; ws.row_dimensions[2].height=26
linhas=[
 "",
 "ABAS DESTE ARQUIVO:",
 "1. Dimensionamento  -> calculo de quantos funcionarios sao necessarios.",
 "2. Funcionarios     -> cadastro (98) com nomes ficticios, turno e posto titular.",
 "3. Postos           -> os 26 postos diurnos/tarde + 5 noturnos + 2 apoio.",
 "4. Calendario 2 anos -> grade mestra: cada funcionario x cada dia (730 dias). FONTE de todas as visoes.",
 "5. Visao Diaria     -> escolha uma DATA e veja quem esta em cada posto naquele dia.",
 "6. Visao Funcionario-> escolha um FUNCIONARIO e veja a escala dele dia-a-dia.",
 "7. Substituicao     -> informe DATA + POSTO + quem faltou; o sistema ranqueia os melhores substitutos.",
 "8. Banco Conhecimento-> pontos de cada pessoa em cada posto (com decaimento apos 6 meses).",
 "9. Horas Extras     -> controle mensal com limite de 52h/mes.",
 "",
 "REGRAS APLICADAS:",
 "- Regime 6x3 (6 dias trabalha, 3 folga) em todos os postos.",
 "- A mesma pessoa (titular) e mantida no proprio posto sempre que esta disponivel.",
 "- Volantes cobrem folgas, ferias e faltas, priorizando MAIOR conhecimento e quem ja estava no posto no dia anterior.",
 "- Substituicao: o ranking usa (1) quem ficou com o posto no ultimo dia e (2) os pontos de conhecimento.",
 "- Legenda do calendario: codigo do posto = trabalhando; FOLGA; FERIAS; RESERVA; '(HE)' = hora extra.",
]
r=3
for t in linhas:
    ws.cell(r,2,t); ws.cell(r,2).alignment=ESQ
    if t.endswith(":"): ws.cell(r,2).font=B_
    r+=1

# ---------- ABA Dimensionamento
wd=wb.create_sheet("Dimensionamento"); wd.sheet_view.showGridLines=False
for c,w in zip("ABCDEFG",[3,46,12,12,14,12,30]): wd.column_dimensions[c].width=w
wd.merge_cells("B2:G2"); wd["B2"]="DIMENSIONAMENTO DA EQUIPE"; wd["B2"].fill=VTIT; wd["B2"].font=T_; wd["B2"].alignment=CEN
wd["B4"]="Turno"; wd["C4"]="Postos"; wd["D4"]="Dias/ano"; wd["E4"]="Pessoa-dias"; wd["F4"]="Disp./ano"; wd["G4"]="Funcionarios"
sr(wd,"B4:G4",VMED,WB_)
linhas=[("Diurno 07:00-15:30",26,365,223),("Tarde 15:00-23:30",26,365,223),
        ("Noturno 23:00-07:30 (5 agrupados)",5,365,223),("Apoio seg-sex (diurno)",2,261,223)]
r=5
for nm,po,di,dp in linhas:
    wd.cell(r,2,nm).alignment=ESQ; wd.cell(r,3,po); wd.cell(r,4,di)
    wd.cell(r,5,f"=C{r}*D{r}"); wd.cell(r,6,dp); wd.cell(r,7,f"=ROUNDUP(E{r}/F{r},0)")
    sr(wd,f"C{r}:G{r}"); wd.cell(r,2).border=BORDA; wd.cell(r,7).font=B_; r+=1
wd.cell(r,2,"TOTAL DE FUNCIONARIOS").font=B_; wd.cell(r,7,f"=SUM(G5:G{r-1})").font=Font(bold=True,size=12)
sr(wd,f"B{r}:G{r}",AMAR,B_); tot=r; r+=2
wd.cell(r,2,"Titulares (posto FIXO)").alignment=ESQ; wd.cell(r,3,"=26+26+5+2"); wd.cell(r,3).font=B_
sr(wd,f"B{r}:C{r}",VSUA); fx=r; r+=1
wd.cell(r,2,"Volantes (posto VARIAVEL)").alignment=ESQ; wd.cell(r,3,f"=G{tot}-C{fx}"); wd.cell(r,3).font=B_
sr(wd,f"B{r}:C{r}",AZUL); r+=2
wd.merge_cells(f"B{r}:G{r}")
wd.cell(r,2,"Faltas imprevistas sao cobertas por hora extra (limite 52h/mes). Ver aba Horas Extras.").alignment=ESQ
wd.cell(r,2).font=Font(italic=True,size=9)

# ---------- ABA Funcionarios
wf=wb.create_sheet("Funcionarios"); wf.sheet_view.showGridLines=False
for c,w in zip("ABCDE",[6,26,12,16,16]): wf.column_dimensions[c].width=w
wf.merge_cells("A1:E1"); wf["A1"]="CADASTRO DE FUNCIONARIOS"; wf["A1"].fill=VTIT; wf["A1"].font=T_; wf["A1"].alignment=CEN
for i,h in enumerate(["ID","Nome","Tipo","Turno","Posto titular"]): wf.cell(2,1+i,h)
sr(wf,"A2:E2",VMED,WB_)
for i,e in enumerate(emp):
    r=3+i
    wf.cell(r,1,e["id"]); wf.cell(r,2,e["nome"]).alignment=ESQ; wf.cell(r,3,e["tipo"])
    wf.cell(r,4,e["turno"]); wf.cell(r,5,e["posto"])
    sr(wf,f"A{r}:E{r}", VSUA if e["tipo"]=="Titular" else AZUL)
    wf.cell(r,2).alignment=ESQ
wf.freeze_panes="A3"

# ---------- ABA Postos
wp=wb.create_sheet("Postos"); wp.sheet_view.showGridLines=False
for c,w in zip("ABCD",[6,16,12,16]): wp.column_dimensions[c].width=w
wp.merge_cells("A1:D1"); wp["A1"]="POSTOS"; wp["A1"].fill=VTIT; wp["A1"].font=T_; wp["A1"].alignment=CEN
for i,h in enumerate(["ID","Malha","Posto","Turno"]): wp.cell(2,1+i,h)
sr(wp,"A2:D2",VMED,WB_)
r=3; pid=1
for sh,(postos,nt,nv,lab) in SHIFTS.items():
    for p in postos:
        wp.cell(r,1,pid); wp.cell(r,2,MALHA.get(p, {"N":"NOITE","A":"APOIO"}[sh] if sh in "NA" else ""))
        wp.cell(r,3,p); wp.cell(r,4,lab)
        fill={"D":VSUA,"T":AZUL,"N":CINZA,"A":AMAR}[sh]; sr(wp,f"A{r}:D{r}",fill); r+=1; pid+=1

# ---------- ABA Calendario 2 anos (grade mestra)
wc=wb.create_sheet("Calendario 2 anos"); wc.sheet_view.showGridLines=False
wc.cell(1,1,"ID"); wc.cell(1,2,"Funcionario")
wc.column_dimensions["A"].width=5; wc.column_dimensions["B"].width=24
DATAS=[D0+timedelta(days=d) for d in range(730)]
for d in range(730):
    c=wc.cell(1,3+d,DATAS[d]); c.number_format="dd/mm"; c.font=Font(bold=True,size=8); c.alignment=CEN
    wc.column_dimensions[get_column_letter(3+d)].width=7
sr(wc,"A1:B1",VMED,WB_)
for i,e in enumerate(emp):
    r=2+i
    wc.cell(r,1,e["id"]); wc.cell(r,2,e["nome"]).alignment=ESQ
    for d in range(730):
        c=wc.cell(r,3+d,status[i][d]); c.font=Font(size=8); c.alignment=CEN
wc.freeze_panes="C2"
# cores por status
rng=f"C2:{get_column_letter(2+730)}{1+N}"
wc.conditional_formatting.add(rng, FormulaRule(formula=['C2="FOLGA"'], fill=CINZA))
wc.conditional_formatting.add(rng, FormulaRule(formula=['C2="FERIAS"'], fill=AMAR))
wc.conditional_formatting.add(rng, FormulaRule(formula=['C2="RESERVA"'], fill=VSUA))
wc.conditional_formatting.add(rng, FormulaRule(formula=['ISNUMBER(SEARCH("(HE)",C2))'], fill=LARJ))
LAST_COL=get_column_letter(2+730)

# ---------- ABA Visao Diaria
vd=wb.create_sheet("Visao Diaria"); vd.sheet_view.showGridLines=False
for c,w in zip("ABCD",[4,16,28,14]): vd.column_dimensions[c].width=w
vd.merge_cells("A1:D1"); vd["A1"]="VISAO DIARIA - quem esta em cada posto"; vd["A1"].fill=VTIT; vd["A1"].font=T_; vd["A1"].alignment=CEN
vd["A3"]="DATA:"; vd["A3"].font=B_
vd["B3"]=D0; vd["B3"].number_format="dd/mm/yyyy"; vd["B3"].fill=AMAR; vd["B3"].font=B_
# coluna do dia no calendario:
vd["A4"]="(coluna)"; vd["B4"]="=MATCH(B3,'Calendario 2 anos'!$1:$1,0)-1"
vd["A4"].font=Font(italic=True,size=8); vd["B4"].font=Font(italic=True,size=8)
for i,h in enumerate(["#","Posto","Funcionario","Turno"]): vd.cell(6,1+i,h)
sr(vd,"A6:D6",VMED,WB_)
DATA_RANGE=f"'Calendario 2 anos'!$B$2:${LAST_COL}${1+N}"
r=7; n=1
for sh,(postos,nt,nv,lab) in SHIFTS.items():
    for p in postos:
        vd.cell(r,1,n); vd.cell(r,2,p); vd.cell(r,4,lab)
        # procura na coluna do dia (offset = B4) o posto p e devolve o nome (col 1 do range)
        f=(f'=IFERROR(INDEX({DATA_RANGE},'
           f'MATCH(B{r},INDEX({DATA_RANGE},0,$B$4),0),1),"-")')
        vd.cell(r,3,f).alignment=ESQ
        sr(vd,f"A{r}:D{r}", {"D":VSUA,"T":AZUL,"N":CINZA,"A":AMAR}[sh]); r+=1; n+=1
vd.freeze_panes="A7"

# ---------- ABA Visao Funcionario
vf=wb.create_sheet("Visao Funcionario"); vf.sheet_view.showGridLines=False
for c,w in zip("ABC",[14,16,18]): vf.column_dimensions[c].width=w
vf.merge_cells("A1:C1"); vf["A1"]="VISAO POR FUNCIONARIO"; vf["A1"].fill=VTIT; vf["A1"].font=T_; vf["A1"].alignment=CEN
vf["A3"]="ID FUNCIONARIO:"; vf["A3"].font=B_
vf["B3"]=1; vf["B3"].fill=AMAR; vf["B3"].font=B_
vf["A4"]="Nome:"; vf["A4"].font=B_
vf["B4"]="=IFERROR(INDEX(Funcionarios!$B:$B,MATCH(B3,Funcionarios!$A:$A,0)),\"\")"
vf["A5"]="Linha calend.:"; vf["B5"]="=MATCH(B3,'Calendario 2 anos'!$A:$A,0)"
vf["A5"].font=Font(italic=True,size=8); vf["B5"].font=Font(italic=True,size=8)
vf["A7"]="Data"; vf["B7"]="Dia"; vf["C7"]="Posto / Status"
sr(vf,"A7:C7",VMED,WB_)
DIAS_SEM=["seg","ter","qua","qui","sex","sab","dom"]
for k in range(120):  # proximos 120 dias a partir de B3 data inicial fixa D0
    r=8+k
    vf.cell(r,1,f"='Calendario 2 anos'!{get_column_letter(3+k)}$1"); vf.cell(r,1).number_format="dd/mm/yyyy"
    vf.cell(r,2,f'=TEXT({get_column_letter(1)}{r},"ddd")')
    vf.cell(r,3,f"=INDEX('Calendario 2 anos'!{get_column_letter(3+k)}:{get_column_letter(3+k)},$B$5)").alignment=ESQ
    sr(vf,f"A{r}:C{r}",None)
vf.freeze_panes="A8"

# ---------- ABA Banco Conhecimento
bc=wb.create_sheet("Banco Conhecimento"); bc.sheet_view.showGridLines=False
for c,w in zip("ABCDEFGHI",[6,24,10,12,14,12,12,14,14]): bc.column_dimensions[c].width=w
bc.merge_cells("A1:I1"); bc["A1"]="BANCO DE CONHECIMENTO (pesos por posto)"; bc["A1"].fill=VTIT; bc["A1"].font=T_; bc["A1"].alignment=CEN
bc.merge_cells("A2:I2"); bc["A2"]="+1 ponto por dia despachado. Apos 180 dias sem despachar, perde 1 ponto/dia ate zerar."
bc["A2"].alignment=ESQ; bc["A2"].font=Font(italic=True,size=9)
bc["A3"]="HOJE:"; bc["B3"]="=TODAY()"; bc["B3"].number_format="dd/mm/yyyy"; bc["A3"].font=B_
for i,h in enumerate(["ID","Funcionario","Posto","Pontos brutos","Ultimo despacho","Dias parado","Decaimento","Pontos efetivos","Nivel"]):
    bc.cell(5,1+i,h)
sr(bc,"A5:I5",VMED,WB_)
# exporta todos os pares com pontos>0
nome_by_id={e["id"]:e["nome"] for e in emp}
pares=sorted([k for k in pts if pts[k]>0], key=lambda k:(k[0], -pts[k]))
r=6
for (eid,p) in pares:
    ult = D0+timedelta(days=last[(eid,p)]) if last[(eid,p)]>=0 else D0
    bc.cell(r,1,eid); bc.cell(r,2,nome_by_id[eid]).alignment=ESQ; bc.cell(r,3,p)
    bc.cell(r,4,pts[(eid,p)]); c=bc.cell(r,5,ult); c.number_format="dd/mm/yyyy"
    bc.cell(r,6,f'=$B$3-E{r}')
    bc.cell(r,7,f'=MAX(0,F{r}-180)')
    bc.cell(r,8,f'=MAX(0,D{r}-G{r})')
    bc.cell(r,9,f'=IF(H{r}>=180,"Especialista",IF(H{r}>=60,"Apto",IF(H{r}>0,"Basico","Sem pratica")))')
    sr(bc,f"A{r}:I{r}",None); bc.cell(r,2).alignment=ESQ; r+=1
bc.freeze_panes="A6"
BC_LAST=r-1

# ---------- ABA Substituicao (ranking)
sb=wb.create_sheet("Substituicao"); sb.sheet_view.showGridLines=False
for c,w in zip("ABCDEFG",[6,24,12,14,16,12,14]): sb.column_dimensions[c].width=w
sb.merge_cells("A1:G1"); sb["A1"]="SUBSTITUICAO - melhores candidatos"; sb["A1"].fill=VTIT; sb["A1"].font=T_; sb["A1"].alignment=CEN
sb["A3"]="DATA:"; sb["B3"]=D0; sb["B3"].number_format="dd/mm/yyyy"; sb["B3"].fill=AMAR; sb["B3"].font=B_; sb["A3"].font=B_
sb["A4"]="POSTO:"; sb["B4"]="BH/NL"; sb["B4"].fill=AMAR; sb["B4"].font=B_; sb["A4"].font=B_
sb["A5"]="Quem faltou (ID):"; sb["B5"]=1; sb["B5"].fill=AMAR; sb["B5"].font=B_; sb["A5"].font=B_
sb["D3"]="Col. do dia:"; sb["E3"]="=MATCH(B3,'Calendario 2 anos'!$1:$1,0)"
sb["D4"]="Col. dia ant.:"; sb["E4"]="=E3-1"
for c in ("D3","D4"): sb[c].font=Font(italic=True,size=8)
for c in ("E3","E4"): sb[c].font=Font(italic=True,size=8)
sb.merge_cells("A7:G7"); sb["A7"]=("Ranking: pontuacao = Pontos de conhecimento no posto + bonus de 1000 se a pessoa "
 "ja estava NESTE posto no dia anterior. So entram pessoas DISPONIVEIS (FOLGA/RESERVA) e diferentes de quem faltou.")
sb["A7"].alignment=ESQ; sb["A7"].font=Font(italic=True,size=9)
hdr=["ID","Funcionario","Status no dia","Estava no posto ontem?","Conhecimento (efetivo)","Bonus ontem","PONTUACAO"]
for i,h in enumerate(hdr): sb.cell(9,1+i,h)
sr(sb,"A9:G9",VMED,WB_)
# uma linha por funcionario (todos), formulas
DATA_COL_REF=f"'Calendario 2 anos'!INDEX($A:${LAST_COL},0,$E$3)"  # nao usado direto
for i,e in enumerate(emp):
    r=10+i
    eid=e["id"]
    rowcal=2+i  # linha no calendario
    sb.cell(r,1,eid); sb.cell(r,2,e["nome"]).alignment=ESQ
    # status no dia = celula calendario(linha, col E3)
    sb.cell(r,3,f"=INDEX('Calendario 2 anos'!$A:${LAST_COL},{rowcal},$E$3)").alignment=ESQ
    # estava no posto ontem?
    sb.cell(r,4,f'=IF(INDEX(\'Calendario 2 anos\'!$A:${LAST_COL},{rowcal},$E$4)=$B$4,1,0)')
    # conhecimento efetivo: procura na aba Banco (ID + posto). usa SUMIFS sobre col H (efetivo) - mas H e formula; usamos D-decaimento via SUMPRODUCT
    sb.cell(r,5,(f'=IFERROR(SUMIFS(\'Banco Conhecimento\'!$H$6:$H${BC_LAST},'
                 f'\'Banco Conhecimento\'!$A$6:$A${BC_LAST},$A{r},'
                 f'\'Banco Conhecimento\'!$C$6:$C${BC_LAST},$B$4),0)'))
    sb.cell(r,6,f'=D{r}*1000')
    # pontuacao: so se disponivel (FOLGA ou RESERVA) e nao for quem faltou
    sb.cell(r,7,(f'=IF(AND($A{r}<>$B$5,OR(C{r}="FOLGA",C{r}="RESERVA")),E{r}+F{r},-1)'))
    sr(sb,f"A{r}:G{r}",None); sb.cell(r,2).alignment=ESQ
sb.cell(9+N+2,1,"DICA: ordene a tabela pela coluna PONTUACAO (maior->menor) para ver o melhor substituto no topo.")
sb.cell(9+N+2,1).font=Font(italic=True,size=9)
sb.freeze_panes="A10"

# ---------- ABA Horas Extras
he=wb.create_sheet("Horas Extras"); he.sheet_view.showGridLines=False
for c,w in zip("ABCDEFG",[6,24,12,16,10,10,14]): he.column_dimensions[c].width=w
he.merge_cells("A1:G1"); he["A1"]="HORAS EXTRAS (limite 52h/mes)"; he["A1"].fill=VTIT; he["A1"].font=T_; he["A1"].alignment=CEN
for i,h in enumerate(["ID","Funcionario","Mes/Ano","Horas realizadas","Limite","Saldo","Status"]): he.cell(3,1+i,h)
sr(he,"A3:G3",VMED,WB_)
# agrega HE gerados por pessoa e mes
from collections import defaultdict
agg=defaultdict(float)
for d,p,eid in he_events:
    dt=D0+timedelta(days=d); mes=dt.strftime("%m/%Y")
    agg[(eid,mes)]+=8.5
rows=sorted(agg.items(), key=lambda x:(-x[1]))[:60]
r=4
for (eid,mes),h in rows:
    he.cell(r,1,eid); he.cell(r,2,nome_by_id[eid]).alignment=ESQ; he.cell(r,3,mes)
    he.cell(r,4,round(h,1)); he.cell(r,5,52); he.cell(r,6,f"=E{r}-D{r}")
    he.cell(r,7,f'=IF(D{r}>E{r},"EXCEDIDO",IF(D{r}>=E{r}*0.9,"ATENCAO","OK"))')
    sr(he,f"A{r}:G{r}",None); he.cell(r,2).alignment=ESQ; r+=1
he.conditional_formatting.add(f"G4:G{r-1}", CellIsRule(operator="equal", formula=['"EXCEDIDO"'], fill=VERM))
he.conditional_formatting.add(f"G4:G{r-1}", CellIsRule(operator="equal", formula=['"ATENCAO"'], fill=AMAR))
he.freeze_panes="A4"

wb.save("Escala_Centro_Operacoes.xlsx")
print("OK. HE events:",len(he_events)," Descobertos:",descobertos," Pares conhecimento:",len(pares))
