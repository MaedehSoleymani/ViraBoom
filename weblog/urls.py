from django.urls import path
from weblog import views

app_name = "weblog"

urlpatterns = [
    path("", views.article_list, name="article_list"),
    path("admin/write/", views.write_article, name="write_article"),
    path("admin/articles/", views.admin_article_list, name="admin_article_list"),
    path("admin/articles/<int:article_id>/edit/", views.article_edit, name="article_edit"),
    path("admin/articles/<int:article_id>/delete/", views.article_delete, name="article_delete"),
    path("<slug:slug>/", views.article_detail, name="article_detail"),
]
