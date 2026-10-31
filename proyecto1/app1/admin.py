from django.contrib import admin
from .models import Carrera, Materia, PerfilUsuario, ProgramaAcademico, SolicitudHomologacion, MateriaSolicitada

# Registramos nuestras 6 tablas para verlas en el panel visual
admin.site.register(Carrera)
admin.site.register(Materia)
admin.site.register(PerfilUsuario)
admin.site.register(ProgramaAcademico)
admin.site.register(SolicitudHomologacion)
admin.site.register(MateriaSolicitada)
