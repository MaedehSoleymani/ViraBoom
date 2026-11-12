
from django.db import models


class Article(models.Model):

    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        REVIEW = "review", "در انتظار بازبینی"
        PUBLISHED = "published", "منتشرشده"

    # اطلاعات اصلی
    title = models.CharField(max_length=255)
    introduction = models.TextField(blank=True)
    content = models.TextField()
    author = models.CharField(max_length=150, default="مدیر")
    reviewer = models.CharField(max_length=150, blank=True)
    source_info = models.TextField(blank=True)
    keywords = models.CharField(max_length=500, blank=True)
    internal_notes = models.TextField(blank=True)

    # تصویر
    img = models.ImageField(
        upload_to="article_images/",
        blank=True,
        null=True
    )
    alt_img = models.CharField(max_length=500,null=True, blank=True)

    # آدرس و سئو
    slug = models.SlugField(max_length=255, unique=True)
    seo_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=255, blank=True)
    focus_keyphrase = models.CharField(max_length=255, blank=True)

    # وضعیت و تاریخ‌ها
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT
    )
    view_count = models.IntegerField(default=0)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    published_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.title


class ArticleFAQ(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="faqs"
    )
    question = models.CharField(max_length=500)
    answer = models.TextField()

    def __str__(self):
        return self.question


class ArticleInternalLink(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="internal_links"
    )
    title = models.CharField(max_length=255)
    url = models.URLField()

    def __str__(self):
        return self.title


class ArticleRevision(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="revisions"
    )
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_date"]

    def __str__(self):
        return f"{self.article.title} - نسخه {self.version}"
