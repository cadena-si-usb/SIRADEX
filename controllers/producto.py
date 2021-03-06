# -*- coding: utf-8 -*-
# try something like

import datetime
import os
import shutil
#import contenttype as c
import os.path
from pprint    import pprint
from datetime  import time
from uuid      import uuid4
from reportlab.platypus   import *
from reportlab.lib.units  import *
from reportlab.lib        import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums  import *
from funciones_siradex import get_tipo_usuario
from log import insertar_log


def gestionar():
    session.message=""
    admin = get_tipo_usuario(session)

    # Productos registrados por el usuario.
    rows = db(db.PRODUCTO.usbid_usu_creador == session.usuario['usbid']).select()

    # Productos del usuario, registrados por otros usuarios
    otrosProductos = db(db.PARTICIPA_PRODUCTO.usbid_usuario == session.usuario['usbid']).select()
    for prod in otrosProductos:
        prodAux = db(db.PRODUCTO.id_producto == prod.id_producto).select()
        rows = rows & prodAux #unimos el producto a las filas que ya existian

    detalles = {}
    nombres = {}
    cant_esp = 0
    cant_val = 0
    cant_rec = 0
    cant_bor = 0

    for row in rows:
        dict_campos  = dict()
        dict_nombres = dict()

        campos = db((db.PRODUCTO_TIENE_CAMPO.id_campo == db.CAMPO.id_campo)
                    & (db.PRODUCTO_TIENE_CAMPO.id_prod == row.id_producto)).select()

        for campo in campos:
            dict_campos[campo.CAMPO.nombre] = campo.PRODUCTO_TIENE_CAMPO.valor_campo

        detalles[row] = dict_campos

        nombres_act = db((db.PRODUCTO.id_tipo == db.TIPO_ACTIVIDAD.id_tipo)
                    & (db.PRODUCTO.id_producto == row.id_producto)).select()

        for nombre in nombres_act:
            nombres[row] = nombre.TIPO_ACTIVIDAD.nombre

        if row["estado"] == "Por Validar":
            cant_esp += 1
        elif row["estado"] == "Validado":
            cant_val += 1
        # solo los creadores pueden ver los no validados
        elif row["estado"] == "No Validado" and row['usbid_usu_creador'] == session.usuario['usbid']:
            cant_rec += 1
        # solo los creadores pueden ver los borrdores
        elif row["estado"] == "Borrador" and row['usbid_usu_creador'] == session.usuario['usbid'] :
            cant_bor += 1

    # Para el modal de Agregar Producto
    programas = db(db.PROGRAMA.papelera==False).select('nombre')
    formulario = SQLFORM.factory(
        Field('programa', requires=IS_NOT_EMPTY()),
        Field('id_tipo',  requires=IS_NOT_EMPTY()))
    if formulario.process(session=None, formname='crear_tipo').accepted:
        redirect(URL(agregar,args=[formulario.vars.id_tipo]))
    elif formulario.errors:
        response.flash = 'el formulario tiene errores'

    return locals()

def tipos():
    rows = db(db.TIPO_ACTIVIDAD.papelera==False).select()
    return locals()

def agregar():

    admin = get_tipo_usuario(session)

    # Para la fecha maxima de realizacion
    now = datetime.datetime.now()
    if now.month < 10 :
        mes = "-0" +  str(now.month)
    else:
        mes = "-" +  str(now.month)
    if now.day < 10 :
        dia = "-0" +  str(now.day)
    else:
        dia = "-" +  str(now.month)
    fecha_max = str(now.year) + mes + dia

    if not request.args:
        raise HTTP(404)
    tipo =  int(request.args(0))

    campos_id = db(db.ACT_POSEE_CAMPO.id_tipo_act == tipo).select()
    tipo_actividad = db(db.TIPO_ACTIVIDAD.id_tipo == tipo).select().first()

    nombre_actividad = tipo_actividad.nombre
    descripcion_actividad = tipo_actividad.descripcion

    fields = []

    # Otros Autores de la Actividad
    lista_usuarios = db(db.USUARIO.tipo == 'Usuario').select()
    usuarios = {}

    # Se crea un diccionario para almacenar unicamente los nombres de los usuarios
    for usuario in lista_usuarios:
        if usuario.usbid != session.usuario['usbid']:
            usuarios[usuario.usbid] = usuario.nombres + ' ' + usuario.apellidos

    for i in range(5):
        fields.append(Field("autor_"+str(i+1),
                            label = 'Autor ',
                            requires = IS_EMPTY_OR(IS_IN_SET(usuarios, zero="Seleccione usuario",
                                                                       error_message = 'Debes elegir uno de los usuarios listados.'))))

    obl = {}
    no_obl = {}
    for row in campos_id:
        rows_campo = db(db.CAMPO.id_campo == row.id_campo).select().first()
        nombre = rows_campo.nombre_interno.replace(" ", "_")
        try :
            if int(nombre[0]):
                nombre = "c4mp0_"+nombre
        except:
            pass

        print(nombre)

        obligatorio = rows_campo.obligatorio
        tipo_campo = rows_campo.tipo_campo.replace(" ", "_")

        if obligatorio:
            obl[nombre]= tipo_campo
            if tipo_campo in   ['Fecha']:             fields.append(Field(nombre,'date', label=rows_campo.nombre+"  (**)",requires=[IS_NOT_EMPTY(),IS_DATE(format=T('%Y-%m-%d'),error_message='Fecha inválida, debe ser: AAA-MM-DD')]))
            elif tipo_campo in ['Texto_Corto']:       fields.append(Field(nombre,'string',label=rows_campo.nombre+" (*)",requires=[IS_NOT_EMPTY(error_message='Inserte texto')]))
            elif tipo_campo in ['Cedula']:            fields.append(Field(nombre,'string',label=rows_campo.nombre +" (*)",requires=[IS_NOT_EMPTY(),IS_MATCH('\d{2}.\d{3}.\d{3}$', error_message='CI inválida, debe ser: XX.XXX.XXX')]))
            elif tipo_campo in ['Documento']:         fields.append(Field(nombre,'upload',label=rows_campo.nombre+" (*)",uploadfolder=os.path.join(request.folder,'uploads') ,requires=[IS_NOT_EMPTY(error_message='Debe subirse un archivo')]))
            elif tipo_campo in ['Telefono']:          fields.append(Field(nombre,'string',label=rows_campo.nombre+" (*)",requires=[IS_NOT_EMPTY(),IS_MATCH('\(0\d{3}\)\d{3}-\d{4}$', error_message='Teléfeno invélido, debe ser: (0xxx)xxx-xxxx')]))
            elif tipo_campo in ['Cantidad_Entera']:   fields.append(Field(nombre,'string',label=rows_campo.nombre+" (*)",requires=[IS_NOT_EMPTY(),IS_INT_IN_RANGE(-9223372036854775800, 9223372036854775807)]))
            elif tipo_campo in ['Cantidad_Decimal']:  fields.append(Field(nombre,'string',label=rows_campo.nombre+" (*)",requires=[IS_NOT_EMPTY(),IS_DECIMAL_IN_RANGE(-9223372036854775800, 9223372036854775807, dot=".",error_message='El numero debe ser de la forma X.X, donde X esta entre -9223372036854775800 y 9223372036854775807')]))
            elif tipo_campo in ['Texto_Largo']:       fields.append(Field(nombre,'text',label=rows_campo.nombre+" (*)",requires=IS_NOT_EMPTY()))


        else:
            no_obl[nombre] = tipo_campo
            if tipo_campo in   ['Fecha']:             fields.append(Field(nombre,'date',label=rows_campo.nombre,requires=IS_EMPTY_OR(IS_DATE(format=T('%Y-%m-%d'),error_message='Fecha inválida, debe ser: AAA-MM-DD'))))
            elif tipo_campo in ['Texto_Corto']:       fields.append(Field(nombre,'string',label=rows_campo.nombre))
            elif tipo_campo in ['Cedula']:            fields.append(Field(nombre,'string',label=rows_campo.nombre,requires=IS_EMPTY_OR(IS_MATCH('\d{2}.\d{3}.\d{3}$', error_message='CI inválida, debe ser: XX.XXX.XXX'))))
            elif tipo_campo in ['Documento']:         fields.append(Field(nombre,'upload',label=rows_campo.nombre,requires=IS_EMPTY_OR(IS_UPLOAD_FILENAME()),uploadfolder=os.path.join(request.folder,'uploads')))
            elif tipo_campo in ['Telefono']:          fields.append(Field(nombre,'string',label=rows_campo.nombre,requires=IS_EMPTY_OR(IS_MATCH('\(0\d{3}\)\d{3}-\d{4}$', error_message='Teléfeno inválido, debe ser: (0xxx)xxx-xxxx'))))
            elif tipo_campo in ['Cantidad_Entera']:   fields.append(Field(nombre,'string',label=rows_campo.nombre,requires=IS_EMPTY_OR(IS_INT_IN_RANGE(-9223372036854775800, 9223372036854775807))))
            elif tipo_campo in ['Cantidad_Decimal']:  fields.append(Field(nombre,'string',label=rows_campo.nombre,requires=IS_EMPTY_OR(IS_DECIMAL_IN_RANGE(-9223372036854775800, 9223372036854775807, dot=".",error_message='El número debe ser de la forma X.X, donde X esta entre -9223372036854775800 y 9223372036854775807'))))
            elif tipo_campo in ['Texto_Largo']:       fields.append(Field(nombre,'text',label=rows_campo.nombre))


    for i in range(5):
        fields.append(Field("c0mpr0bant3_"+str(i+1), 'upload', autodelete=True, uploadseparate=True, uploadfolder=os.path.join(request.folder,'uploads'), label=''))
        fields.append(Field("d3scr1pc10n_comprobante_"+str(i+1), 'string', label="Descripción (*)"))


    #fields.append(Field(nombre,requires=IS_IN_SET([(1,'Method1'), (2,'Method2'), (3,'Method3')], zero='Select')))
    url = URL('download')



    form=SQLFORM.factory(*fields, upload=url, buttons = [INPUT(_value='Guardar como Borrador',_type="submit", _class="btn blue-add btn-block btn-border ", _name="borrador"),
                                                         INPUT(_value='Enviar Producto',_type="submit", _class="btn blue-add btn-block btn-border ")])
    form.element()

    #fix para el datepicker de las fechas:
    for i in obl.keys():
        form.element(_name=i)['_class']= form.element(_name=i)['_class'] + " obligatoria "+ obl[i]

    for i in no_obl.keys():
        form.element(_name=i)['_class']= form.element(_name=i)['_class'] + ' ' + no_obl[i]

    if form.process().accepted:
        no = ['nombre','descripcion','fecha_realizacion','lugar','colaboradores']

        estado = "Por Validar"
        if request.vars.borrador:
            #Verificamos si se quiere es un borrador.
            estado = "Borrador"
        dicc_producto = db.PRODUCTO.insert(id_tipo = tipo,nombre=form.vars.nombre, descripcion=form.vars.descripcion,\
                                      estado= estado, fecha_realizacion=form.vars.fecha_realizacion, fecha_modificacion=now, \
                                      lugar = form.vars.lugar,colaboradores=form.vars.colaboradores,
                                      usbid_usu_creador= session.usuario['usbid'])
        id_producto = dicc_producto['id_producto']

        if request.vars.borrador:
            insertar_log(db, 'PRODUCTO', datetime.datetime.now(), request.client, 'NUEVO BORRADOR CON ID ' + str(id_producto), session.usuario['usbid'])
        else:
            insertar_log(db, 'PRODUCTO', datetime.datetime.now(), request.client, 'NUEVO PRODUCTO CON ID ' + str(id_producto), session.usuario['usbid'])

        for var in form.vars:
            if not(var in no):
                #Buscamos los autores
                try:
                    if (var[0:5]=="autor"):
                        usbid_autor = getattr(form.vars, var)
                        if usbid_autor != None:
                            db.PARTICIPA_PRODUCTO.insert(id_producto = id_producto, usbid_usuario =  usbid_autor)
                except Exception, e:
                    print "Exception Autor: "
                    print e

                try:
                    if (var[0:11]=="c0mpr0bant3"):
                        numero_comprobante = var[12:13]
                        descripcion = getattr(form.vars ,'d3scr1pc10n_comprobante_'+ numero_comprobante)
                        nombre = getattr(form.vars ,var)
                        if nombre!='':
                            db.COMPROBANTE.insert(archivo=nombre,descripcion=descripcion,producto=id_producto)
                        continue


                    elif (var[0:11]=="d3scr1pc10n"):
                        continue

                except Exception, e:
                    print "Exception: "
                    print e

                try:
                    if (var[0:6]=="c4mp0_"):
                        campo = var[6:]
                    else:
                        campo = var
                except Exception, e:
                    print "Exception: "
                    print e
                    campo = var

                #Ignora campos de autor
                if campo[0:5] != 'autor' and campo[0:8] != 'borrador':
                    print campo
                    campo = campo.replace("_"," ")
                    id_camp = db(db.CAMPO.nombre_interno==campo).select().first().id_campo
                    valor = getattr(form.vars ,var)
                    db.PRODUCTO_TIENE_CAMPO.insert(id_prod=id_producto,id_campo=id_camp,valor_campo= valor)

        redirect(URL('gestionar'))
    elif form.errors:
        response.flash = 'el formulario tiene errores'


    return locals()

def modificar():
    admin = get_tipo_usuario(session)

    if not request.args:
        raise HTTP(404)
    id_producto = int(request.args(0))

    now = datetime.datetime.now()
    if now.month < 10 :
        mes = "-0" +  str(now.month)
    else:
        mes = "-" +  str(now.month)
    if now.day < 10 :
        dia = "-0" +  str(now.day)
    else:
        dia = "-" +  str(now.month)
    fecha_max = str(now.year) + mes + dia

    # Obtenemos los productos para mostrarlos en el html
    producto = db(db.PRODUCTO.id_producto==id_producto).select().first()

    # Si el producto no existe
    if not producto :
        redirect(URL('gestionar'))
        # Si no soy el creador del producto
    elif producto["usbid_usu_creador"] != session.usuario["usbid"] :
        redirect(URL('gestionar'))

    query = "SELECT id_comprobante, descripcion FROM COMPROBANTE WHERE producto="+str(id_producto)+";"
    comprobantes = db.executesql(query)

    temp= "SELECT id_comprobante, descripcion FROM COMPROBANTE WHERE producto="+str(id_producto)+"AND ;"
    tipo_actividad = db(db.TIPO_ACTIVIDAD.id_tipo == producto.id_tipo).select().first()

    nombre_actividad = tipo_actividad.nombre
    descripcion_actividad = tipo_actividad.descripcion

    # Creamos el formulario
    rows = db(db.PRODUCTO_TIENE_CAMPO.id_prod == id_producto).select()
    fields = []

    obl = {}
    no_obl = {}

    valores = {}
    valores['nombre'] = producto.nombre
    valores['descripcion'] = producto.descripcion
    valores['fecha_realizacion'] = producto.fecha_realizacion
    valores['lugar'] = producto.lugar
    valores['colaboradores'] = producto.colaboradores
    documentos=[]

    # Otros Autores de la Actividad
    lista_usuarios = db(db.USUARIO.tipo == 'Usuario').select()
    usuarios = {}

    # Se crea un diccionario para almacenar unicamente los nombres de los usuarios
    for usuario in lista_usuarios:
        if usuario.usbid != session.usuario['usbid']:
            usuarios[usuario.usbid] = usuario.nombres + ' ' + usuario.apellidos

    for i in range(5):
        fields.append(Field("autor_"+str(i+1),
                            label = 'Autor ',
                            requires = IS_EMPTY_OR(IS_IN_SET(usuarios, zero="Seleccione usuario", error_message = 'Debes elegir uno de los usuarios listados.'))))



    #Obtenemos los valores de los otros autores, si exiten
    otros_autores = db(db.PARTICIPA_PRODUCTO.id_producto == producto.id_producto).select()
    num_aut = 0
    for autor in otros_autores:
        autorAux = db(db.USUARIO.usbid == autor.usbid_usuario).select().first()
        valores['autor_' + str(num_aut + 1)] = autorAux.usbid
        num_aut += 1

    # Los tipos documento tienen que ser tratados diferente y cargados los enlaces con js
    hay_uploads = False
    for row in rows:
        rows_campo = db(db.CAMPO.id_campo == row.id_campo).select().first()
        nombre = rows_campo.nombre_interno.replace(" ", "_")
        try :
            if int(nombre[0]):
                nombre = "campo_"+nombre
        except:
            pass
        obligatorio = rows_campo.obligatorio
        tipo_campo = rows_campo.tipo_campo

        if obligatorio:
            obl[nombre.replace(" ", "_")]= tipo_campo
            if tipo_campo in   ['Fecha']:             fields.append(Field(nombre,'date',label=rows_campo.nombre+" (*)",requires=[IS_NOT_EMPTY(),IS_DATE(format=T('%Y-%m-%d'),error_message='Fecha inválida, debe ser: AAA-MM-DD')]))
            elif tipo_campo in ['Texto Corto']:       fields.append(Field(nombre,'string',label=rows_campo.nombre+" (*)",requires=[IS_NOT_EMPTY(error_message='Inserte texto')]))
            elif tipo_campo in ['Cedula']:            fields.append(Field(nombre,'string',label=rows_campo.nombre+" (*)",requires=[IS_NOT_EMPTY(),IS_MATCH('\d{2}.\d{3}.\d{3}$', error_message='CI inválida, debe ser: XX.XXX.XXX')]))
            elif tipo_campo in ['Documento']:
                if(row.valor_campo!=''):
                    temp= [str(rows_campo.id_campo),str(row.id_prod), rows_campo.nombre+" (*)", nombre]
                    documentos+= [temp]
                fields.append(Field(nombre,'upload',label=rows_campo.nombre+" (*)",uploadfolder=os.path.join(request.folder,'uploads'),requires=[IS_NOT_EMPTY(error_message='Debe subirse un archivo')]))
            elif tipo_campo in ['Telefono']:          fields.append(Field(nombre,'string',label=rows_campo.nombre+" (*)",requires=[IS_NOT_EMPTY(),IS_MATCH('\(0\d{3}\)\d{3}-\d{4}$', error_message='Teléfeno inválido, debe ser: (0xxx)xxx-xxxx')]))
            elif tipo_campo in ['Cantidad Entera']:   fields.append(Field(nombre,'string',label=rows_campo.nombre+" (*)",requires=[IS_NOT_EMPTY(),IS_INT_IN_RANGE(-9223372036854775800, 9223372036854775807)]))
            elif tipo_campo in ['Cantidad Decimal']:  fields.append(Field(nombre,'string',label=rows_campo.nombre+" (*)",requires=[IS_NOT_EMPTY(),IS_DECIMAL_IN_RANGE(-9223372036854775800, 9223372036854775807, dot=".",error_message='El número debe ser de la forma X.X, donde X está entre -9223372036854775800 y 9223372036854775807')]))
            elif tipo_campo in ['Texto Largo']:       fields.append(Field(nombre,'text',label=rows_campo.nombre+" (*)",requires=IS_NOT_EMPTY()))

        else:
            no_obl[nombre.replace(" ", "_")] = tipo_campo
            if tipo_campo in   ['Fecha']:             fields.append(Field(nombre,'date',label=rows_campo.nombre,requires=IS_EMPTY_OR(IS_DATE(format=T('%Y-%m-%d'),error_message='Fecha inválida, debe ser: AAA-MM-DD'))))
            elif tipo_campo in ['Texto Corto']:       fields.append(Field(nombre,'string',label=rows_campo.nombre))
            elif tipo_campo in ['Cedula']:            fields.append(Field(nombre,'string',label=rows_campo.nombre,requires=IS_EMPTY_OR(IS_MATCH('\d{2}.\d{3}.\d{3}$', error_message='CI inválida, debe ser: XX.XXX.XXX'))))
            elif tipo_campo in ['Documento']:
                if(row.valor_campo!=''):
                    temp= [str(rows_campo.id_campo),row.id_prod, rows_campo.nombre, nombre]
                    documentos+= [temp]
                fields.append(Field(nombre,'upload',label=rows_campo.nombre,requires=IS_EMPTY_OR(IS_UPLOAD_FILENAME()),uploadfolder=os.path.join(request.folder,'uploads')))
            elif tipo_campo in ['Telefono']:          fields.append(Field(nombre,'string',label=rows_campo.nombre,requires=IS_EMPTY_OR(IS_MATCH('\(0\d{3}\)\d{3}-\d{4}$', error_message='Teléfeno inválido, debe ser: (0xxx)xxx-xxxx'))))
            elif tipo_campo in ['Cantidad Entera']:   fields.append(Field(nombre,'string',label=rows_campo.nombre,requires=IS_EMPTY_OR(IS_INT_IN_RANGE(-9223372036854775800, 9223372036854775807))))
            elif tipo_campo in ['Cantidad Decimal']:  fields.append(Field(nombre,'string',label=rows_campo.nombre,requires=IS_EMPTY_OR(IS_DECIMAL_IN_RANGE(-9223372036854775800, 9223372036854775807, dot=".",error_message='El número debe ser de la forma X.X, donde X está entre -9223372036854775800 y 9223372036854775807'))))
            elif tipo_campo in ['Texto Largo']:       fields.append(Field(nombre,'text',label=rows_campo.nombre))


        valores[nombre]=row.valor_campo
    print documentos
    for i in range(5):
        fields.append(Field("c0mpr0bant3_"+str(i+1), 'upload', autodelete=True, uploadseparate=True, uploadfolder=os.path.join(request.folder,'uploads'), label=''))
        fields.append(Field("d3scr1pc10n_comprobante_"+str(i+1), 'string', label="Descripción"))

    form=SQLFORM.factory(*fields, upload=URL('download'), buttons = [INPUT(_value='Guardar como Borrador',_type="submit", _class="btn blue-add btn-block btn-border ", _name="borrador"),
                                                         INPUT(_value='Enviar Producto',_type="submit", _class="btn blue-add btn-block btn-border ")])
    form.element()

    # Le escribimos la informacion a las vistas
    for nombre_campo in valores.keys():
        setattr(form.vars, nombre_campo, valores[nombre_campo])
    #fix para el datepicker de las fechas:
    for i in obl.keys():
        form.element(_name=i)['_class']= form.element(_name=i)['_class'] + " obligatoria "+ obl[i].replace(" ", "_")

    for i in no_obl.keys():
        form.element(_name=i)['_class']= form.element(_name=i)['_class'] + ' ' + no_obl[i].replace(" ", "_")


    # Al aceptar el formulario
    if form.process().accepted:
        no = ['nombre','descripcion','fecha_realizacion','fecha_modificacion','lugar', 'colaboradores']
        sql = ''
        if request.vars.borrador:
            sql = "UPDATE PRODUCTO SET estado = 'Borrador' WHERE id_producto = '"+str(id_producto)+"';"
            insertar_log(db, 'PRODUCTO', datetime.datetime.now(), request.client, 'MODICIFACION DE BORRADOR CON ID ' + str(id_producto), session.usuario['usbid'])
        else:
            sql = "UPDATE PRODUCTO SET estado = 'Por Validar' WHERE id_producto = '"+str(id_producto)+"';"
            insertar_log(db, 'PRODUCTO', datetime.datetime.now(), request.client, 'NUEVO PRODUCTO CON ID ' + str(id_producto), session.usuario['usbid'])

        sql2 = "UPDATE PRODUCTO SET fecha_modificacion='"+str(now.date())+"' WHERE id_producto = '"+str(id_producto)+"';"
        db.executesql(sql)
        db.executesql(sql2)

        # Eliminamos los autores anteriores.
        db(db.PARTICIPA_PRODUCTO.id_producto == id_producto).delete()

        for var in form.vars:
            #Buscamos los autores
            try:
                if (var[0:5]=="autor"):
                    usbid_autor = getattr(form.vars, var)
                    if usbid_autor != None:
                        db.PARTICIPA_PRODUCTO.insert(id_producto = id_producto, usbid_usuario =  usbid_autor)
            except Exception, e:
                print "Exception Autor: "
                print e
            try:
                if (var[0:11]=="c0mpr0bant3"):
                    numero_comprobante = var[12:13]
                    descripcion = getattr(form.vars ,'d3scr1pc10n_comprobante_'+ numero_comprobante)
                    nombre = getattr(form.vars ,var)
                    if nombre!='':
                        db.COMPROBANTE.insert(archivo=nombre,descripcion=descripcion,producto=id_producto)
                    continue


                elif (var[0:11]=="d3scr1pc10n"):
                    continue

            except Exception, e:
                print "Exception: "
                print e

            if var[0:5] != 'autor' and var[0:8] != 'borrador':
                valor_anterior = valores[var]
                if not(var in no):

                    try:
                        if (var[0:6]=="campo_"):
                            campo = var[6:]
                        else:
                            campo = var
                    except Exception,e:
                        print "Exception: "
                        print e
                        campo = var

                    valor_nuevo = getattr(form.vars ,var)
                    if valor_nuevo != valor_anterior:
                        campo = campo.replace("_"," ")
                        id_campo = db(db.CAMPO.nombre_interno==campo).select().first().id_campo

                        sql = "UPDATE PRODUCTO_TIENE_CAMPO SET valor_campo = '" + str(valor_nuevo)
                        sql = sql + "' WHERE id_prod = '" + str(id_producto) + "' AND id_campo = '" + str(id_campo) + "';"
                        db.executesql(sql)

                    else:
                        pass
                else:
                    valor_nuevo = getattr(form.vars ,var)
                    if valor_nuevo != valor_anterior:
                        sql = "UPDATE PRODUCTO SET "+var+"= '"+str(valor_nuevo)+\
                              "' WHERE id_producto = '"+str(id_producto)+"';"
                        db.executesql(sql)

                    else:
                        pass

        redirect(URL('gestionar'))

    return locals()

def eliminar():
    admin = get_tipo_usuario(session)

    if not request.args:
        raise HTTP(404)
    id_act = int(request.args(0))

    query = "SELECT archivo FROM COMPROBANTE WHERE producto="+str(id_act)+";"
    comprobantes = db.executesql(query)

    for  i in range (len(comprobantes)):
        pdf = os.path.join(request.folder,'uploads',comprobantes[i][0][0:22],comprobantes[i][0][23:25],comprobantes[i][0])
        try:
            os.unlink(pdf)
        except Exception,e:
            print "Exception: "
            print e


    set_tiene_campo = db(db.PRODUCTO_TIENE_CAMPO.id_prod == id_act)
    set_tiene_campo.delete()
    producto = db(db.PRODUCTO.id_producto == id_act)
    producto.delete()

    insertar_log(db, 'PRODUCTO', datetime.datetime.now(), request.client, 'PRODUCTO CON ID ' + str(id_act) + ' ELIMINADO', session.usuario['usbid'])
    redirect(URL('gestionar'))

    #return "producto {} eliminada".format(producto)
    return locals()

# Funcion utilizada para el ajax en el agregar
def obtener_actividades():
    admin = get_tipo_usuario(session)

    programa = db(db.PROGRAMA.nombre==request.vars.programa).select().first()
    tiposA = db(db.TIPO_ACTIVIDAD.id_programa==programa.id_programa).select(db.TIPO_ACTIVIDAD.nombre,
        db.TIPO_ACTIVIDAD.id_tipo, db.TIPO_ACTIVIDAD.papelera).as_list()

    concat = '<option></option>'

    for tipo in tiposA:
        if tipo['papelera']==False :
            concat += '<option value='+str(tipo['id_tipo'])+'>'+tipo['nombre']+'</option>'

    aux = programa.descripcion.split('\r\n')[0]
    descripcion = "<div class=\"col-sm-offset-1\"><h4>Descripción del Programa:</h4><p>"+aux+"</p></div>"
    html = "jQuery('#lista_tipos').empty().append('"+concat+"');jQuery('#descripcion_programa').empty().append('"+descripcion+"')"
    return html

# Funcion utilizada para el ajax cuando se elige la actividad para que aparezcan los campos
def seleccion_actividad():
    admin = get_tipo_usuario(session)

    if request.vars.id_tipo=="":
        tipo_global = None
        respuesta = "jQuery('#nombre_actividad').empty();"
        respuesta += "jQuery('#descripcion_actividad').empty();"
        respuesta += "jQuery('#campos_actividad').empty()"
        return respuesta

    tipo =  request.vars.id_tipo
    tipo_global = tipo
    posibles_campos = {'Fecha':'date', 'Telefono':'string', 'Texto Corto':'string','Documento':'upload', 'Numero Entero':'integer', 'Texto Largo':'text'}

    campos_id = db(db.ACT_POSEE_CAMPO.id_tipo_act == tipo).select()
    tipo_actividad = db(db.TIPO_ACTIVIDAD.id_tipo == tipo).select().first()
    nombre_actividad = tipo_actividad.nombre
    descripcion_actividad = tipo_actividad.descripcion

    respuesta_inputs = ""

    for row in campos_id:

        rows_campo = db(db.CAMPO.id_campo == row.id_campo).select().first()
        nombre_campo = rows_campo.nombre
        nombre_campo_input = nombre_campo.replace(" ", "_").replace("-", "_")
        obligatorio_campo = rows_campo.obligatorio
        tipo_campo = rows_campo.tipo_campo
        es_obligatorio = ""

        if obligatorio_campo:
            nombre_campo += " (*)"
            es_obligatorio += " obligatorio"


        html_input = '<div class="form-group">'+\
                        '<label for="'+nombre_campo_input+'" class = "control-label col-sm-3">'+nombre_campo+'</label>'+\
                        '<div class="col-sm-8">'+\
                            '<input class="form-control input-'+posibles_campos[tipo_campo]+es_obligatorio+'" type="'+posibles_campos[tipo_campo]+'" name="'+nombre_campo_input+'"/>'+\
                        '</div>'+\
                    '</div>'

        respuesta_inputs += html_input


    respuesta = "jQuery('#nombre_actividad').empty().append('"+nombre_actividad+"');"
    respuesta += "jQuery('#descripcion_actividad').empty().append('"+descripcion_actividad+"');"
    respuesta += "jQuery('#campos_actividad').empty().append('"+respuesta_inputs+"')"

    return respuesta

def get_comprobante():
    admin = get_tipo_usuario(session)

    if not request.args:
        raise HTTP(404)
    query = "SELECT archivo FROM COMPROBANTE WHERE id_comprobante="+request.args(0)+";"
    comprobante = db.executesql(query)

    pdf = os.path.join(request.folder,'uploads',comprobante[0][0][0:22],comprobante[0][0][23:25],comprobante[0][0])
    data = open(pdf,"rb").read()

    response.headers['Content-Type']='application/pdf'
    return data

def descargar_comprobante():
    admin = get_tipo_usuario(session)

    if not request.args:
        raise HTTP(404)
    query = "SELECT archivo FROM COMPROBANTE WHERE id_comprobante="+request.args(0)+";"
    comprobante = db.executesql(query)

    pdf = os.path.join(request.folder,'uploads',comprobante[0][0][0:22],comprobante[0][0][23:25],comprobante[0][0])
    data = open(pdf,"rb").read()

    response.headers['Content-Type']='application/pdf'
    response.headers["Content-Disposition"] = "attachment; filename=%s" % comprobante[0][0]
    return data

def descargar_documento():
    admin = get_tipo_usuario(session)

    if not request.args:
        raise HTTP(404)
    query = "SELECT valor_campo FROM PRODUCTO_TIENE_CAMPO WHERE id_campo="+request.args(0)+" AND id_prod ="+request.args(1)+";"
    documento = db.executesql(query)

    pdf = os.path.join(request.folder,'uploads',documento[0][0])
    data = open(pdf,"rb").read()

    response.headers['Content-Type']='application/pdf'
    response.headers["Content-Disposition"] = "attachment; filename=%s" % documento[0][0]
    return data

#Funcion para exportar PDF de un producto
def get_pdf():
    admin = get_tipo_usuario(session)
    if not request.args:
        raise HTTP(404)
    id_producto = request.args(0)
    producto = db.PRODUCTO(id_producto)
    creador = db(db.USUARIO.usbid == producto.usbid_usu_creador).select().first()

    nombres_autores  = creador.nombres +' '+ creador.apellidos #Primer autor siempre es el creador.
    autores = db(db.PARTICIPA_PRODUCTO.id_producto == id_producto).select()

    for autor in autores:
        autorAux = db(db.USUARIO.usbid == autor.usbid_usuario).select().first()
        nombres_autores  = nombres_autores + ', ' + autorAux.nombres +' '+ autorAux.apellidos

    colaboradores = ""
    if producto.colaboradores :
        colaboradores = producto.colaboradores

    # cargando informacion de los campos adicionales
    dict_campos = dict()
    campos = db((db.PRODUCTO_TIENE_CAMPO.id_campo == db.CAMPO.id_campo)
                & (db.PRODUCTO_TIENE_CAMPO.id_prod == id_producto)).select()

    for campo in campos:
        if campo.CAMPO.tipo_campo in ['Fecha', 'Texto Corto', 'Texto Largo', 'Cedula']:
            dict_campos[campo.CAMPO.nombre] = campo.PRODUCTO_TIENE_CAMPO.valor_campo

    # print(dict_campos)

    tmpfilename = os.path.join(request.folder,'private',str(uuid4()))
    doc = SimpleDocTemplate(tmpfilename)
    elements = []

    # Definimos los estilos para el documento
    estilo = getSampleStyleSheet()

    estilo_tabla = estilo["BodyText"]
    estilo_tabla.alignment = TA_LEFT
    estilo_tabla.fontName = "Helvetica"
    estilo_tabla.fontSize = 10
    estilo_tabla.leading = 12

    estilo_titulo = estilo["Normal"]
    estilo_titulo.alignment = TA_CENTER
    estilo_titulo.fontName = "Helvetica"
    estilo_titulo.fontSize = 12
    estilo_titulo.leading = 15

    estilo_footer = estilo["Italic"]
    estilo_footer.alignment = TA_CENTER
    estilo_footer.fontName = "Helvetica"
    estilo_footer.fontSize = 10
    estilo_footer.leading = 12

    # Agrega el footer al documento
    def addFooter(canvas, doc):

    	footer1 = Paragraph('''<br/>Sartenejas, Baruta, Edo. Miranda - Apartado 89000 Cable Unibolivar Caracas Venezuela. Teléfono +58 0212-9063111
    	 					   <br/>Litoral. Camurí Grande, Edo. Vargas Parroquia Naiguatá. Teléfono +58 0212-9069000	''', estilo_footer)
    	w, h = footer1.wrap(doc.width, doc.bottomMargin)
    	footer1.drawOn(canvas, doc.leftMargin, h)


    usb_logo_url = os.path.join(request.folder, 'static/images','usblogo.png')
    usblogo = Image(usb_logo_url)
    usblogo.drawHeight = 70
    usblogo.drawWidth  = 100

    elements.append(usblogo)
    elements.append(Paragraph('Universidad Simón Bolívar' , estilo_titulo))
    elements.append(Paragraph('Vicerrectorado Académico' , estilo_titulo))
    elements.append(Paragraph('Decanato de Extensión' , estilo_titulo))
    elements.append(Paragraph('Sistema de Registro de Actividades de Extensión (SIRADEx)' , estilo_titulo))
    elements.append(Paragraph('<br/><br/>DATOS DEL PRODUCTO' , estilo_titulo))

    data = []
    data.append([''])
    data.append(['', Paragraph('<b>ID DEL PRODUCTO:</b> ', estilo_tabla),  Paragraph(str(producto.id), estilo_tabla), ''])
    data.append(['', Paragraph('<b>AUTOR(ES):</b> ', estilo_tabla),  Paragraph(nombres_autores, estilo_tabla), ''])

    if colaboradores:
        data.append(['', Paragraph('<b>COLABORADOR(ES):</b>', estilo_tabla),  Paragraph(str(colaboradores), estilo_tabla), ''])

    data.append(['', Paragraph('<b>REGISTRADO POR: </b>' , estilo_tabla),  Paragraph(str(creador.nombres +' '+ creador.apellidos), estilo_tabla),''])
    data.append(['', Paragraph('<b>CI:</b> ' , estilo_tabla),  Paragraph(str(creador.ci), estilo_tabla),''])

    if dict_campos:
        data.append([''])
        data.append(['', Paragraph('<b>DETALLES DEL PRODUCTO </b> ' , estilo_tabla),  Paragraph('', estilo_tabla),''])

        for campo in dict_campos:
            data.append(['', Paragraph('<b>%s:</b> '%str(campo).upper() , estilo_tabla),  Paragraph(str(dict_campos[campo]), estilo_tabla),''])

        data.append([''])

    data.append(['', Paragraph('<b>ÚLTIMA FECHA DE MODIFICACIÓN: </b>' , estilo_tabla) ,  Paragraph(str (producto.fecha_modificacion), estilo_tabla), ''])
    data.append(['', Paragraph('<b>STATUS DE VALIDACIÓN: </b>', estilo_tabla) ,  Paragraph(str (producto.estado), estilo_tabla), ''])

    t=Table(data, colWidths=(2.5*inch))
    t.setStyle(TableStyle([('VALIGN',(1,0),(1,8),'MIDDLE')]))

    elements.append(t)

    # construimos el documento
    doc.build(elements, onFirstPage=addFooter)
    data = open(tmpfilename,"rb").read()
    os.unlink(tmpfilename)
    response.headers['Content-Type']='application/pdf'

    return data


def eliminar_comprobante():
    if not request.args:
        raise HTTP(404)
    id_comprobante = request.args(0)

    admin = get_tipo_usuario(session)

    query = "SELECT archivo FROM COMPROBANTE WHERE id_comprobante="+id_comprobante+";"
    comprobante = db.executesql(query)


    pdf = os.path.join(request.folder,'uploads',comprobante[0][0][0:22],comprobante[0][0][23:25],comprobante[0][0])
    try:
        os.unlink(pdf)
    except Exception,e:
        print "Exception: "
        print e

    db(db.COMPROBANTE.id_comprobante == id_comprobante).delete()
    return redirect(URL(modificar,args=[request.args(1)]))

def eliminar_documento():

    if not request.args:
        raise HTTP(404)
    id_documento = request.args(0)

    admin = get_tipo_usuario(session)

    query = "SELECT valor_campo FROM PRODUCTO_TIENE_CAMPO WHERE id_campo="+id_documento+";"
    documento = db.executesql(query)

    pdf = os.path.join(request.folder,'uploads', documento[0][0])
    try:
        os.unlink(pdf)
    except Exception,e:
        print "Exception: "
        print e

    db(db.PRODUCTO_TIENE_CAMPO.id_campo == id_documento).update(valor_campo="")
    return redirect(URL(modificar,args=[request.args(1)]))

def get_documento():
    admin = get_tipo_usuario(session)

    if not request.args:
        raise HTTP(404)
    print "request:"
    print request.args
    query = "SELECT valor_campo FROM PRODUCTO_TIENE_CAMPO WHERE id_campo    ="+request.args(0)+" AND id_prod ="+request.args(1)+";"
    documento = db.executesql(query)
    print query
    print documento

    pdf = os.path.join(request.folder,'uploads',documento[0][0])
    data = open(pdf,"rb").read()

    response.headers['Content-Type']='application/pdf'
    return data
