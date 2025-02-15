import json
import os
import shutil
from datetime import datetime, timedelta
from urllib.parse import unquote

from Functions.APPfunctions import *
from efacture.Handlers.AUTH_Handler import RequireLogin, RequirePermission
from efacture.Handlers.ERROR_Handlers import *
from efacture.models import *
from efacture.Pdf_Themes.devis.devis import DrawNotechPdf
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.http import FileResponse, JsonResponse
from django.shortcuts import HttpResponse, get_object_or_404, redirect, render


@RequireLogin
def H_Create_New_Devis(requests):
    # Get Loged User Id from Session_id
    userid = requests.session['session_id']
    User = get_object_or_404(APP_User, id=userid)
    # Get All Deviss From DB And Work With them
    All_Deviss = APP_Created_Devis.objects.all()
    new_devis_number = GetNewNumber(APP_Created_Devis)
    context = {
        'pagetitle': 'Nouvelle Devis',
        'todaydate': datetime.today().strftime('%Y-%m-%d'),
        'new_Devis_number': GetNewNumber(APP_Created_Devis),
        'User': User,
        'selecteditem': 'devis'
    }
    settings = APP_Settings.objects.all().first()
    if requests.method == "GET":
        context['setting'] = settings
        context['selectbody'] = GetClientsListWith_ID()
        context['selectproductbody'] = [product.DESIGNATION for product in list(APP_Products.objects.all())]
        return render(requests, str(settings.APP_lang)+'/CreateNew/Creat-New-Devis.html', context)
    elif requests.method == "POST":
        # Get Post Data
        try :
            datatable = json.loads(requests.POST['datatable'])['myrows']
        except json.decoder.JSONDecodeError :
            pass        
        Devis_number = requests.POST['Devis_number']
        CLIENT_ID = int(requests.POST['client_name'])
        date = requests.POST['date']

        # check if len(datatable)!=0 and all len() rows in that table != 4
        if len(datatable) != 0:
            datatable_status = 'not valid'
            for row in datatable:
                if row['DESIGNATION'] and row['P.T'] and row['P.U'] and row['Qs']:
                    datatable_status = 'valid'
                else:
                    datatable_status = 'not valid'
                    break
        else:
            datatable_status = 'not valid'
        # Check All Required POST Data
        if datatable and Devis_number and CLIENT_ID and CLIENT_ID != '-' and date and datatable_status == 'valid':
            # Check if Devis_number already Exist
            all_Devis_numbers = [n.number for n in All_Deviss]
            if int(Devis_number) in all_Devis_numbers:
                return JsonResponse({'ERR_MSG':f"un Devis avec le même numéro ({Devis_number}) existe déjà"}, status=400)

            if int(Devis_number) not in all_Devis_numbers:
                # Created Devis With POST data if Devis_number not found
                Client = get_object_or_404(APP_Clients,id=CLIENT_ID)
                HT = 0
                Devis = APP_Created_Devis(
                    number=Devis_number,
                    Client=Client,
                    Date=date,
                    CreatedBy=User,
                    HT=HT
                )
                ALL_ITEMS = []
                # Turn Json Table Data into Python Dict
                for data in datatable:
                    # For item in DataTable Create item
                    PT = data[list(data.keys())[3]]
                    HT = HT + float(PT)
                    Items = APP_Devis_items(
                        Qs=data[list(data.keys())[0]],
                        DESIGNATION=data[list(data.keys())[1]],
                        PU=data[list(data.keys())[2]],
                        PT=data[list(data.keys())[3]],
                        BelongToDevis=Devis
                    )
                    ALL_ITEMS.append(Items)
                # Create a History
                actiondetail = f'{User.username} crée un nouvelle Devis avec le numéro {Devis_number} en {Fix_Date(str(datetime.today()))}'
                APP_History.objects.create(
                    CreatedBy=User,
                    action='créer un Devis',
                    action_detail=actiondetail,
                )
                Devis.HT = HT
                Devis.save()
                [it.save() for it in ALL_ITEMS]
                MSG = f"Le Devis {Devis.number} a été crée avec succès"
                return JsonResponse({'MSG':MSG,'ID':Devis.id,'ROOT_URL':'/list-all-devis/'}, status=200)
        else:
            return JsonResponse({'ERR_MSG':"Veuillez remplir toutes les données"}, status=400)


@RequireLogin
def H_Delete_Devis(requests, id):
    context = {'pagetitle': f'Supprimer un Devis'}
    # remove delete/<id> from URL
    redirect_after_done = '/list-all-devis/'
    userid = requests.session['session_id']
    User = get_object_or_404(APP_User, id=userid)
    context['User'] = User
    Devis = get_object_or_404(APP_Created_Devis, id=id)
    context['Devis'] = Devis
    if User.userpermission == 'Admin':
        if requests.method == "POST" and requests.POST['password']:
            password = requests.POST['password']
            if check_password(password, User.password):
                Devis_items = APP_Devis_items.objects.filter(
                    BelongToDevis=Devis)
                Devis_items.delete()
                Devis.delete()
                actionmsg = f'{User.username} Supprimer Le Devis {Devis.number}'
                APP_History.objects.create(
                    CreatedBy=User, action='Supprimer un Devis', action_detail=actionmsg)
                messages.info(requests, "Le Devis a été supprimée avec succès")
                return redirect(redirect_after_done)
            else:
                messages.error(requests, "Oops, Mot de passe incorrect !")
                return redirect(redirect_after_done)
        elif requests.method == "GET":
            return HTTP_404(requests)
    else:
        APP_Warning.objects.create(
            what='supprimer', what_detail=f'{User.username} essayez de supprimer Le Devis avec le nombre {Devis.Devis_number}', Who=User.username)
        return HTTP_403(request=requests, context=context)

@RequireLogin
# Require Login || Admin || author Permission
def H_Edit_Devis(requests, Devis_id):
    # Get Loged User Id from Session_id
    userid = requests.session['session_id']
    User = get_object_or_404(APP_User, id=userid)
    settings = APP_Settings.objects.all().first()
    # Context
    context = {'pagetitle': 'Edité Le Devis',
               'User': User, 'selecteditem': 'list-all-Deviss'}
    # template Path
    templatepath = str(settings.APP_lang)+'/Edit/edit_Devis.html'
    print(templatepath)
    # Get requests Devis by id
    Devis = get_object_or_404(APP_Created_Devis, id=Devis_id)
    # Edit Devis Require Admin Account or The Creator of this Devis
    if User.userpermission == 'Admin' or Devis.CreatedBy.id == userid:
        if requests.method == "GET":
            context['setting'] = settings
            # Pass All Clients name in context to show them in select2
            context['selectbody'] = GetClientsListWith_ID()
            # Pass All Product name in context to show them in select2
            context['selectproductbody'] = [product.DESIGNATION for product in list(APP_Products.objects.all())]
            # Pass the Devis item
            context['Devis'] = Devis
            # Pass the Date of Devis
            context['Date'] = Devis.Date.strftime('%Y-%m-%d')
            # Get All Devis items that belong to that Devis
            Devis_item = APP_Devis_items.objects.filter(BelongToDevis=Devis)
            # generate table of Devis items and pass him in context
            table = generate_table_of_devis_items(Devis_items=Devis_item)
            context['tablebody'] = table
            # pass client name
            context['ClientID'] = Devis.Client.id

            context['len_item'] = len(Devis_item)
            context['TT_INFO'] = Calcule_TVA_TOTAL_TTC(Devis_item)
            return render(requests, templatepath, context)
        elif requests.method == "POST":
            # Get Post Data
            # get datatable and convert it from json to python dict and get data from myrows
            try :
                datatable = json.loads(requests.POST['datatable'])['myrows']
            except json.decoder.JSONDecodeError :
                pass

            Devis_number = requests.POST['Devis_number']
            CLIENT_ID = int(requests.POST['client_name'])
            date = requests.POST['date']
            # check if len(datatable)!=0 and all len() rows in that table != 4
            if len(datatable) != 0:
                datatable_status = 'not valid'
                for row in datatable:
                    if row['DESIGNATION'] and row['P.T'] and row['P.U'] and row['Qs']:
                        datatable_status = 'valid'
                    else:
                        datatable_status = 'not valid'
                        break
            else:
                datatable_status = 'not valid'
            # Check if all required values are in POST
            if datatable and Devis_number and CLIENT_ID and CLIENT_ID != '-' and date and datatable_status == 'valid':
                CLIENT = get_object_or_404(APP_Clients,id=CLIENT_ID)
                Devis.Client = CLIENT
                Devis.Date = date
                actiondetail = f'{User.username} editer un Devis avec le numéro {Devis_number} en {Fix_Date(str(datetime.today()))}'
                APP_History.objects.create(
                    CreatedBy=User,
                    action='editer un Devis',
                    action_detail=actiondetail,
                    DateTime=str(datetime.today())
                )
                APP_Devis_items.objects.filter(BelongToDevis=Devis).delete()
                HT = 0
                ITEMS = []
                for data in datatable:
                    try:
                        PT = data[list(data.keys())[3]]
                        HT = HT + float(PT)
                        theItem = APP_Devis_items(
                            Qs=data[list(data.keys())[0]],
                            DESIGNATION=data[list(data.keys())[1]],
                            PU=data[list(data.keys())[2]],
                            PT=data[list(data.keys())[3]],
                            BelongToDevis=Devis
                        )
                        ITEMS.append(theItem)
                    except Exception as err:
                        pass
                Devis.HT = HT
                Devis.save()
                APP_Devis_items.objects.bulk_create(ITEMS)
                MSG = f"Le Devis {Devis_number} a été éditer avec succès"
                return JsonResponse({'MSG':MSG,'ID':Devis.id,'ROOT_URL':'/list-all-devis/'}, status=200)
            else:
                return JsonResponse({'ERR_MSG':"Veuillez remplir toutes les données"}, status=400)

    else:
        return PermissionErrMsg_and_Warning_Handler(requests, 'Éditer', f'{User.username} essayez de Éditer Le Devis avec le nombre {Devis.Devis_number}', User.username, context, templatepath)

@RequireLogin
# All Deviss Table
def H_List_All_Devis(requests):
    # Get Loged User Id from Session_id
    userid = requests.session['session_id']
    User = get_object_or_404(APP_User, id=userid)
    # context
    context = {'pagetitle': 'Lister Toutes Les Devis',
               'User': User, 'selecteditem': 'list-all-Deviss'}
    if requests.method == "GET":
        settings = APP_Settings.objects.all().first()
        context['setting'] = settings
        # Generate HTML Table and Pass it in context
        Deviss = list(APP_Created_Devis.objects.all())
        tablebody = generate_table_of_devis(devis=Deviss)
        context['tablebody'] = tablebody
        return render(requests, str(settings.APP_lang)+'/List-All-Factures/Created-Devis.html', context)

@RequireLogin
def H_OpenPdf(requests, Devis_id):
    context = {'pagetitle': 'PDF Devis'}
    userid = requests.session['session_id']
    User = get_object_or_404(APP_User, id=userid)
    context['User'] = User
    try:
        Devis = APP_Created_Devis.objects.get(id=Devis_id)
        context['Devis'] = Devis
        if requests.method == "GET":
            settings = APP_Settings.objects.all().first()
            context['setting'] = settings
            Devis_item = APP_Devis_items.objects.filter(BelongToDevis=Devis)
            Company_City = APP_Settings.objects.all().first().Company_Place
            filepath = DrawNotechPdf(Devis, Devis_item, Company_City)
            return FileResponse(open(filepath, 'rb'), content_type='application/pdf')
        else:
            return HTTP_404(requests, context)
    except APP_Created_Devis.DoesNotExist:
        return HTTP_404(requests, context)

@RequireLogin
def H_Devis_To_Facture(requests,Devis_id):
    userid = requests.session['session_id']
    User = get_object_or_404(APP_User, id=userid)
    Devis = get_object_or_404(APP_Created_Devis,id=Devis_id)
    Devis_items = APP_Devis_items.objects.filter(BelongToDevis=Devis)
    isAlreadyConverted = APP_Created_Facture.objects.filter(ConvertedFromDevis=Devis)
    if requests.method == 'GET':
        settings = APP_Settings.objects.all().first()
        if isAlreadyConverted :
            messages.info(requests, f"Ce Devis a été Déjà Convertir à une Facture  avec le nombre {isAlreadyConverted[0].number}")
            return redirect('/list-all-facturs/')
        elif not isAlreadyConverted :
            facturen_nmbr = GetNewNumber(APP_Created_Facture)
            HT = 0
            TVA = 0
            TTC = 0
            # List of item that should saved after facture creation
            ITEMS_NEED_TO_SAVE = []
            facture = APP_Created_Facture(
                        number=facturen_nmbr,
                        Client=Devis.Client,
                        Date=Devis.Date,
                        CreatedBy=User,
                        HT=HT,
                        TVA=TVA,
                        TTC=TTC,
                        ConvertedFromDevis=Devis
                    )
            for item in Devis_items:
                PT = item.PT
                HT = HT + float(PT)
                itm = APP_Facture_items(
                    Qs=item.Qs,
                    PU=item.PU,
                    DESIGNATION=item.DESIGNATION,
                    PT=item.PT,
                    BelongToFacture=facture
                )
                ITEMS_NEED_TO_SAVE.append(itm)
            actiondetail = f'{User.username} convertir le Devis avec le numéro {Devis.number} a une facture avec le numéro {facture.number} en {Fix_Date(str(datetime.today()))}'
            APP_History.objects.create(
                CreatedBy=User,
                action='convertir un Devis',
                action_detail=actiondetail,
                DateTime=str(datetime.today())
            )
            settings = APP_Settings.objects.all().first()
            TVA = HT / 100 * float(settings.Company_TVATAUX)
            TTC = HT + TVA
            facture.HT = HT
            facture.TVA = TVA
            facture.TTC = TTC
            facture.save()
            [it.save() for it in ITEMS_NEED_TO_SAVE]
            messages.info(requests, f"ce devis a été converti en facture:{facture.number}  avec succès")
            return redirect('/list-all-facturs/')
    else:
        return HTTP_404(requests)
