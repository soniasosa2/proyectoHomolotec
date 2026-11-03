import datetime
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from .models import PerfilUsuario, SolicitudHomologacion, Materia, MateriaSolicitada, Carrera, ProgramaAcademico

# ========================================================
# PÁGINA PÚBLICA DE PRESENTACIÓN / LANDING PAGE
# ========================================================
def landing(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        instituto = request.POST.get('instituto', '').strip()
        email = request.POST.get('email', '').strip()

        # Mostramos en consola el contacto recibido
        print("==========================================")
        print("📩 NUEVA CONSULTA DE CONTRATACIÓN HOMOLOTEC:")
        print(f"Contacto: {nombre} ({email}) - Instituto: {instituto}")
        print("==========================================")

        messages.success(request, f'¡Muchas gracias {nombre}! Recibimos tu consulta sobre "{instituto}". Nos comunicaremos a la brevedad.')
        return redirect('landing')

    return render(request, 'app1/landing.html')


# ========================================================
# PANTALLA 1: INICIAR SESIÓN (LOGIN INTELIGENTE POR ROL)
# ========================================================
def index(request):
    # Si ya está logueado, lo mandamos a su panel correspondiente
    if request.user.is_authenticated and hasattr(request.user, 'perfil'):
        if request.user.perfil.rol == 'ALUMNO':
            return redirect('panel_alumno')
        elif request.user.perfil.rol == 'SECRETARIA':
            return redirect('secretaria_dashboard')
        elif request.user.perfil.rol == 'JEFE_CARRERA':
            return redirect('jefe_pendientes')
        elif request.user.perfil.rol == 'PROFESOR':
            return redirect('profesor_inicio')

    if request.method == 'POST':
        correo = request.POST.get('correo', '').strip()
        password = request.POST.get('password')

        user = authenticate(request, username=correo, password=password)

        if user is not None:
            login(request, user)
            # Redirección según el Rol de la persona
            if hasattr(user, 'perfil'):
                if user.perfil.rol == 'ALUMNO':
                    return redirect('panel_alumno')
                elif user.perfil.rol == 'SECRETARIA':
                    return redirect('secretaria_dashboard')
                elif user.perfil.rol == 'JEFE_CARRERA':
                    return redirect('jefe_pendientes')
                elif user.perfil.rol == 'PROFESOR':
                    return redirect('profesor_inicio')
            return redirect('index')
        else:
            messages.error(request, 'Correo electrónico o contraseña incorrectos.')

    return render(request, 'app1/index.html')


def cerrar_sesion(request):
    logout(request)
    return redirect('index')


# ========================================================
# MÓDULO ALUMNO (CU001, CU002, CU008)
# ========================================================
@login_required(login_url='index')
def panel_alumno(request):
    perfil = request.user.perfil
    solicitudes = SolicitudHomologacion.objects.filter(alumno=perfil).order_by('-fecha_creacion')
    
    total_solicitudes = solicitudes.count()
    en_evaluacion = solicitudes.filter(estado='EN_EVALUACION').count()
    finalizadas = solicitudes.filter(estado__in=['HOMOLOGACION_APROBADA', 'HOMOLOGACION_RECHAZADA']).count()

    contexto = {
        'perfil': perfil,
        'solicitudes': solicitudes[:5],
        'total_solicitudes': total_solicitudes,
        'en_evaluacion': en_evaluacion,
        'finalizadas': finalizadas,
    }
    return render(request, 'app1/panel_alumno.html', contexto)


@login_required(login_url='index')
def mis_solicitudes(request):
    perfil = request.user.perfil
    solicitudes = SolicitudHomologacion.objects.filter(alumno=perfil).order_by('-fecha_actualizacion')

    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        solicitudes = solicitudes.filter(
            Q(numero_tramite__icontains=busqueda) |
            Q(materias_solicitadas__materia__nombre__icontains=busqueda)
        ).distinct()

    estado_filtro = request.GET.get('estado', '')
    if estado_filtro:
        solicitudes = solicitudes.filter(estado=estado_filtro)

    contexto = {
        'solicitudes': solicitudes,
        'busqueda': busqueda,
        'estado_filtro': estado_filtro,
        'estados_disponibles': SolicitudHomologacion.ESTADOS,
    }
    return render(request, 'app1/mis_solicitudes.html', contexto)


@login_required(login_url='index')
def nueva_solicitud(request):
    perfil = request.user.perfil

    if request.method == 'POST':
        institucion_origen = request.POST.get('institucion_origen')
        carrera_origen = request.POST.get('carrera_origen')
        observaciones = request.POST.get('observaciones', '')
        materias_seleccionadas = request.POST.getlist('materias')

        año_actual = datetime.datetime.now().year
        total_anteriores = SolicitudHomologacion.objects.count() + 1
        numero_tramite = f"HOM-{año_actual}-{total_anteriores:04d}"

        solicitud = SolicitudHomologacion.objects.create(
            numero_tramite=numero_tramite,
            alumno=perfil,
            institucion_origen=institucion_origen,
            carrera_origen=carrera_origen,
            observaciones_alumno=observaciones,
            estado='PENDIENTE_PRESENTACION'
        )

        for materia_id in materias_seleccionadas:
            if materia_id:
                MateriaSolicitada.objects.create(
                    solicitud=solicitud,
                    materia_id=materia_id
                )

        return redirect('solicitud_confirmacion', solicitud_id=solicitud.id)

    materias_disponibles = Materia.objects.all()
    return render(request, 'app1/nueva_solicitud.html', {'materias_disponibles': materias_disponibles})


@login_required(login_url='index')
def solicitud_confirmacion(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudHomologacion, id=solicitud_id, alumno=request.user.perfil)
    return render(request, 'app1/solicitud_confirmacion.html', {'solicitud': solicitud})


@login_required(login_url='index')
def detalle_solicitud(request, solicitud_id):
    # Si es alumno solo ve la suya, si es secretaría puede ver cualquiera
    if request.user.perfil.rol == 'ALUMNO':
        solicitud = get_object_or_404(SolicitudHomologacion, id=solicitud_id, alumno=request.user.perfil)
    else:
        solicitud = get_object_or_404(SolicitudHomologacion, id=solicitud_id)
    return render(request, 'app1/detalle_solicitud.html', {'solicitud': solicitud})


# ========================================================
# CU001: ACTIVACIÓN DE CUENTA
# ========================================================
def activar_cuenta(request):
    if request.method == 'POST':
        nombre_apellido = request.POST.get('nombre_apellido', '').strip()
        dni = request.POST.get('dni', '').strip()
        fecha_nacimiento = request.POST.get('fecha_nacimiento')
        correo = request.POST.get('correo', '').strip()
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'app1/activar_cuenta.html')

        if len(password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
            return render(request, 'app1/activar_cuenta.html')

        if User.objects.filter(email=correo).exists():
            messages.error(request, 'El correo electrónico ya se encuentra registrado con otra cuenta.')
            return render(request, 'app1/activar_cuenta.html')

        try:
            perfil = PerfilUsuario.objects.get(dni=dni)
        except PerfilUsuario.DoesNotExist:
            messages.error(request, 'No fue posible verificar tu identidad con el DNI ingresado. Comunicate con Secretaría.')
            return render(request, 'app1/activar_cuenta.html')

        if perfil.cuenta_activada:
            messages.error(request, 'Esta cuenta ya se encuentra activada. Podés iniciar sesión directamente.')
            return render(request, 'app1/activar_cuenta.html')

        codigo = str(random.randint(100000, 999999))
        perfil.codigo_verificacion = codigo
        perfil.save()

        request.session['activacion_perfil_id'] = perfil.id
        request.session['activacion_correo'] = correo
        request.session['activacion_password'] = password

        print("==========================================")
        print(f"📧 CÓDIGO DE VERIFICACIÓN ENVIADO: {codigo}")
        print("==========================================")

        return redirect('verificar_codigo')

    return render(request, 'app1/activar_cuenta.html')


def verificar_codigo(request):
    perfil_id = request.session.get('activacion_perfil_id')
    correo = request.session.get('activacion_correo', 'tu-correo@email.com')
    password = request.session.get('activacion_password')

    if not perfil_id:
        return redirect('activar_cuenta')

    perfil = PerfilUsuario.objects.get(id=perfil_id)

    if request.method == 'POST':
        codigo_ingresado = "".join([
            request.POST.get('d1', ''),
            request.POST.get('d2', ''),
            request.POST.get('d3', ''),
            request.POST.get('d4', ''),
            request.POST.get('d5', ''),
            request.POST.get('d6', ''),
        ]).strip()

        if codigo_ingresado == perfil.codigo_verificacion:
            user = User.objects.create_user(
                username=correo,
                email=correo,
                password=password,
                first_name=perfil.nombre_apellido
            )
            perfil.user = user
            perfil.cuenta_activada = True
            perfil.codigo_verificacion = None
            perfil.save()

            request.session.flush()
            return redirect('registro_exitoso')
        else:
            messages.error(request, 'El código ingresado es incorrecto. Verificalo en la terminal.')

    return render(request, 'app1/verificar_codigo.html', {'correo': correo})


def registro_exitoso(request):
    return render(request, 'app1/registro_exitoso.html')


# ========================================================
# MÓDULO SECRETARÍA (CU003 y Pantalla 13 del PDF)
# ========================================================
# Dashboard principal de Secretaría
@login_required(login_url='index')
def secretaria_dashboard(request):
    if request.user.perfil.rol != 'SECRETARIA':
        return redirect('index')

    total = SolicitudHomologacion.objects.count()
    pendientes = SolicitudHomologacion.objects.filter(estado='PENDIENTE_PRESENTACION').count()
    en_evaluacion = SolicitudHomologacion.objects.filter(estado='EN_EVALUACION').count()
    finalizadas = SolicitudHomologacion.objects.filter(
        estado__in=['HOMOLOGACION_APROBADA', 'HOMOLOGACION_RECHAZADA']
    ).count()
    solicitudes_recientes = SolicitudHomologacion.objects.all().order_by('-fecha_actualizacion')[:5]

    contexto = {
        'total': total,
        'pendientes': pendientes,
        'en_evaluacion': en_evaluacion,
        'finalizadas': finalizadas,
        'solicitudes_recientes': solicitudes_recientes,
    }
    return render(request, 'app1/secretaria_dashboard.html', contexto)
@login_required(login_url='index')
def secretaria_solicitudes(request):
    # Verificamos que sea Secretaría
    if request.user.perfil.rol != 'SECRETARIA':
        return redirect('index')

    solicitudes = SolicitudHomologacion.objects.all().order_by('-fecha_actualizacion')

    # Búsqueda por número de trámite, nombre de alumno o materia
    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        solicitudes = solicitudes.filter(
            Q(numero_tramite__icontains=busqueda) |
            Q(alumno__nombre_apellido__icontains=busqueda) |
            Q(materias_solicitadas__materia__nombre__icontains=busqueda)
        ).distinct()

    # Filtro por estado
    estado_filtro = request.GET.get('estado', '')
    if estado_filtro:
        solicitudes = solicitudes.filter(estado=estado_filtro)

    contexto = {
        'solicitudes': solicitudes,
        'busqueda': busqueda,
        'estado_filtro': estado_filtro,
        'estados_disponibles': SolicitudHomologacion.ESTADOS,
    }
    return render(request, 'app1/secretaria_solicitudes.html', contexto)


# CU003: Registrar Recepción y Verificación de Documentos
@login_required(login_url='index')
def secretaria_recibir(request, solicitud_id=None):
    if request.user.perfil.rol != 'SECRETARIA':
        return redirect('index')

    solicitud = None
    numero_tramite = request.GET.get('numero_tramite', '').strip()

    # Si viene con ID directo o si buscó por número de trámite
    if solicitud_id:
        solicitud = get_object_or_404(SolicitudHomologacion, id=solicitud_id)
    elif numero_tramite:
        try:
            solicitud = SolicitudHomologacion.objects.get(numero_tramite__iexact=numero_tramite)
        except SolicitudHomologacion.DoesNotExist:
            messages.error(request, f'No se encontró ningún trámite con el número "{numero_tramite}".')

    # Si Secretaría confirma la recepción de los documentos
    if request.method == 'POST' and solicitud:
        solicitud.estado = 'DOCUMENTACION_RECIBIDA'
        solicitud.save()
        messages.success(request, f'¡Recepción confirmada! El trámite #{solicitud.numero_tramite} pasó a estado "Documentación recibida".')
        return redirect('secretaria_solicitudes')

    return render(request, 'app1/secretaria_recibir.html', {'solicitud': solicitud, 'numero_tramite': numero_tramite})

# ========================================================
# MÓDULO JEFE DE CARRERA (CU004, CU006, CU008)
# ========================================================

@login_required(login_url='index')
def jefe_pendientes(request):
    if request.user.perfil.rol != 'JEFE_CARRERA':
        return redirect('index')

    perfil = request.user.perfil
    
    solicitudes = SolicitudHomologacion.objects.filter(
        estado__in=['DOCUMENTACION_RECIBIDA', 'PENDIENTE_PRESENTACION', 'PROFESOR_ASIGNADO']
    ).order_by('-fecha_actualizacion')

    if perfil.carrera:
        solicitudes = solicitudes.filter(
            Q(alumno__carrera=perfil.carrera) | Q(materias_solicitadas__materia__carrera=perfil.carrera)
        ).distinct()

    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        solicitudes = solicitudes.filter(
            Q(numero_tramite__icontains=busqueda) |
            Q(alumno__nombre_apellido__icontains=busqueda) |
            Q(materias_solicitadas__materia__nombre__icontains=busqueda)
        ).distinct()

    filtro_falta = request.GET.get('falta', 'todos')

    items_pendientes = []
    for s in solicitudes:
        for ms in s.materias_solicitadas.all():
            falta = None
            if not ms.profesor_evaluador and not ms.programa_institucional:
                falta = 'profesor_y_programa'
                falta_label = 'Profesor y programa'
                falta_badge = 'badge-pendiente'
            elif ms.profesor_evaluador and not ms.programa_institucional:
                falta = 'programa'
                falta_label = 'Programa de estudio'
                falta_badge = 'badge-recibida'
            elif not ms.profesor_evaluador and ms.programa_institucional:
                falta = 'profesor'
                falta_label = 'Profesor evaluador'
                falta_badge = 'badge-en-evaluacion'

            if falta:
                if filtro_falta == 'todos' or filtro_falta == falta:
                    items_pendientes.append({
                        'solicitud': s,
                        'materia_solicitada': ms,
                        'falta': falta,
                        'falta_label': falta_label,
                        'falta_badge': falta_badge,
                    })

    contexto = {
        'items_pendientes': items_pendientes,
        'total_pendientes': len(items_pendientes),
        'busqueda': busqueda,
        'filtro_falta': filtro_falta,
    }
    return render(request, 'app1/jefe_pendientes.html', contexto)


@login_required(login_url='index')
def jefe_asignar(request, solicitud_id):
    if request.user.perfil.rol != 'JEFE_CARRERA':
        return redirect('index')

    solicitud = get_object_or_404(SolicitudHomologacion, id=solicitud_id)
    materias_solicitadas = solicitud.materias_solicitadas.all()
    profesores = PerfilUsuario.objects.filter(rol='PROFESOR')

    materias_con_programas = []
    for ms in materias_solicitadas:
        programas = ProgramaAcademico.objects.filter(materia=ms.materia)
        materias_con_programas.append({
            'ms': ms,
            'programas': programas,
        })

    if request.method == 'POST':
        todas_completas = True
        for ms in materias_solicitadas:
            prof_id = request.POST.get(f'profesor_{ms.id}')
            prog_id = request.POST.get(f'programa_{ms.id}')

            if prof_id:
                ms.profesor_evaluador_id = prof_id
            else:
                todas_completas = False

            if prog_id:
                ms.programa_institucional_id = prog_id
            else:
                todas_completas = False

            ms.save()

        if todas_completas:
            solicitud.estado = 'PROFESOR_ASIGNADO'
            solicitud.save()
            messages.success(request, f'¡Asignación guardada con éxito! La solicitud #{solicitud.numero_tramite} fue asignada a los profesores evaluadores.')
        else:
            messages.info(request, f'Se guardaron las asignaciones parciales para la solicitud #{solicitud.numero_tramite}.')

        return redirect('jefe_pendientes')

    contexto = {
        'solicitud': solicitud,
        'materias_con_programas': materias_con_programas,
        'profesores': profesores,
    }
    return render(request, 'app1/jefe_asignar.html', contexto)


@login_required(login_url='index')
def jefe_dictamenes(request):
    if request.user.perfil.rol != 'JEFE_CARRERA':
        return redirect('index')

    perfil = request.user.perfil
    solicitudes = SolicitudHomologacion.objects.filter(
        estado__in=['EVALUACION_FINALIZADA', 'CORRECCION_SOLICITADA']
    ).order_by('-fecha_actualizacion')

    if perfil.carrera:
        solicitudes = solicitudes.filter(
            Q(alumno__carrera=perfil.carrera) | Q(materias_solicitadas__materia__carrera=perfil.carrera)
        ).distinct()

    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        solicitudes = solicitudes.filter(
            Q(numero_tramite__icontains=busqueda) |
            Q(alumno__nombre_apellido__icontains=busqueda) |
            Q(materias_solicitadas__materia__nombre__icontains=busqueda)
        ).distinct()

    contexto = {
        'solicitudes': solicitudes,
        'busqueda': busqueda,
    }
    return render(request, 'app1/jefe_dictamenes.html', contexto)


@login_required(login_url='index')
def jefe_revisar_dictamen(request, solicitud_id):
    if request.user.perfil.rol != 'JEFE_CARRERA':
        return redirect('index')

    solicitud = get_object_or_404(SolicitudHomologacion, id=solicitud_id)
    materia_solicitada = solicitud.materias_solicitadas.first()

    if request.method == 'POST':
        accion = request.POST.get('accion')
        observaciones = request.POST.get('observaciones', '').strip()

        if accion == 'aprobar':
            solicitud.estado = 'DICTAMEN_APROBADO'
            solicitud.save()
            messages.success(request, f'¡Dictamen aprobado! La solicitud #{solicitud.numero_tramite} fue derivada a Secretaría para registrar la resolución.')
            return redirect('jefe_dictamenes')

        elif accion == 'corregir':
            if not observaciones:
                messages.error(request, 'Las observaciones son obligatorias cuando se solicita una corrección al docente.')
            else:
                solicitud.estado = 'CORRECCION_SOLICITADA'
                solicitud.save()
                if materia_solicitada:
                    materia_solicitada.observaciones_jefe_carrera = observaciones
                    materia_solicitada.save()
                messages.warning(request, f'Se solicitó corrección al profesor para la solicitud #{solicitud.numero_tramite}.')
                return redirect('jefe_dictamenes')

    contexto = {
        'solicitud': solicitud,
        'materia_solicitada': materia_solicitada,
    }
    return render(request, 'app1/jefe_revisar_dictamen.html', contexto)


@login_required(login_url='index')
def jefe_historial(request):
    if request.user.perfil.rol != 'JEFE_CARRERA':
        return redirect('index')

    perfil = request.user.perfil
    solicitudes = SolicitudHomologacion.objects.exclude(
        estado__in=['PENDIENTE_PRESENTACION', 'DOCUMENTACION_RECIBIDA']
    ).order_by('-fecha_actualizacion')

    if perfil.carrera:
        solicitudes = solicitudes.filter(
            Q(alumno__carrera=perfil.carrera) | Q(materias_solicitadas__materia__carrera=perfil.carrera)
        ).distinct()

    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        solicitudes = solicitudes.filter(
            Q(numero_tramite__icontains=busqueda) |
            Q(alumno__nombre_apellido__icontains=busqueda) |
            Q(materias_solicitadas__materia__nombre__icontains=busqueda)
        ).distinct()

    estado_filtro = request.GET.get('estado', '')
    if estado_filtro:
        solicitudes = solicitudes.filter(estado=estado_filtro)

    contexto = {
        'solicitudes': solicitudes,
        'busqueda': busqueda,
        'estado_filtro': estado_filtro,
        'estados_disponibles': SolicitudHomologacion.ESTADOS,
    }
    return render(request, 'app1/jefe_historial.html', contexto)
# ========================================================
# MÓDULO PROFESOR EVALUADOR (CU005, CU008)
# ========================================================

@login_required(login_url='index')
def profesor_inicio(request):
    if request.user.perfil.rol != 'PROFESOR':
        return redirect('index')

    perfil = request.user.perfil
    mis_evaluaciones = MateriaSolicitada.objects.filter(profesor_evaluador=perfil)

    # 1. Trámites pendientes de evaluar
    por_evaluar = mis_evaluaciones.filter(
        resultado_dictamen='PENDIENTE',
        solicitud__estado__in=['PROFESOR_ASIGNADO', 'EN_EVALUACION']
    )

    # 2. Trámites devueltos para corrección por el Jefe de Carrera
    para_corregir = mis_evaluaciones.filter(solicitud__estado='CORRECCION_SOLICITADA')

    # 3. Dictámenes ya emitidos
    dictamenes_enviados = mis_evaluaciones.exclude(resultado_dictamen='PENDIENTE')

    contexto = {
        'por_evaluar': por_evaluar,
        'cant_por_evaluar': por_evaluar.count(),
        'cant_para_corregir': para_corregir.count(),
        'cant_enviados': dictamenes_enviados.count(),
    }
    return render(request, 'app1/profesor_inicio.html', contexto)


@login_required(login_url='index')
def profesor_evaluar(request, materia_solicitada_id):
    if request.user.perfil.rol != 'PROFESOR':
        return redirect('index')

    materia_solicitada = get_object_or_404(
        MateriaSolicitada, 
        id=materia_solicitada_id, 
        profesor_evaluador=request.user.perfil
    )
    solicitud = materia_solicitada.solicitud

    if request.method == 'POST':
        resultado = request.POST.get('resultado')
        observaciones = request.POST.get('observaciones', '').strip()

        if not observaciones:
            messages.error(request, 'Las observaciones y fundamentación son obligatorias.')
        else:
            materia_solicitada.resultado_dictamen = resultado
            materia_solicitada.fundamentacion_profesor = observaciones
            materia_solicitada.save()

            # La solicitud pasa a "Evaluación finalizada" para que la revise el Jefe de Carrera
            solicitud.estado = 'EVALUACION_FINALIZADA'
            solicitud.save()

            messages.success(request, f'¡Dictamen registrado con éxito para {materia_solicitada.materia.nombre}! Se notificó al Jefe de Carrera.')
            return redirect('profesor_inicio')

    contexto = {
        'materia_solicitada': materia_solicitada,
        'solicitud': solicitud,
    }
    return render(request, 'app1/profesor_evaluar.html', contexto)


@login_required(login_url='index')
def profesor_correcciones(request):
    if request.user.perfil.rol != 'PROFESOR':
        return redirect('index')

    perfil = request.user.perfil
    correcciones = MateriaSolicitada.objects.filter(
        profesor_evaluador=perfil,
        solicitud__estado='CORRECCION_SOLICITADA'
    ).order_by('-solicitud__fecha_actualizacion')

    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        correcciones = correcciones.filter(
            Q(solicitud__numero_tramite__icontains=busqueda) |
            Q(solicitud__alumno__nombre_apellido__icontains=busqueda) |
            Q(materia__nombre__icontains=busqueda)
        ).distinct()

    contexto = {
        'correcciones': correcciones,
        'busqueda': busqueda,
    }
    return render(request, 'app1/profesor_correcciones.html', contexto)


@login_required(login_url='index')
def profesor_corregir(request, materia_solicitada_id):
    if request.user.perfil.rol != 'PROFESOR':
        return redirect('index')

    materia_solicitada = get_object_or_404(
        MateriaSolicitada, 
        id=materia_solicitada_id, 
        profesor_evaluador=request.user.perfil
    )
    solicitud = materia_solicitada.solicitud

    if request.method == 'POST':
        resultado = request.POST.get('resultado')
        observaciones = request.POST.get('observaciones', '').strip()

        if not observaciones:
            messages.error(request, 'La fundamentación y respuesta a las observaciones son obligatorias.')
        else:
            materia_solicitada.resultado_dictamen = resultado
            materia_solicitada.fundamentacion_profesor = observaciones
            materia_solicitada.save()

            # Al reenviar vuelve a revisión del Jefe de Carrera
            solicitud.estado = 'EVALUACION_FINALIZADA'
            solicitud.save()

            messages.success(request, f'¡Dictamen corregido y reenviado al Jefe de Carrera!')
            return redirect('profesor_inicio')

    contexto = {
        'materia_solicitada': materia_solicitada,
        'solicitud': solicitud,
    }
    return render(request, 'app1/profesor_corregir.html', contexto)


@login_required(login_url='index')
def profesor_historial(request):
    if request.user.perfil.rol != 'PROFESOR':
        return redirect('index')

    perfil = request.user.perfil
    evaluaciones = MateriaSolicitada.objects.filter(
        profesor_evaluador=perfil
    ).exclude(resultado_dictamen='PENDIENTE').order_by('-solicitud__fecha_actualizacion')

    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        evaluaciones = evaluaciones.filter(
            Q(solicitud__numero_tramite__icontains=busqueda) |
            Q(solicitud__alumno__nombre_apellido__icontains=busqueda) |
            Q(materia__nombre__icontains=busqueda)
        ).distinct()

    contexto = {
        'evaluaciones': evaluaciones,
        'busqueda': busqueda,
    }
    return render(request, 'app1/profesor_historial.html', contexto)
# ========================================================
# CU007: REGISTRAR RESOLUCIÓN DE HOMOLOGACIÓN (SECRETARÍA)
# ========================================================

@login_required(login_url='index')
def secretaria_resoluciones(request):
    if request.user.perfil.rol != 'SECRETARIA':
        return redirect('index')

    # Trámites con dictamen aprobado por el Jefe de Carrera listos para finalizar
    solicitudes = SolicitudHomologacion.objects.filter(
        estado='DICTAMEN_APROBADO'
    ).order_by('-fecha_actualizacion')

    busqueda = request.GET.get('q', '').strip()
    if busqueda:
        solicitudes = solicitudes.filter(
            Q(numero_tramite__icontains=busqueda) |
            Q(alumno__nombre_apellido__icontains=busqueda) |
            Q(materias_solicitadas__materia__nombre__icontains=busqueda)
        ).distinct()

    contexto = {
        'solicitudes': solicitudes,
        'busqueda': busqueda,
    }
    return render(request, 'app1/secretaria_resoluciones.html', contexto)


@login_required(login_url='index')
def secretaria_registrar_resolucion(request, solicitud_id):
    if request.user.perfil.rol != 'SECRETARIA':
        return redirect('index')

    solicitud = get_object_or_404(SolicitudHomologacion, id=solicitud_id)
    materia_solicitada = solicitud.materias_solicitadas.first()

    # Si el dictamen del docente fue rechazado, la resolución es rechazo; si no, es aprobación
    es_aprobada = True
    if materia_solicitada and materia_solicitada.resultado_dictamen == 'RECHAZADA':
        es_aprobada = False

    # Al presionar CONFIRMAR en el modal
    if request.method == 'POST':
        if es_aprobada:
            solicitud.estado = 'HOMOLOGACION_APROBADA'
        else:
            solicitud.estado = 'HOMOLOGACION_RECHAZADA'
        solicitud.save()

        # Muestra la Pantalla 12 ter (Resolución registrada con éxito)
        contexto_exito = {
            'solicitud': solicitud,
            'materia_solicitada': materia_solicitada,
            'es_aprobada': es_aprobada,
        }
        return render(request, 'app1/secretaria_resolucion_exitosa.html', contexto_exito)

    contexto = {
        'solicitud': solicitud,
        'materia_solicitada': materia_solicitada,
        'es_aprobada': es_aprobada,
    }
    return render(request, 'app1/secretaria_registrar_resolucion.html', contexto)

# ========================================================
# CU009: GESTIÓN DE PROGRAMAS ACADÉMICOS INSTITUCIONALES
# ========================================================
@login_required(login_url='index')
def programas_listado(request):
    # Solo permitido para Secretaría y Jefe de Carrera (según actores de CU009)
    if request.user.perfil.rol not in ['SECRETARIA', 'JEFE_CARRERA']:
        return redirect('index')

    programas = ProgramaAcademico.objects.select_related('materia', 'materia__carrera').order_by('materia__nombre', '-año_vigencia')

    # Si es Jefe de Carrera con carrera asignada, mostramos preferentemente los de su carrera
    perfil = request.user.perfil
    if perfil.rol == 'JEFE_CARRERA' and perfil.carrera:
        programas = programas.filter(materia__carrera=perfil.carrera)

    contexto = {
        'programas': programas,
    }
    return render(request, 'app1/programas_listado.html', contexto)


@login_required(login_url='index')
def programa_cargar(request):
    if request.user.perfil.rol not in ['SECRETARIA', 'JEFE_CARRERA']:
        return redirect('index')

    perfil = request.user.perfil
    materias = Materia.objects.select_related('carrera').order_by('nombre')
    if perfil.rol == 'JEFE_CARRERA' and perfil.carrera:
        materias = materias.filter(carrera=perfil.carrera)

    año_actual = datetime.datetime.now().year

    if request.method == 'POST':
        materia_id = request.POST.get('materia_id')
        año_vigencia = request.POST.get('año_vigencia')
        archivo_pdf = request.FILES.get('archivo_pdf')

        if not materia_id or not año_vigencia or not archivo_pdf:
            messages.error(request, 'Por favor completá todos los campos obligatorios.')
        elif not archivo_pdf.name.lower().endswith('.pdf'):
            messages.error(request, 'El archivo adjunto debe ser en formato PDF.')
        else:
            materia = get_object_or_404(Materia, id=materia_id)
            programa = ProgramaAcademico.objects.create(
                materia=materia,
                año_vigencia=int(año_vigencia),
                archivo_pdf=archivo_pdf
            )
            messages.success(request, f'¡Programa de "{materia.nombre}" (Vigencia {año_vigencia}) guardado con éxito!')
            return redirect('programas_listado')

    contexto = {
        'materias': materias,
        'año_actual': año_actual,
    }
    return render(request, 'app1/programa_cargar.html', contexto)