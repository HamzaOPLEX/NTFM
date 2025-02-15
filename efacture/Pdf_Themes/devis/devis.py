import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Table, SimpleDocTemplate, TableStyle, Spacer, Paragraph , PageBreak
from reportlab import platypus
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from pathlib import Path
from num2words import num2words
from efacture.models import APP_Settings
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
import textwrap
from colour import Color

def DrawNotechPdf(DevisObj, DevisItemsObj, Company_City):
    Table_Color = Color(APP_Settings.objects.all().first().Invoice_Color)
    Table_Color = Table_Color.rgb
    def draw_wrapped_line(canvas, text, length, x_pos, y_pos, y_offset):
        if len(text) > length:
            wraps = textwrap.wrap(text, length)
            for x in range(len(wraps)):
                canvas.drawCentredString(x_pos, y_pos, wraps[x])
                y_pos -= y_offset
            y_pos += y_offset  # add back offset after last wrapped line
        else:
            canvas.drawCentredString(x_pos, y_pos, text)
        return y_pos

    story = []
    BASE_DIR = Path(__file__).resolve().parent
    GLOBAL_CONFIG_PATH = str(str(BASE_DIR.parent)+"/global_config/")

    Date = DevisObj.Date.strftime('%d-%m-%Y')
    Year = DevisObj.Date.strftime('%Y')
    tabledata = []
    header = ('QS', 'DISIGNATION', 'P.U', 'PT')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ClientSide',
                              alignment=TA_LEFT,
                              fontName='Helvetica',
                              fontSize=10,
                              textColor=colors.black,
                              leading=13,
                              wordWrap='LTR',
                              splitLongWords=True,
                              spaceShrinkage=0.05,
                              backColor=None,
                              borderWidth=1,
                              borderPadding=10,
                              borderColor=colors.black,
                              borderRadius=8

                              ))
    styles.add(ParagraphStyle(name='CompanySide',
                              alignment=TA_LEFT,
                              fontName='Helvetica',
                              fontSize=10,
                              textColor=colors.black,
                              leading=13,
                              wordWrap='LTR',
                              splitLongWords=True,
                              spaceShrinkage=0.05,
                              backColor=None,
                              borderWidth=1,
                              borderPadding=10,
                              borderColor=colors.black,
                              borderRadius=8
                              ))
    styles.add(ParagraphStyle(name='HeaderDataStyle',
                              alignment=TA_LEFT,
                              fontName='Helvetica',
                              fontSize=10,
                              textColor=colors.black,
                              leading=13,
                              textTransform='uppercase',
                              wordWrap='LTR',
                              splitLongWords=True,
                              spaceShrinkage=0.05,
                              backColor=None,
                              borderWidth=1,
                              borderPadding=10,
                              borderColor=colors.black,
                              ))
    styles.add(ParagraphStyle(name='FooterMessage',
                              alignment=TA_CENTER,
                              fontName='Helvetica',
                              fontSize=11,
                              textColor=colors.black,
                              leading=13,
                              wordWrap='LTR',
                              splitLongWords=True,
                              spaceShrinkage=0.05,
                              ))

    def Number2Letter(number):
        if ',' in str(number):
            number = number.replace(',', '')
        elif '.' in str(number):
            number = round(float(number), 2)
            number = str(number).split('.')
            # Befor point
            part01 = str(num2words(int(number[0]), lang='fr')+' Dirhams Et ')
            # After point
            part02 = str(num2words(int(number[1]), lang='fr')+' Centimes')
            allNumber_Parts = part01 + part02
            return allNumber_Parts.title()
        else:
            number = num2words(int(number), lang='fr')+' Dirhams'
            return number.title()

    # - Start TOTAL,TVA,TTC Table Handler - ##################################################
    TOTALint = DevisObj.HT
    TOTAL = ['', 'TOTAL HT', round(TOTALint, 2)]
    TOTALtableData = [TOTAL]
    TOTALletter = Number2Letter(str(TOTALint))

    def Info_Table(tabledata):
        colwidths = (200, 90, 200)
        t = Table(tabledata, colwidths)
        t.hAlign = 'CENTER'
        GRID_STYLE = TableStyle(
            [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER')
            ]
        )
        t.setStyle(GRID_STYLE)
        return t

    def TOTAL_table(tabledata):
        colwidths = (0, 60, 60)
        t = Table(tabledata, colwidths)
        t.hAlign = 'RIGHT'
        GRID_STYLE = TableStyle(
            [('GRID', (0, 0), (-1, -1), 0.25, colors.black),
             ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ]
        )
        t.setStyle(GRID_STYLE)
        return t
    # - End TOTAL,TVA,TTC Table Handler - ################################################

    def DrawPageImages(canvas, doc):
        canvas.saveState()
        canvas.drawImage(GLOBAL_CONFIG_PATH+"invoice-bg.png", 0, 0, 600, 840)
        canvas.restoreState()

    #create the table for our document
    def myTable(tabledata):
        colwidths = (30, 350, 60, 60)
        t = Table(tabledata, colwidths)
        t.hAlign = 'RIGHT'
        GRID_STYLE = TableStyle(
            [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                ('LINEBEFORE', (0, 1), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), Table_Color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ]
        )
        t.setStyle(GRID_STYLE)
        return t

    HeaderDataStyle = styles['HeaderDataStyle']
    FooterMessage = styles['FooterMessage']
    ClientSide = styles['ClientSide']
    CompanySide = styles['CompanySide']
    company_side = f"""
                <b>Client:</b> {str(DevisObj.Client.Client_Name).title()}<br/>
                <b>ICE :</b> {str(DevisObj.Client.ICE).title()}<br/>
                """
    client_side = f"""
                    <b>Devis :</b> {str(DevisObj.number).zfill(3)}/{Year}<br/>
                    <b>{str(Company_City).upper()} le:</b> {DevisObj.Date}"""

    client_company_table_data = [
        [Paragraph(client_side, ClientSide), '',
         Paragraph(company_side, CompanySide)],
    ]
    client_company_table = Info_Table(client_company_table_data)


    def chunks(l, n):
        n = max(1, n)
        return (l[i:i+n] for i in range(0, len(l), n))

    def colr(x, y, z):
        return (x/255, y/255, z/255)
    # change this to for item in Devis items , tabledata.append(item)

    for item in DevisItemsObj:
        row = [str(item.Qs).strip(), str(item.DESIGNATION).strip().title(),
               str(item.PU).strip(), str(item.PT).strip()]
        tabledata.append(row)
    MAX_ROWS = 30

    tabledata = list(chunks(tabledata,MAX_ROWS))
    for chunk in tabledata :
        if len(chunk) <= MAX_ROWS:
            emptyrows_needed = MAX_ROWS-int(len(chunk))
            for i in range(emptyrows_needed):
                empty_row = ['', '', '', '']
                chunk.append(empty_row)
        story.append(Spacer(1, .25*inch))
        story.append(client_company_table)
        story.append(Spacer(1, .25*inch))
        chunk.insert(0,header)
        tabmestle = myTable(chunk)
        story.append(tabmestle)
        # check if chunk is last element in tabledata so add TOTAL info to the last table in pages
        if tabledata.index(chunk) == tabledata.index(tabledata[-1]):
            story.append(TOTAL_table(TOTALtableData,))
            story.append(Spacer(1, .25*inch))
            # Money_msg = f"Arrêté le Présente  facture  la somme de {TOTALletter}  TTC"
            # story.append(Paragraph(Money_msg,FooterMessage))

        story.append(PageBreak())

    filename = f'{DevisObj.Client.Client_Name}-{str(DevisObj.number).zfill(3)}-{Date}' 
    filepath = os.path.join(BASE_DIR.parent.parent.parent,'static')+f"/PDF_FILES/{filename}.pdf"

    doc = SimpleDocTemplate(filepath, pagesize=A4, pagetitle='filename',rightMargin=43, leftMargin=43,topMargin=100, bottomMargin=23)
    doc.title = filename
    doc.author = 'E-FACTURE - Dev Team'

    doc.build(story, onFirstPage=DrawPageImages, onLaterPages=DrawPageImages)

    return filepath
