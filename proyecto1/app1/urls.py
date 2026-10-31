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
    
    # Activación de Cuenta
    path('activar-cuenta/', views.activar_cuenta, name='activar_cuenta'),
    path('verificar-codigo/', views.verificar_codigo, name='verificar_codigo'),
    path('registro-exitoso/', views.registro_exitoso, name='registro_exitoso'),
]