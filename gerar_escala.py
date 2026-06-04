# -*- coding: utf-8 -*-
"""
Gera a planilha de controle de escala para um Centro de Operacoes 24h.
Saida: Escala_Centro_Operacoes.xlsx
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from datetime import date

# ----------------------------------------------------------------------------
# ESTILOS
# ----------------------------------------------------------------------------
VERDE_TIT   = PatternFill("solid", fgColor="375623")  # cabecalho escuro
VERDE_MED   = PatternFill("solid", fgColor="70AD47")
VERDE_CLR   = PatternFill("solid", fgColor="C6E0B4")
VERDE_SUAVE = PatternFill("solid", fgColor="E2EFDA")
LARANJA     = PatternFill("solid", fgColor="F8CBAD")
AZUL_CLR    = PatternFill("solid", fgColor="DDEBF7")
CINZA       = PatternFill("solid", fgColor="D9D9D9")
AMARELO     = PatternFill("solid", fgColor="FFF2CC")
VERMELHO    = PatternFill("solid", fgColor="F4CCCC")

BRANCO_BOLD = Font(bold=True, color="FFFFFF")
BOLD        = Font(bold=True)
TITULO      = Font(bold=True, size=14, color="FFFFFF")

THIN = Side(style="thin", color="A6A6A6")
BORDA = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT   = Alignment(horizontal="left", vertical="center", wrap_text=True)

def style_range(ws, rng, fill=None, font=None, border=BORDA, align=CENTER):
    for row in ws[rng]:
        for c in row:
            if fill:   c.fill = fill
            if font:   c.font = font
            if border: c.border = border
            if align:  c.alignment = align

wb = openpyxl.Workbook()

# ============================================================================
# ABA 1 - DIMENSIONAMENTO (resposta as perguntas)
# ============================================================================
ws = wb.active
ws.title = "Dimensionamento"
ws.sheet_view.showGridLines = False
widths = {"A":3,"B":46,"C":16,"D":16,"E":16,"F":16,"G":40}
for k,v in widths.items(): ws.column_dimensions[k].width = v

ws.merge_cells("B2:G2")
ws["B2"] = "DIMENSIONAMENTO DA EQUIPE - CENTRO DE OPERACOES 24h"
ws["B2"].fill = VERDE_TIT; ws["B2"].font = TITULO; ws["B2"].alignment = CENTER
ws.row_dimensions[2].height = 28

r = 4
ws[f"B{r}"] = "1) PREMISSAS DA OPERACAO"; ws[f"B{r}"].font = BOLD; ws[f"B{r}"].fill = VERDE_CLR
ws.merge_cells(f"B{r}:G{r}")
r += 1
premissas = [
    ("Postos diurnos (07:00-15:30) - 7 dias/sem", 26),
    ("Postos tarde (15:00-23:30) - 7 dias/sem", 26),
    ("Postos noturnos (23:00-07:30) - 7 dias/sem (agrupados)", 5),
    ("Postos de apoio (seg a sex, diurno)", 2),
    ("Dias de ferias por ano (por funcionario)", 30),
    ("Regime de trabalho", "6x3"),
    ("Limite de hora extra por mes (horas)", 52),
]
hdr = r
ws[f"B{r}"]="Parametro"; ws[f"C{r}"]="Valor"
style_range(ws, f"B{r}:C{r}", VERDE_MED, BRANCO_BOLD)
r += 1
for nome, val in premissas:
    ws[f"B{r}"]=nome; ws[f"C{r}"]=val
    style_range(ws, f"B{r}:B{r}", VERDE_SUAVE, None, BORDA, LEFT)
    style_range(ws, f"C{r}:C{r}", None, BOLD)
    r += 1

r += 1
ws[f"B{r}"] = "2) BASE DE CALCULO"; ws[f"B{r}"].font=BOLD; ws[f"B{r}"].fill=VERDE_CLR
ws.merge_cells(f"B{r}:G{r}")
r += 1
notas = [
 "Regime 6x3: a cada ciclo de 9 dias o funcionario trabalha 6. Fator de cobertura continua = 9/6 = 1,5 pessoas por posto.",
 "Dias uteis trabalhados/ano por pessoa (6x3): 365 x 6/9 = 243 dias.",
 "Desconto de ferias (30 dias corridos): perde ~20 dias de trabalho/ano. Disponibilidade liquida = ~223 dias/ano.",
 "Headcount por turno = (postos x 365) / 223 dias liquidos. Apoio usa 261 dias uteis/ano.",
]
for n in notas:
    ws.merge_cells(f"B{r}:G{r}")
    ws[f"B{r}"]=n; ws[f"B{r}"].alignment=LEFT; ws[f"B{r}"].font=Font(italic=True, size=9)
    ws.row_dimensions[r].height = 26
    r += 1

r += 1
ws[f"B{r}"]="3) NECESSIDADE DE PESSOAL POR TURNO"; ws[f"B{r}"].font=BOLD; ws[f"B{r}"].fill=VERDE_CLR
ws.merge_cells(f"B{r}:G{r}")
r += 1
ws[f"B{r}"]="Turno"; ws[f"C{r}"]="Postos"; ws[f"D{r}"]="Dias/ano"; ws[f"E{r}"]="Pessoa-dias"; ws[f"F{r}"]="Disp./ano"; ws[f"G{r}"]="Funcionarios"
style_range(ws, f"B{r}:G{r}", VERDE_MED, BRANCO_BOLD)
r += 1
linhas = [
    ("Diurno 07:00-15:30", 26, 365, 223),
    ("Tarde 15:00-23:30", 26, 365, 223),
    ("Noturno 23:00-07:30 (5 agrupados)", 5, 365, 223),
    ("Apoio seg-sex (diurno)", 2, 261, 223),
]
primeira = r
for nome, postos, dias, disp in linhas:
    ws[f"B{r}"]=nome
    ws[f"C{r}"]=postos
    ws[f"D{r}"]=dias
    ws[f"E{r}"]=f"=C{r}*D{r}"
    ws[f"F{r}"]=disp
    ws[f"G{r}"]=f"=ROUNDUP(E{r}/F{r},0)"
    style_range(ws, f"B{r}:B{r}", VERDE_SUAVE, None, BORDA, LEFT)
    style_range(ws, f"C{r}:G{r}")
    ws[f"G{r}"].font = BOLD
    r += 1
ult = r-1
ws[f"B{r}"]="TOTAL DE FUNCIONARIOS (efetivo)"; ws[f"B{r}"].font=BOLD
ws[f"G{r}"]=f"=SUM(G{primeira}:G{ult})"; ws[f"G{r}"].font=Font(bold=True,size=12)
style_range(ws, f"B{r}:G{r}", AMARELO, BOLD)
total_row = r
r += 2

ws[f"B{r}"]="4) FIXOS x VARIAVEIS (continuidade no posto)"; ws[f"B{r}"].font=BOLD; ws[f"B{r}"].fill=VERDE_CLR
ws.merge_cells(f"B{r}:G{r}")
r += 1
ws.merge_cells(f"B{r}:G{r}")
ws[f"B{r}"]=("Estrategia: 1 TITULAR fixo por posto (mantem a mesma pessoa no mesmo posto). "
            "Os demais sao VOLANTES/COBERTURA, que cobrem folgas, ferias e faltas e por isso tem posto variavel.")
ws[f"B{r}"].alignment=LEFT; ws[f"B{r}"].font=Font(italic=True,size=9); ws.row_dimensions[r].height=28
r += 1
ws[f"B{r}"]="Categoria"; ws[f"C{r}"]="Qtde"; ws[f"D{r}"]="Observacao"
ws.merge_cells(f"D{r}:G{r}")
style_range(ws, f"B{r}:G{r}", VERDE_MED, BRANCO_BOLD)
r += 1
# titulares = 26+26+5+2 = 59
ws[f"B{r}"]="Titulares (POSTO FIXO)"; ws[f"C{r}"]="=26+26+5+2"
ws.merge_cells(f"D{r}:G{r}"); ws[f"D{r}"]="Um por posto (26 diurno + 26 tarde + 5 noite + 2 apoio)"
ws[f"D{r}"].alignment=LEFT
fixos_row=r
style_range(ws, f"B{r}:C{r}"); ws[f"C{r}"].font=BOLD; ws[f"D{r}"].border=BORDA
r += 1
ws[f"B{r}"]="Volantes / Cobertura (POSTO VARIAVEL)"; ws[f"C{r}"]=f"=G{total_row}-C{fixos_row}"
ws.merge_cells(f"D{r}:G{r}"); ws[f"D{r}"]="Cobrem folgas do 6x3, ferias e faltas; rodam entre postos"
ws[f"D{r}"].alignment=LEFT
style_range(ws, f"B{r}:C{r}", VERDE_SUAVE); ws[f"C{r}"].font=BOLD; ws[f"D{r}"].border=BORDA
r += 2

ws[f"B{r}"]="5) HORA EXTRA (folga de seguranca)"; ws[f"B{r}"].font=BOLD; ws[f"B{r}"].fill=VERDE_CLR
ws.merge_cells(f"B{r}:G{r}")
r += 1
ws.merge_cells(f"B{r}:G{r}")
ws[f"B{r}"]=("Faltas/atestados imprevistos sao cobertos por hora extra (limite 52h/mes por pessoa). "
            "Uma jornada de cobertura = 8,5h, entao cada pessoa pode fazer ate ~6 coberturas extras/mes. Ver aba 'Horas Extras'.")
ws[f"B{r}"].alignment=LEFT; ws[f"B{r}"].font=Font(italic=True,size=9); ws.row_dimensions[r].height=30

# ============================================================================
# ABA 2 - POSTOS
# ============================================================================
postos_diurnos = [
    ("CENTRO","BH/NL"),("CENTRO","SG/AR"),("CENTRO","BT"),("CENTRO","SL"),
    ("LESTE","GV"),("LESTE","RA/PO"),("LESTE","TO/PR"),("LESTE","IP/AG"),
    ("OESTE","DV/IJ"),("OESTE","FM/CL"),("OESTE","IA/CR"),
    ("NORTE","MO/SI"),("NORTE","PT/AL"),("NORTE","JN/BC"),("NORTE","JB/PI"),
    ("MANTIQUEIRA","JF/OP"),("MANTIQUEIRA","PN/LV"),("MANTIQUEIRA","LF/BD"),
    ("TRIANGULO","UL/IR"),("TRIANGULO","PM/PS"),("TRIANGULO","TB/AF"),("TRIANGULO","UR/JM"),
    ("SUL","PA/SJ"),("SUL","TC/FR"),("SUL","VR/AX"),
    ("CENTRO","CN/MG"),  # 26o posto
]
postos_noite = [("NOITE","N1 (CENTRO+LESTE)"),("NOITE","N2 (OESTE)"),
                ("NOITE","N3 (NORTE)"),("NOITE","N4 (MANTIQ+TRIANG)"),("NOITE","N5 (SUL)")]
postos_apoio = [("APOIO","APOIO-1"),("APOIO","APOIO-2")]

ws2 = wb.create_sheet("Postos")
ws2.sheet_view.showGridLines = False
for col,w in zip("ABCD",[4,16,22,18]): ws2.column_dimensions[col].width=w
ws2.merge_cells("B2:D2"); ws2["B2"]="CADASTRO DE POSTOS"; ws2["B2"].fill=VERDE_TIT; ws2["B2"].font=TITULO; ws2["B2"].alignment=CENTER
hdr=["Cod","Malha","Posto","Turno"]
ws2["A4"]="ID"
for i,h in enumerate(["Malha","Posto","Turno"]): ws2.cell(4,2+i,h)
style_range(ws2,"A4:D4",VERDE_MED,BRANCO_BOLD)
rr=5; pid=1
for grupo, lst, turno in [("Diurno",postos_diurnos,"07:00-15:30"),
                          ("Tarde",postos_diurnos,"15:00-23:30"),
                          ("Noite",postos_noite,"23:00-07:30"),
                          ("Apoio",postos_apoio,"Apoio seg-sex")]:
    for malha, posto in lst:
        ws2.cell(rr,1,pid); ws2.cell(rr,2,malha); ws2.cell(rr,3,posto); ws2.cell(rr,4,turno)
        fill = {"Diurno":VERDE_SUAVE,"Tarde":AZUL_CLR,"Noite":CINZA,"Apoio":AMARELO}[grupo]
        style_range(ws2,f"A{rr}:D{rr}",fill)
        rr+=1; pid+=1

# ============================================================================
# ABA 3 - FUNCIONARIOS
# ============================================================================
ws3 = wb.create_sheet("Funcionarios")
ws3.sheet_view.showGridLines=False
for col,w in zip("ABCDEF",[4,26,16,18,16,16]): ws3.column_dimensions[col].width=w
ws3.merge_cells("B2:F2"); ws3["B2"]="CADASTRO DE FUNCIONARIOS"; ws3["B2"].fill=VERDE_TIT; ws3["B2"].font=TITULO; ws3["B2"].alignment=CENTER
heads=["ID","Nome","Tipo","Turno base","Posto titular","Inicio ferias"]
for i,h in enumerate(heads): ws3.cell(4,1+i,h)
style_range(ws3,"A4:F4",VERDE_MED,BRANCO_BOLD)
# 98 funcionarios: nomes da foto + genericos
nomes_foto = ["Felipe Generoso","Cristiano Alisson","Marcelo Thiersch","Elenise Ceres",
"Rodrigo Mesquita","Leandro Bruno","Samuel Mazoni","Vinicius Lima","Victor Ricarte",
"Hugo Tavares","Joao Paulo","Linneker Amaral","Wesley Ramos","Normando Guimaraes",
"Ronaldo Soares","Andre dos Anjos","Samuel Henrique","Welinton Barbosa","Marllon Bastos",
"Gilmar Jose","Leonardo Henrique","Nicolas Augusto","Antonio Carlos","Rafel Teles","Erick Garcia"]
dv=DataValidation(type="list",formula1='"Titular,Volante"',allow_blank=True)
ws3.add_data_validation(dv)
TOTAL_FUNC=98
for i in range(TOTAL_FUNC):
    rr=5+i
    nome = nomes_foto[i] if i<len(nomes_foto) else f"Funcionario {i+1:03d}"
    tipo = "Titular" if i<59 else "Volante"
    ws3.cell(rr,1,i+1); ws3.cell(rr,2,nome).alignment=LEFT
    c=ws3.cell(rr,3,tipo); dv.add(c)
    ws3.cell(rr,4,""); ws3.cell(rr,5,""); ws3.cell(rr,6,"")
    style_range(ws3,f"A{rr}:F{rr}", VERDE_SUAVE if tipo=="Titular" else AZUL_CLR)
    ws3.cell(rr,2).alignment=LEFT

# ============================================================================
# ABA 4 - ESCALA (modelo no padrao da foto)
# ============================================================================
ws4 = wb.create_sheet("Escala (modelo)")
ws4.sheet_view.showGridLines=False
for col,w in zip("ABCD",[4,18,16,26]): ws4.column_dimensions[col].width=w
ws4.merge_cells("A1:D1")
ws4["A1"]="DIA 04/06/2026 - TURNO 07:00 as 15:30 h (G1)"
ws4["A1"].fill=VERDE_MED; ws4["A1"].font=BRANCO_BOLD; ws4["A1"].alignment=CENTER
for i,h in enumerate(["MALHA","POSTO","TECNICO"]):
    ws4.cell(2,1+i,h)
ws4.merge_cells("C2:D2")
style_range(ws4,"A2:D2",VERDE_CLR,BOLD)
rr=3
malha_atual=None; ini=None
diurnos_so = postos_diurnos
for idx,(malha,posto) in enumerate(diurnos_so):
    ws4.cell(rr,2,posto)
    ws4.merge_cells(f"C{rr}:D{rr}")
    ws4.cell(rr,3,"")  # preencher tecnico
    style_range(ws4,f"A{rr}:D{rr}",VERDE_SUAVE)
    if malha!=malha_atual:
        if malha_atual is not None:
            ws4.merge_cells(f"A{ini}:A{rr-1}")
            ws4.cell(ini,1,malha_atual).alignment=CENTER
        malha_atual=malha; ini=rr
    rr+=1
ws4.merge_cells(f"A{ini}:A{rr-1}"); ws4.cell(ini,1,malha_atual).alignment=CENTER
ws4.cell(rr,1,"Supervisor"); ws4.merge_cells(f"A{rr}:B{rr}")
ws4.merge_cells(f"C{rr}:D{rr}"); ws4.cell(rr,3,"")
style_range(ws4,f"A{rr}:D{rr}",VERDE_MED,BRANCO_BOLD)

# ============================================================================
# ABA 5 - BANCO DE CONHECIMENTO (PESOS) com decaimento
# ============================================================================
ws5 = wb.create_sheet("Banco Conhecimento")
ws5.sheet_view.showGridLines=False
ws5.merge_cells("B2:I2")
ws5["B2"]="BANCO DE CONHECIMENTO - PESOS POR POSTO"
ws5["B2"].fill=VERDE_TIT; ws5["B2"].font=TITULO; ws5["B2"].alignment=CENTER
# Regras
ws5.merge_cells("B3:I3")
ws5["B3"]=("Regra: +1 ponto por dia despachado no posto. Apos 180 dias (6 meses) sem despachar, "
           "perde 1 ponto por dia ate zerar. 'Pontos efetivos' aplica o decaimento automaticamente.")
ws5["B3"].alignment=LEFT; ws5["B3"].font=Font(italic=True,size=9); ws5.row_dimensions[3].height=28
ws5["B5"]="HOJE:"; ws5["C5"]="=TODAY()"; ws5["C5"].number_format="dd/mm/yyyy"; ws5["B5"].font=BOLD

heads=["ID Func.","Funcionario","Posto","Dias despachados","Ultimo despacho",
       "Dias parado","Decaimento","Pontos efetivos","Nivel"]
for i,h in enumerate(heads): ws5.cell(7,2+i,h)
style_range(ws5,"B7:J7",VERDE_MED,BRANCO_BOLD)
for col,w in zip("ABCDEFGHIJ",[3,9,24,16,16,16,12,12,14,12]): ws5.column_dimensions[col].width=w

# Exemplos preenchidos (alguns) + estrutura para preencher
exemplos=[
 (1,"Felipe Generoso","BH/NL",420, date(2026,6,1)),
 (1,"Felipe Generoso","SG/AR",35,  date(2025,9,10)),
 (4,"Elenise Ceres","SL",380,      date(2026,5,28)),
 (25,"Erick Garcia","VR/AX",512,   date(2026,6,3)),
 (25,"Erick Garcia","PA/SJ",18,    date(2025,7,1)),
 (7,"Samuel Mazoni","TO/PR",260,   date(2026,5,30)),
]
rr=8
for fid,nome,posto,dias,ult in exemplos:
    ws5.cell(rr,2,fid)
    ws5.cell(rr,3,nome).alignment=LEFT
    ws5.cell(rr,4,posto)
    ws5.cell(rr,5,dias)
    c=ws5.cell(rr,6,ult); c.number_format="dd/mm/yyyy"
    ws5.cell(rr,7,f'=IF(F{rr}="","",$C$5-F{rr})')          # dias parado
    ws5.cell(rr,8,f'=IF(F{rr}="",0,MAX(0,G{rr}-180))')     # decaimento
    ws5.cell(rr,9,f'=MAX(0,E{rr}-H{rr})')                  # pontos efetivos
    ws5.cell(rr,10,f'=IF(I{rr}>=180,"Especialista",IF(I{rr}>=60,"Apto",IF(I{rr}>0,"Basico","Sem pratica")))')
    style_range(ws5,f"B{rr}:J{rr}",VERDE_SUAVE)
    ws5.cell(rr,3).alignment=LEFT
    rr+=1
# linhas em branco prontas com formula
for _ in range(40):
    ws5.cell(rr,7,f'=IF(F{rr}="","",$C$5-F{rr})')
    ws5.cell(rr,8,f'=IF(F{rr}="",0,MAX(0,G{rr}-180))')
    ws5.cell(rr,9,f'=IF(E{rr}="","",MAX(0,E{rr}-H{rr}))')
    ws5.cell(rr,10,f'=IF(E{rr}="","",IF(I{rr}>=180,"Especialista",IF(I{rr}>=60,"Apto",IF(I{rr}>0,"Basico","Sem pratica"))))')
    style_range(ws5,f"B{rr}:J{rr}",None)
    rr+=1

# ============================================================================
# ABA 6 - HORAS EXTRAS
# ============================================================================
ws6 = wb.create_sheet("Horas Extras")
ws6.sheet_view.showGridLines=False
ws6.merge_cells("B2:H2")
ws6["B2"]="CONTROLE DE HORAS EXTRAS (limite 52h/mes)"
ws6["B2"].fill=VERDE_TIT; ws6["B2"].font=TITULO; ws6["B2"].alignment=CENTER
heads=["ID","Funcionario","Mes/Ano","Horas realizadas","Limite","Saldo","Status"]
for i,h in enumerate(heads): ws6.cell(4,2+i,h)
style_range(ws6,"B4:H4",VERDE_MED,BRANCO_BOLD)
for col,w in zip("ABCDEFGH",[3,8,26,14,16,10,10,18]): ws6.column_dimensions[col].width=w
rr=5
for i in range(30):
    ws6.cell(rr,6,52)  # limite
    ws6.cell(rr,7,f'=IF(E{rr}="","",F{rr}-E{rr})')  # saldo
    ws6.cell(rr,8,f'=IF(E{rr}="","",IF(E{rr}>F{rr},"EXCEDIDO",IF(E{rr}>=F{rr}*0.9,"ATENCAO","OK")))')
    if i<3:
        ws6.cell(rr,2,[1,7,25][i]); ws6.cell(rr,3,["Felipe Generoso","Samuel Mazoni","Erick Garcia"][i]).alignment=LEFT
        ws6.cell(rr,4,"06/2026"); ws6.cell(rr,5,[34,51,17][i])
    style_range(ws6,f"B{rr}:H{rr}",VERDE_SUAVE if i<3 else None)
    rr+=1

# Formatacao condicional simples nao essencial; salvar
wb.save("Escala_Centro_Operacoes.xlsx")
print("OK - arquivo gerado")
