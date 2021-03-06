# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

# -------------------------------------------------------------------------
# This is a sample controller
# - index is the default action of any application
# - user is required for authentication and authorization
# - download is for downloading files uploaded in the db (does streaming)
# -------------------------------------------------------------------------
import os
import datetime
import re
from usbutils import get_ldap_data, random_key
from funciones_siradex import get_tipo_usuario,get_tipo_usuario_not_loged
from log import insertar_log
import urllib2
from notificaciones import *
# import pygal
# from pygal.style import Style

### required - do no delete
def user(): return dict(form=auth())
def download(): return response.download(request,db)
def call(): return service()
### end requires

# URLS DE RETORNO PARA EL CAS ##
# PARA EL SERVIDOR:
URL_RETORNO = "http%3A%2F%2Fsiradex.dex.usb.ve%2Fdefault%2Flogin_cas"
# PARA DESSARROLLO. Cambiar el puerto 8000 si es necesario.
# URL_RETORNO = "http%3A%2F%2Flocalhost%3A8000%2FSiraDex%2Fdefault%2Flogin_cas"

# FUNCIONES USUARIO
def login_cas():
    if not request.vars.getfirst('ticket'):
        #redirect(URL('error'))
        pass
    try:
        import urllib2, ssl
        ssl._create_default_https_context = ssl._create_unverified_context

        url = "https://secure.dst.usb.ve/validate?ticket="+\
        request.vars.getfirst('ticket') +\
        "&service=" + URL_RETORNO

        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        the_page = response.read()

    except Exception, e:
        print "Exception: "
        print e
        # redirect(URL('error'))

    if the_page[0:2] == "no":
        pass
    else:
        # session.casticket = request.vars.getfirst('ticket')
        data  = the_page.split()
        usbid = data[1]

        usuario = get_ldap_data(usbid) #Se leen los datos del CAS

        tablaUsuarios = db.USUARIO

        session.usuario = usuario
        session.usuario['usbid'] = usbid
        if not db(tablaUsuarios.usbid == usbid).isempty():
            datosUsuario = db(tablaUsuarios.usbid==usbid).select()[0]
            session.usuario['tipo'] = datosUsuario.tipo
            session.usuario['alternativo'] = datosUsuario.correo_alter

            session.usuario['phone'] = datosUsuario.telefono


            if datosUsuario.tipo == "Bloqueado":
                insertar_log(db, 'LOGIN', datetime.datetime.now(), request.client, 'LOGIN USUARIO BLOQUEADO', usbid)
                response.flash = T("Usuario bloqueado")
                redirect(URL(c = "default",f="logout_cas"))
            else:
                insertar_log(db, 'LOGIN', datetime.datetime.now(), request.client, 'LOGIN SATISFACTORIO', usbid)
                redirect(URL('perfil'))
        else:

            session.usuario['tipo'] = "Usuario"
            session.usuario['alternativo'] = None
           # Para el envio de notificacion
            datos_usuario = {'nombres' : session.usuario['first_name'] + ' ' + session.usuario['last_name']}
            datos_usuario['email'] = session.usuario['email']

            if session.usuario["phone"]:
                telefono = session.usuario["phone"]
            else:
                telefono = ""

            db.USUARIO.insert(ci=session.usuario["cedula"],  # Lo insertamos en la base de datos.
            usbid=session.usuario["usbid"],
            nombres=session.usuario["first_name"],
            apellidos=session.usuario["last_name"],
            correo_inst=session.usuario["email"],
            correo_alter= "",
            telefono=telefono,
            tipo = "Usuario")

            insertar_log(db, 'REGISTRO', datetime.datetime.now(), request.client, 'REGISTRO SATISFACTORIO', usbid)

            # Se envia correo de bienvenida al usuario
            enviar_correo_bienvenida(mail,datos_usuario)

            insertar_log(db, 'LOGIN', datetime.datetime.now(), request.client, 'LOGIN SATISFACTORIO', usbid)
            redirect(URL('perfil'))

def logout_cas():
    insertar_log(db, 'LOGOUT', datetime.datetime.now(), request.client, 'LOGOUT SATISFACTORIO', session.usuario['usbid'])
    session.usuario = None
    return response.render()

def grafica_pie():

    query = "select  programa.id_programa, programa.nombre, programa.abreviacion, count(producto.nombre)" + \
    " from ((programa inner join tipo_actividad on programa.id_programa=tipo_actividad.id_programa)" + \
    " inner join producto on producto.id_tipo=tipo_actividad.id_tipo and producto.usbid_usu_creador=\'"+ session.usuario["usbid"] +\
    "\' and producto.estado=\'Validado\') group by programa.id_programa, programa.nombre, programa.abreviacion;"

    query2 = "select count(producto.nombre) from producto where producto.usbid_usu_creador=\'"+ session.usuario["usbid"]+"\' and producto.estado=\'Validado\';"

    datos = db.executesql(query)
    num_productos = db.executesql(query2)[0][0]

    programas={}

    for producto in datos:
        id_programa = producto[0]
        try:
            programas[id_programa]['repeticiones'] += 1
        except:
            nombre = producto[1]
            abrev = producto[2]
            programas[id_programa] = {'id':id_programa,'nombre':nombre,'abreviacion':abrev,'repeticiones':1}


    # for producto in datos:
    #     porcentaje = (producto[2]*100)//num_productos
    #     pie_chart.add(producto[1],[{'value':porcentaje, 'label':producto[0]}])

    return programas

def perfil():
    if session.usuario != None:
        print "El admin es:"
        admin = get_tipo_usuario(session)
        print admin

        correo_i = session.usuario["usbid"]+"@usb.ve"
        alternativo = session.usuario["alternativo"] if session.usuario["alternativo"]!=None else ''
        telefono = session.usuario["phone"] if session.usuario["phone"]!=None else ''

        if session.usuario['alternativo']==None:
            print("None")
        else:
            print("no es None")
        form = SQLFORM.factory(
            Field("USBID", default=session.usuario["usbid"],writable = False),
            Field('Nombres',default=session.usuario["first_name"],writable = False),
            Field('Apellidos', default=session.usuario["last_name"],writable=False),
            Field('Correo_Institucional', default=correo_i,writable=False),
            Field('Telefono',label = "Teléfono", default=telefono ,writable=False),
            Field('Correo_Alternativo', default=alternativo ,writable=False),
            readonly=True)

        # Productos Registrados por el Usuario
        rows = db(db.PRODUCTO.usbid_usu_creador==session.usuario['usbid']).select()

        # Productos del usuario, registrados por otros usuarios
        otrosProductos = db(db.PARTICIPA_PRODUCTO.usbid_usuario == session.usuario['usbid']).select()
        for prod in otrosProductos:
            prodAux = db(db.PRODUCTO.id_producto == prod.id_producto).select()
            rows = rows & prodAux #unimos el producto a las filas que ya existian

        productos = {
                    "Validados":[],
                    "No Validados":[],
                    "Por Validar":[]
                    }

        infoPieChart = grafica_pie()
        tabla = URL('default','tabla')

        nombres = {}
        for row in rows:
            nombres_act = db((db.PRODUCTO.id_tipo == db.TIPO_ACTIVIDAD.id_tipo)
                        & (db.PRODUCTO.id_producto == row.id_producto)).select()

            for nombre in nombres_act:
                nombres[row] = nombre.TIPO_ACTIVIDAD.nombre

        for row in rows:
            if row.estado == "Validado":
                productos["Validados"] += [row]
            elif row.estado == "No Validado":
                productos["No Validados"]+= [row]
            else:
                productos["Por Validar"] += [row]

        return locals()
    else:
        redirect(URL("index"))

def tabla():
    fecha_hasta = datetime.date.today().year
    fecha_desde = fecha_hasta - 10
    query = "select p.id_programa, count(p.id_programa), extract(year from prod.fecha_realizacion) as yy" + \
        " from ((programa as p inner join tipo_actividad as a on p.id_programa=a.id_programa)" + \
        " inner join producto as prod on prod.id_tipo=a.id_tipo and prod.usbid_usu_creador=\'"+ session.usuario["usbid"] +\
        "\' and prod.estado=\'Validado\') group by p.id_programa, extract(year from prod.fecha_realizacion);"


    productos = db.executesql(query)

    #programas = db(db.PROGRAMA['papelera']==False).select().as_list()
    programas = db(db.PROGRAMA).select().as_list()

    programas_dict = {}
    for programa in programas:
        ident = programa['id_programa']
        nombre = programa['nombre']
        abrev = programa['abreviacion']
        programas_dict[ident] = {'nombre':nombre, 'abreviacion':abrev, 'repeticiones':[0 for x in range(11)]}

    for producto in productos:
        identificador = producto[0]
        anio = int(producto[2])
        index = anio-fecha_desde
        if (index <= 0):
            index=0
        programas_dict[identificador]['repeticiones'][index]+= producto[1]


    line_chart = pygal.Bar()
    line_chart.x_labels = map(str, range(fecha_desde, fecha_hasta + 1))

    for key in programas_dict:
        line_chart.add(programas_dict[key]['abreviacion'],programas_dict[key]['repeticiones'])

    return line_chart.render_table(transpose=True,style=True)

def EditarPerfil():
    if session.usuario != None:
        admin = get_tipo_usuario(session)

        form = SQLFORM.factory(
            Field("USBID", default=session.usuario["usbid"],writable = False),
            Field('Nombres',default=session.usuario["first_name"],writable = False),
            Field('Apellidos', default=session.usuario["last_name"],writable=False),
            readonly=True)


        # Modificar datos del perfil
        usuario = db(db.USUARIO.ci==session.usuario['cedula']).select().first()
        print usuario
        alternativo = session.usuario["alternativo"] if session.usuario["alternativo"]!=None else ''
        telefono = session.usuario["phone"] if session.usuario["phone"]!=None else ''


        forma=SQLFORM.factory(
            Field('telefono',
                   requires=[IS_LENGTH(20),
                             IS_MATCH('^\(0[0-9]{3}\)[0-9]{3}-[0-9]{4}$|^$', error_message="Formato inválido")]),
            Field('correo_alter',
                   requires=[IS_MATCH('^[.A-z0-9À-ÿŸ\s-]+@[.A-z0-9À-ÿŸ\s-]+$|^$', error_message="Formato inválido")]),
            submit_button='Agregar',
            labels={'telefono':'Teléfono', 'correo_alter':'Correo alternativo'},
            col3={'telefono':'Ej: (0212)123-1234','correo_alter':'Ej: ejemplo@gmail.com'}
            )

        forma.element(_type='submit')['_class']="btn blue-add btn-block btn-border"
        forma.element(_type='submit')['_value']="Actualizar"


        if forma.accepts(request.vars, session,formname="forma"):
            nuevoTelefono = request.vars.telefono
            nuevoCorreoAlter = request.vars.correo_alter

            valor_telefono = "" if (nuevoTelefono== None) else nuevoTelefono
            session.usuario["phone"] = valor_telefono

            valor_correo = "" if (nuevoCorreoAlter== None) else nuevoCorreoAlter
            session.usuario["alternativo"] = valor_correo

            db(db.USUARIO.ci == session.usuario["cedula"]).update(telefono=valor_telefono, correo_alter=valor_correo)

            insertar_log(db, 'PERFIL', datetime.datetime.now(), request.client, 'ACT. PERFIL SATISFACTORIA', session.usuario['usbid'])
            redirect(URL('perfil'))
        else :
            message = T("Debe colocar su teléfono y correo alternativo.")


        return dict(form1 = form, form = forma, admin = admin, telefono=telefono, alternativo=alternativo)
    else:
        redirect(URL("index"))

#  FUNCIONES GESTIONAR USUARIO
def index():
    admin = get_tipo_usuario_not_loged(session)

    now = datetime.datetime.now()
    if now.month < 10 :
        mes = "-0" +  str(now.month)
    else:
        mes = "-" +  str(now.month)
    if now.day < 10 :
        dia = "-0" +  str(now.day)
    else:
        dia = "-" +  str(now.month)
    fecha = str(now.year) + mes + dia
    programas = db(db.PROGRAMA.papelera == False).select().as_list()
    actividades = db(db.TIPO_ACTIVIDAD.papelera == False).select().as_list()
    usuarios = db(db.USUARIO.tipo!='Bloqueado').select().as_list()
    return locals()

def obtener_actividades():
    if request.vars.Programa=="all":
        tiposA = db(db.TIPO_ACTIVIDAD.papelera == False).select()
    else:
        tiposA = db(db.TIPO_ACTIVIDAD.id_programa==int(request.vars.Programa)).select()


    concat = '<option value="all" selected="">--cualquiera--</option>'

    for tipo in tiposA:
        if (tipo.papelera==False):
                option = tipo.nombre
                if len(option)>88:
                    option = option[0:88]+"..."
                concat += '<option value="'+str(tipo.id_tipo)+'">'+option+'</option>'

    return "jQuery('#lista_tipos').empty().append('"+concat+"')"

##########################################################################################################
####################################### REVISAR SI SE PUEDEN BORRAR ######################################
##########################################################################################################

def vMenuAdmin():
    if session.usuario != None:
        if session.usuario["tipo"] == "Bloqueado":
            redirect(URL("index"))
        if session.usuario["tipo"] == "Administrador":
            session.message = ""
            return response.render(admin = get_tipo_usuario(session))
        else:
            redirect(URL("perfil"))
    else:
        redirect(URL("index"))

def vMenuDex():
    if session.usuario != None:
        if session.usuario["tipo"] == "Bloqueado":
            redirect(URL("index"))
        if session.usuario["tipo"] == "DEX" or session.usuario["tipo"] == "Administrador":
            admin = 4
            if(session.usuario["tipo"] == "DEX"):
                admin = 2
            elif(session.usuario["tipo"] == "Administrador"):
                admin = 1
            else:
                admin = 0
            return dict(admin = admin)
        else:
            redirect(URL("perfil"))
    else:
        redirect(URL("index"))

# Controlador para el registro del usuario
def vRegistroUsuario():
    if session.usuario != None:
        # Se usa un formulario que muestre los datos no modificables.
        form = SQLFORM.factory(
            Field("USBID", default=session.usuario["usbid"],writable = False),
            Field('Nombres',default=session.usuario["first_name"],writable = False),
            Field('Apellidos', default=session.usuario["last_name"],writable=False),
            readonly=True)

        #Realiza las modificaciones sobre la base de datos en funcion de lo que introduzca el usuario.
        usuarios = db(db.USUARIO).select()
        for raw in usuarios:
            if raw.ci == session.usuario["cedula"]:
                forma=SQLFORM(
                    db.USUARIO,
                    raw,
                    button=['Registrarse'],
                    fields=['telefono','correo_alter'],
                    submit_button='Registrarse',
                    labels={'telefono':'Teléfono', 'correo_alter':'Correo alternativo'})
                break
        if len(request.vars)!=0:
            nuevoTelefono = request.vars.telefono
            nuevoCorreoAlter = request.vars.correo_alter
            db(db.USUARIO.ci == session.usuario["cedula"]).update(telefono=nuevoTelefono, correo_alter=nuevoCorreoAlter)
            redirect(URL('perfil'))        # Redirige al usuario al menu principal.
        return dict(form1 = form, form = forma, admin=get_tipo_usuario(session))
    else:
        redirect(URL("index"))
