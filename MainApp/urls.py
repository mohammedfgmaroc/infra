from django.conf import settings
from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf.urls import handler404, handler500



urlpatterns = [
    
    path('', views.data_visualization_view, name='data_visualization'),
    path('data_visualization/', views.data_visualization_view, name='data_visualization'),
    path('home/', views.data_visualization_view, name='data_visualization'),
    path('print_page/', views.print_page_view, name='print_page'),
    path('workers/', views.Workers_managment_view, name='workers_managment'),
    path('workers/<int:pk>', views.Workers_managment_edit_view, name='workers_edit'),
    path('login/', views.Login_infra_view, name='login'),
    path('Upload/', views.Upload_view, name='Upload'),
    path('logout/', views.logout_user, name='logout'),
    path('delete_users/', views.delete_users, name='delete_users'),
    path('delete/<int:pk>/', views.delete_user, name='delete_user'),
    path('add_employee/', views.add_employee, name='add_employee'),
    path('validation/', views.validation_page, name='validation'),
    path('error-500/', views.error_500, name='error_500'),
    path('error-404/', views.error_404, name='error_404'),
    path('download/', views.download_filtered_df_as_excel, name='download_filtered_df_as_excel'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)