from django.db import models
from django.contrib.auth.models import User

# ========================================================
# TABLA 1: CARRERAS DEL INSTITUTO
# ========================================================
class Carrera(models.Model):
    nombre = models.CharField(max_length=150, verbose_name="Nombre de la Carrera")

    def __str__(self):
        return self.nombre


# ========================================================
# TABLA 2: MATERIAS DEL INSTITUTO
# ========================================================
class Materia(models.Model):
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name="materias")
    nombre = models.CharField(max_length=150, verbose_name="Nombre de la Materia")
    año = models.CharField(max_length=20, blank=True, null=True, verbose_name="Año / Nivel")

    def __str__(self):
        return f"{self.nombre} ({self.carrera.nombre})"


# ========================================================
# TABLA 3: USUARIOS Y ROLES (CU001) - Con contraseña encriptada por Django
# ========================================================
class PerfilUsuario(models.Model):
    ROLES = [
        ('ALUMNO', 'Alumno'),
        ('SECRETARIA', 'Secretaría'),
        ('JEFE_CARRERA', 'Jefe de Carrera'),
        ('PROFESOR', 'Profesor'),
    ]

    # Vinculado al User de Django (donde la contraseña se guarda con hash PBKDF2/SHA-256)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name="perfil")
    
    nombre_apellido = models.CharField(max_length=150, verbose_name="Nombre y Apellido")
    dni = models.CharField(max_length=15, unique=True, verbose_name="DNI")
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Nacimiento")
    rol = models.CharField(max_length=20, choices=ROLES, default='ALUMNO', verbose_name="Rol")
    carrera = models.ForeignKey(Carrera, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Carrera")
    
    cuenta_activada = models.BooleanField(default=False, verbose_name="¿Cuenta Activada?")
    codigo_verificacion = models.CharField(max_length=6, blank=True, null=True, verbose_name="Código de 6 dígitos")

    def __str__(self):
        return f"{self.nombre_apellido} - {self.get_rol_display()} (DNI: {self.dni})"


# ========================================================
# TABLA 4: PROGRAMAS ACADÉMICOS INSTITUCIONALES (CU009)
# ========================================================
class ProgramaAcademico(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name="programas")
    año_vigencia = models.IntegerField(verbose_name="Año de Vigencia")
    archivo_pdf = models.FileField(upload_to="programas_institucionales/", verbose_name="Archivo PDF del Programa")
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Programa {self.materia.nombre} ({self.año_vigencia})"


# ========================================================
# TABLA 5: SOLICITUD DE HOMOLOGACIÓN - CABECERA (CU002 al CU008)
# ========================================================
class SolicitudHomologacion(models.Model):
    ESTADOS = [
        ('PENDIENTE_PRESENTACION', 'Pendiente de presentación en Secretaría'),
        ('DOCUMENTACION_RECIBIDA', 'Documentación recibida'),
        ('PROFESOR_ASIGNADO', 'Profesor asignado'),
        ('EN_EVALUACION', 'En evaluación'),
        ('EVALUACION_FINALIZADA', 'Evaluación finalizada'),
        ('CORRECCION_SOLICITADA', 'Corrección solicitada'),
        ('DICTAMEN_APROBADO', 'Dictamen aprobado'),
        ('HOMOLOGACION_APROBADA', 'Homologación aprobada'),
        ('HOMOLOGACION_RECHAZADA', 'Homologación rechazada'),
    ]

    # Número único de trámite, ej: HOM-2026-0019
    numero_tramite = models.CharField(max_length=30, unique=True, verbose_name="Número de Trámite")
    alumno = models.ForeignKey(PerfilUsuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'ALUMNO'}, related_name="solicitudes")
    
    # Datos de origen (del instituto anterior)
    institucion_origen = models.CharField(max_length=200, verbose_name="Institución de Origen")
    carrera_origen = models.CharField(max_length=200, verbose_name="Carrera de Origen")
    
    # Documentación digital adjunta en PDF
    analitico_pdf = models.FileField(upload_to="analiticos/", null=True, blank=True, verbose_name="Certificado Analítico")
    programa_origen_pdf = models.FileField(upload_to="programas_origen/", null=True, blank=True, verbose_name="Programa de la Materia de Origen")
    
    observaciones_alumno = models.TextField(blank=True, null=True, verbose_name="Observaciones del Alumno")
    estado = models.CharField(max_length=30, choices=ESTADOS, default='PENDIENTE_PRESENTACION', verbose_name="Estado de la Solicitud")
    
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    def __str__(self):
        return f"{self.numero_tramite} - {self.alumno.nombre_apellido} ({self.get_estado_display()})"


# ========================================================
# TABLA 6: MATERIAS SOLICITADAS / DETALLE (CU004, CU005, CU006, CU007)
# ========================================================
class MateriaSolicitada(models.Model):
    RESULTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
    ]

    solicitud = models.ForeignKey(SolicitudHomologacion, on_delete=models.CASCADE, related_name="materias_solicitadas")
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, verbose_name="Materia Institucional a Homologar")
    
    # Asignación realizada por el Jefe de Carrera (CU004)
    profesor_evaluador = models.ForeignKey(PerfilUsuario, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'rol': 'PROFESOR'}, related_name="evaluaciones_asignadas")
    programa_institucional = models.ForeignKey(ProgramaAcademico, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Evaluación y dictamen del Profesor (CU005)
    resultado_dictamen = models.CharField(max_length=20, choices=RESULTADOS, default='PENDIENTE', verbose_name="Resultado Dictamen")
    fundamentacion_profesor = models.TextField(blank=True, null=True, verbose_name="Fundamentación del Profesor")
    
    # Observaciones del Jefe de Carrera si solicita corrección (CU006)
    observaciones_jefe_carrera = models.TextField(blank=True, null=True, verbose_name="Observaciones Jefe de Carrera")

    def __str__(self):
        return f"{self.solicitud.numero_tramite} - {self.materia.nombre}"
