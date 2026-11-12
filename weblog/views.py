from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from weblog.models import Article, ArticleRevision
from weblog.forms import ArticleForm, FAQFormSet, InternalLinkFormSet
from django.utils import timezone

def article_list(request):
    articles = Article.objects.filter(
        status=Article.Status.PUBLISHED
     ).select_related(
        # "author"
        ).order_by(
        "-published_date",
        "-created_date"
    )
    return render(request,"weblog/user_article_list.html",{"articles": articles})


def admin_article_list(request):
    articles = Article.objects.all().order_by("-created_date")

    published_count = articles.filter(
        status=Article.Status.PUBLISHED
    ).count()

    draft_count = articles.filter(
        status=Article.Status.DRAFT
    ).count()
    print("تعداد مقالات:", Article.objects.count())
    return render(
        request,
        "weblog/admin_article_list.html",
        {
            "articles": articles,
            "published_count": published_count,
            "draft_count": draft_count,})

def article_detail(request, slug):
    article = get_object_or_404(Article,slug=slug,status=Article.Status.PUBLISHED)
    article.view_count += 1
    article.save(update_fields=['view_count'])
    return render(
        request,
        "weblog/user_article_detail.html",
        {"article": article}
    )

def write_article(request):
    if request.method == "POST":
        form = ArticleForm(request.POST, request.FILES)

        faq_formset = FAQFormSet(request.POST)
        link_formset = InternalLinkFormSet(request.POST)

        if (
            form.is_valid()
            and faq_formset.is_valid()
            and link_formset.is_valid()
        ):
            article = form.save(commit=False)

            action = request.POST.get("action", "draft")

            if action == "review":
                article.status = Article.Status.REVIEW
            else:
                article.status = Article.Status.DRAFT

            with transaction.atomic():
                article.save()

                faq_formset.instance = article
                faq_formset.save()

                link_formset.instance = article
                link_formset.save()

                ArticleRevision.objects.create(
                    article=article,
                    version=1,
                    title=article.title,
                    content=article.content,
                    note="ایجاد محتوا"
                )

            return redirect("weblog:admin_article_list")

    else:
        form = ArticleForm()
        faq_formset = FAQFormSet()
        link_formset = InternalLinkFormSet()

    return render(
        request,
        "weblog/admin_write_article.html",
        {
            "form": form,
            "faq_formset": faq_formset,
            "link_formset": link_formset,
            "revisions": [],
        }
    )

def article_edit(request, article_id):
    article = get_object_or_404(Article, id=article_id)

    if request.method == "POST":
        form = ArticleForm(request.POST, request.FILES, instance=article)
        faq_formset = FAQFormSet(request.POST, instance=article)
        link_formset = InternalLinkFormSet(request.POST, instance=article)

        if form.is_valid() and faq_formset.is_valid() and link_formset.is_valid():
            with transaction.atomic():
                article_obj = form.save(commit=False)

                action = request.POST.get("action")
                if action == "review":
                    article_obj.status = Article.Status.REVIEW
                elif action == "published":
                    article_obj.status = Article.Status.PUBLISHED
                elif action == "draft":
                    article_obj.status = Article.Status.DRAFT      
                if action == "published" and not article_obj.published_date:
                    article_obj.published_date = timezone.now()

                article_obj.save()

                faq_formset.save()
                link_formset.save()

                last_revision = article_obj.revisions.first()
                next_version = (last_revision.version + 1) if last_revision else 1

                ArticleRevision.objects.create(
                    article=article_obj,
                    version=next_version,
                    title=article_obj.title,
                    content=article_obj.content,
                    note=request.POST.get("revision_note", "ویرایش محتوا"),
                )

            return redirect("weblog:admin_article_list")
    else:
        form = ArticleForm(instance=article)
        faq_formset = FAQFormSet(instance=article)
        link_formset = InternalLinkFormSet(instance=article)

    return render(
        request,
        "weblog/admin_article_edit.html",
        {
            "form": form,
            "faq_formset": faq_formset,
            "link_formset": link_formset,
            "article": article,
            "revisions": article.revisions.all()[:10],
        },
    )

def article_delete(request, article_id):
    if request.method == "POST":
        article = get_object_or_404(Article, id=article_id)
        article.delete()

    return redirect("weblog:admin_article_list")