from django.views import View
from django.template.loader import get_template
from django.http import HttpResponse
import os
from django.contrib import messages
from django.shortcuts import redirect, render
from efacture.models import *
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Table, SimpleDocTemplate, TableStyle, Spacer, Paragraph
from reportlab import platypus
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from num2words import num2words
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from django.http import Http404
from datetime import datetime
import textwrap
import re
from django.db.models import Sum

def Login_To_Continue_Handler(requests, *args, **kwargs):
    messages.error(requests, "S'il vous plait Connectez-vous d'abord : )")
    respond = redirect('/login/')
    respond.set_cookie('REDIRECT_AFTER_LOGIN',
                       requests.get_full_path(), max_age=60)
    return respond

def Your_Account_Has_Been_Suspended(requests, *args, **kwargs):
    messages.error(requests, "Votre compte utilisateur a été suspendu")
    requests.session.flush()
    return redirect('/login')

def PermissionErrMsg_and_Warning_Handler(requests, what, what_detail, Who, context, template):
    APP_Warning.objects.create(what=what, what_detail=what_detail, Who=Who)
    PermissionMessage = f"vous n'êtes pas autorisé à {what} cette facture, contactez l'administrateur<br>(cette action sera signalée à l'administrateur)"
    context['PermissionMessage'] = PermissionMessage
    return render(requests, template, context)

def generate_table_of_facture_items(factureitemsobj, showaction=True):
    tablebody = []
    for item in factureitemsobj:
        Qs = str(item.Qs).strip()
        DESIGNATION = str(item.DESIGNATION).strip()
        PU = str(item.PU).strip()
        PT = str(item.PT).strip()
        D = {}
        D['Qs'] = Qs
        D['DT'] = DESIGNATION
        D['PU'] = PU
        D['PT'] = PT
        if showaction == True:
            action = """
                        <button type="button" class="btn btn-danger btn-sm" onclick="DeleteSelectedRow(this);"><i class="fas fa-trash"></i></button>\n
                        <button type="button" id="editrow" class="btn btn-info btn-sm" style="margin-left: 12px;padding-right: 6px;" onclick="EditSelectedRow(this);"><i class="fas fa-edit"></i></button>
                    """
            D['Action'] = action
        tablebody.append(D)
    return tablebody

def generate_table_of_clients(showaction=True, allclients=''):
    tablebody = []
    for client in allclients:
        D = {}
        name = client.Client_Name
        ICE = client.ICE
        City = client.City
        NOS = client.Number_Of_Use
        if showaction:
            D['name'] = name
            D['ICE'] = ICE
            D['City'] = City
            D['Action'] = f"""<a class='btn btn-info  btn-sm' href='#' onclick='EditClient(this,\"/settings/manage-clients/edit/{client.id}\")' title='Edit' data-toggle='tooltip'>
                                                <i class='fas fa-pencil-alt'></i>\n</a>
                            <a class='btn btn-danger btn-sm' href='#' title='Delete' onclick='EnterPwdToDeletePopup(\"/settings/manage-clients/delete/{client.id}\");' data-toggle='tooltip'>
                                        <i class='fas fa-trash'></i></a>\n"""
        else:
            D['name'] = name
            D['ICE'] = ICE
            D['City'] = City

        tablebody.append(D)
    return tablebody

def generate_table_of_products(showaction=True, Products=''):
    tablebody = []
    for product in Products:
        D = {}
        name = product.DESIGNATION
        PU = product.PU
        D['name'] = name
        D['PU'] = PU
        if showaction == True:
            D['Action'] = f"""<a class='btn btn-info  btn-sm' href='#' onclick='EditProduct(this,\"/settings/manage-products/edit/{product.id}\")' title='Edit' data-toggle='tooltip'>
                                                <i class='fas fa-pencil-alt'></i>\n</a>
                                    <a class='btn btn-danger btn-sm' href='#' title='Delete' onclick='EnterPwdToDeletePopup(\"/settings/manage-products/delete/{product.id}\");' data-toggle='tooltip'>
                                                <i class='fas fa-trash'></i></a>\n"""
        tablebody.append(D)
    return tablebody

def generate_table_of_created_factures(showaction='all', factures=''):
    TVA_taux = int(APP_Settings.objects.all().first().Company_TVATAUX)
    factures = list(factures)[::-1]
    tablebody = []
    for facture in factures:
        facture_number = f"{str(facture.number).zfill(3)}/{facture.Date.strftime('%Y')}"
        client = facture.Client.Client_Name
        date = facture.Date.strftime('%d/%m/%Y')
        isPaid = facture.isPaid
        Avance  = facture.Avance
        HT = facture.HT
        TVA = facture.TVA
        TTC = facture.TTC
        D = {}
        D['N'] = facture_number
        D['client'] = f'{client}<br>{facture.Client.ICE}'
        D['date'] = date
        if isPaid == 'Oui':
            D['status'] = f'''<form id="StatusForm{facture.id}" method="POST" action="/facture-status/ajax/update/{facture.id}"><input type="hidden" name="status" value="Oui"><button class="btn btn-success btn-sm" type="button"  onclick="SubmitThisForm('StatusForm{facture.id}')" style="font-size: 14px;"><span id='IconSpin' class="spinner-border spinner-border-sm" style='display:none'></span> Payée</button></form>'''
        elif isPaid == 'Non':
            D['status'] = f'''<form id="StatusForm{facture.id}" method="POST" action="/facture-status/ajax/update/{facture.id}"><input type="hidden" name="status" value="Non"><button class="btn btn-danger btn-sm" type="button" onclick="SubmitThisForm('StatusForm{facture.id}')" style="font-size: 14px;" ><span id='IconSpin' class="spinner-border spinner-border-sm" style='display:none'></span> Non Payée</button></form>'''
        D['avance'] = Avance
        if facture.TTCorHT == 'TTC':
            D['reste'] = str(round(TTC - Avance,2))+' TTC'
        elif facture.TTCorHT == 'HT':
            D['reste'] = str(round(HT - Avance,2))+' HT'
        D['HT'] = round(HT,2)
        D['TVA'] = round(TVA,2)
        D['TTC'] = round(TTC,2)

        if showaction == 'all':
            D['Action'] = f'''<a class="btn btn-info btn-sm" href="/list-all-facturs/edit/{facture.id}" title="Edit" data-toggle="tooltip">
                                    <i class="fas fa-pencil-alt"></i>\n</a> 
                                <a class="btn btn-danger btn-sm" href="#" onclick="EnterPwdToDeletePopup(\'/list-all-facturs/delete/{facture.id}\');" title="Delete" data-toggle="tooltip">
                                    <i class="fas fa-trash"></i></a>\n
                                <a href="/list-all-facturs/detail/open/{facture.id}" target="_blank" class="btn btn-success btn-sm"><i class="fas fa-eye"></i></a>
                                '''

        elif showaction == 'Detail-Edit':
            D['Action'] = f'''<a class="btn btn-info btn-sm" href="/list-all-facturs/edit/{facture.id}" title="Edit" target='_blank' data-toggle="tooltip">
                                    <i class="fas fa-pencil-alt"></i>\n</a> 
                                <a href="/list-all-facturs/detail/open/{facture.id}" target="_blank" class="btn btn-success btn-sm"><i class="fas fa-eye"></i></a>
                            '''
        tablebody.append(D)
    return tablebody

def generate_table_of_history(histories, simpletable=False):
    histories = list(histories)[::-1]
    tablebody = []
    for history in histories:
        D = {}
        actor = history.CreatedBy
        action = history.action
        date = history.DateTime
        D['actor'] = actor
        D['action'] = action
        D['date'] = Fix_Date(date)
        if simpletable == False:
            action_detail = history.action_detail
            D['action_detail'] = action_detail
        tablebody.append(D)
    return tablebody

def generate_table_of_devis(devis=''):
    devis = list(devis)[::-1]
    tablebody = []
    for dv in devis:
        Devis_number = dv.number
        client = dv.Client.Client_Name
        date = dv.Date
        CreatedBy = dv.CreatedBy
        HT = dv.HT
        D = {}
        D['Serie'] =  f"{str(Devis_number).zfill(3)}/{date.strftime('%Y')}"
        D['client'] = client
        D['date'] = date.strftime('%d/%m/%Y')
        D['HT'] = HT
        D['Action'] = f'''<a class="btn btn-info btn-sm" href="/list-all-devis/edit/{dv.id}" title="Edit" data-toggle="tooltip">
                                <i class="fas fa-pencil-alt"></i>\n</a> 
                            <a class="btn btn-danger btn-sm" href="#" onclick="EnterPwdToDeletePopup(\'/list-all-devis/delete/{dv.id}\');" title="Delete" data-toggle="tooltip">
                                <i class="fas fa-trash"></i></a>\n
                            <a href="/list-all-devis/detail/open/{dv.id}" target="_blank" class="btn btn-success btn-sm"><i class="fas fa-eye"></i></a>
                            <a href="/devis-to-facture/{dv.id}" target="_blank" class="btn btn-warning btn-sm"><i class="fas fa-sync-alt"></i></a>
                            '''
        tablebody.append(D)
    return tablebody


def generate_table_of_BL(BL=''):
    BL = list(BL)[::-1]
    tablebody = []
    for bl in BL:
        BL_number = bl.number
        client = bl.Client.Client_Name
        date = bl.Date
        CreatedBy = bl.CreatedBy
        HT = bl.HT

        D = {}
        D['choose'] = f'<input class="form-check-input check-box" id="{bl.id}" type="checkbox">'
        D['Serie'] = f"{str(BL_number).zfill(3)}/{date.strftime('%Y')}"
        D['client'] = client
        D['date'] = date.strftime('%d/%m/%Y')
        D['HT'] = HT        
        D['Action'] = f'''<a class="btn btn-info btn-sm" href="/list-all-bl/edit/{bl.id}" title="Edit" data-toggle="tooltip">
                                <i class="fas fa-pencil-alt"></i>\n</a> 
                            <a class="btn btn-danger btn-sm" href="#" onclick="EnterPwdToDeletePopup(\'/list-all-bl/delete/{bl.id}\');" title="Delete" data-toggle="tooltip">
                                <i class="fas fa-trash"></i></a>\n
                            <a href="/list-all-bl/detail/open/{bl.id}" target="_blank" class="btn btn-success btn-sm"><i class="fas fa-eye"></i></a>
                            '''
        tablebody.append(D)
    return tablebody


def generate_table_of_devis_items(Devis_items=''):
    tablebody = []
    for item in Devis_items:
        Qs = str(item.Qs).strip()
        DESIGNATION = str(item.DESIGNATION).strip()
        PU = str(item.PU).strip()
        PT = str(item.PT).strip()
        D = {}
        D['Qs'] = Qs
        D['DT'] = DESIGNATION
        D['PU'] = PU
        D['PT'] = PT
        action = """
                    <button type="button" class="btn btn-danger btn-sm" onclick="DeleteSelectedRow(this);"><i class="fas fa-trash"></i></button>\n
                    <button type="button" id="editrow" class="btn btn-info btn-sm" style="margin-left: 12px;padding-right: 6px;" onclick="EditSelectedRow(this);"><i class="fas fa-edit"></i></button>
                """
        D['Action'] = action
        tablebody.append(D)
    return tablebody


def generate_table_of_BL_items(BL_items=''):
    tablebody = []
    for item in BL_items:
        Qs = str(item.Qs).strip()
        DESIGNATION = str(item.DESIGNATION).strip()
        PU = str(item.PU).strip()
        PT = str(item.PT).strip()
        D = {}
        D['Qs'] = Qs
        D['DT'] = DESIGNATION
        D['PU'] = PU
        D['PT'] = PT
        action = """
                    <button type="button" class="btn btn-danger btn-sm" onclick="DeleteSelectedRow(this);"><i class="fas fa-trash"></i></button>\n
                    <button type="button" id="editrow" class="btn btn-info btn-sm" style="margin-left: 12px;padding-right: 6px;" onclick="EditSelectedRow(this);"><i class="fas fa-edit"></i></button>
                """
        D['Action'] = action
        tablebody.append(D)
    return tablebody


def Calcule_TVA_TOTAL_TTC(factureitemsobj):
    TOTAL = 0
    TVA_taux = int(APP_Settings.objects.all().first().Company_TVATAUX)
    for item in factureitemsobj:
        PT = float(item.PT)
        TOTAL = TOTAL + PT
    TVA = TOTAL / 100 * TVA_taux
    TTC = TOTAL + TVA
    return (TOTAL, TVA, TTC)

def Fix_Date(date):
    try:
        format = "%Y-%m-%d %H:%M:%S.%f%z"
        date = datetime.strptime(str(date), format)
    except Exception:
        format = "%Y-%m-%d %H:%M:%S.%f"
        date = datetime.strptime(str(date), format)
    format = "%Y-%m-%d %H:%M:%S"
    date = datetime.strftime(date, format)
    return date

def CheckNewNumberisNotExsit(obj):
    pass

def GetNewNumber(obj):
    All_IDs = [o.number for o in obj.objects.all()]
    new_number = len(All_IDs) + 1
    while new_number in All_IDs:
        new_number = new_number + 1
    return new_number


def GetClientsListWith_ID():
    Clients = [(f'{str(clientname.Client_Name).upper()}:{str(clientname.City).title()}',clientname.id) for clientname in list(APP_Clients.objects.all())]
    return Clients
