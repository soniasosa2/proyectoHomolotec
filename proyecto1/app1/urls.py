from django.urls import path
from app1 import views

urlpatterns = [
    path('', views.index, name='index'),
    path('cerrar-sesion/', views.cerrar_sesion, name='cerrar_sesion'),
    
    # Alumno
    path('panel-alumno/', views.panel_alumno, name='panel_alumno'),
    path('mis-solicitudes/', views.mis_solicitudes, name='mis_solicitudes'),
    path('nueva-solicitud/', views.nueva_solicitud, name='nueva_solicitud'),
    path('solicitud-confirmacion/<int:solicitud_id>/', views.solicitud_confirmacion, name='solicitud_confirmacion'),
    path('solicitud/<int:solicitud_id>/', views.detalle_solicitud, name='detalle_solicitud'),
    
    # Secretaría
    path('secretaria/', views.secretaria_dashboard, name='secretaria_dashboard'),
    path('secretaria/solicitudes/', views.secretaria_solicitudes, name='secretaria_solicitudes'),
    path('secretaria/recibir/', views.secretaria_recibir, name='secretaria_recibir'),
    path('secretaria/recibir/<int:solicitud_id>/', views.secretaria_recibir, name='secretaria_recibir_detalle'),
    path('secretaria/resoluciones/', views.secretaria_resoluciones, name='secretaria_resoluciones'),
    path('secretaria/resolucion/<int:solicitud_id>/', views.secretaria_registrar_resolucion, name='secretaria_registrar_resolucion'),
    
    # Jefe de Carrera (CU004, CU006, CU008)
    path('jefe-carrera/', views.jefe_pendientes, name='jefe_pendientes'),
    path('jefe-carrera/asignar/<int:solicitud_id>/', views.jefe_asignar, name='jefe_asignar'),
    path('jefe-carrera/revisar-dictamenes/', views.jefe_dictamenes, name='jefe_dictamenes'),
    path('jefe-carrera/revisar-dictamen/<int:solicitud_id>/', views.jefe_revisar_dictamen, name='jefe_revisar_dictamen'),
    path('jefe-carrera/historial/', views.jefe_historial, name='jefe_historial'),

    # Módulo Profesor Evaluador (CU005 y CU008)
    path('profesor/', views.profesor_inicio, name='profesor_inicio'),
    path('profesor/evaluar/<int:materia_solicitada_id>/', views.profesor_evaluar, name='profesor_evaluar'),
    path('profesor/correcciones/', views.profesor_correcciones, name='profesor_correcciones'),
    path('profesor/corregir/<int:materia_solicitada_id>/', views.profesor_corregir, name='profesor_corregir'),
    path('profesor/historial/', views.profesor_historial, name='profesor_historial'),
   
    # Activación de Cuenta
    path('activar-cuenta/', views.activar_cuenta, name='activar_cuenta'),
    path('verificar-codigo/', views.verificar_codigo, name='verificar_codigo'),
    path('registro-exitoso/', views.registro_exitoso, name='registro_exitoso'),
]
