import datetime
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from .models import PerfilUsuario, SolicitudHomologacion, Materia, MateriaSolicitada

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