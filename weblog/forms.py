
from django import forms
from django.forms import inlineformset_factory

from .models import Article, ArticleFAQ, ArticleInternalLink


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = [
            "title",
            "introduction",
            "author",
            "reviewer",
            "source_info",
            "content",
            "keywords",
            "internal_notes",
            "slug",
            "seo_title",
            "meta_description",
            "focus_keyphrase",
            "img",
            "alt_img",
            "published_date",
        ]

        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "عنوان اصلی مقاله"
            }),
            "introduction": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "معرفی کوتاه مقاله"
            }),
            "author": forms.TextInput(attrs={
                "placeholder": "نام نویسنده"
            }),
            "reviewer": forms.TextInput(attrs={
                "placeholder": "نام بازبین"
            }),
            "source_info": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "منبع اطلاعات و توضیحات تأیید صحت محتوا"
            }),
            "content": forms.Textarea(attrs={
                "rows": 16,
                "placeholder": "متن اصلی مقاله را اینجا بنویسید..."
            }),
            "keywords": forms.TextInput(attrs={
                "placeholder": "مثلاً: آموزش، محصولات، راهنما"
            }),
            "internal_notes": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "یادداشت‌هایی که برای کاربران نمایش داده نمی‌شوند"
            }),
            "slug": forms.TextInput(attrs={
                "placeholder": "مثلاً: article-title"
            }),
            "seo_title": forms.TextInput(attrs={
                "placeholder": "عنوان مناسب برای نتایج جست‌وجو"
            }),
            "meta_description": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "خلاصه‌ای جذاب از مقاله برای موتورهای جست‌وجو"
            }),
            "focus_keyphrase": forms.TextInput(attrs={
                "placeholder": "عبارت کلیدی اصلی"
            }),
            "alt_img": forms.TextInput(attrs={
                "placeholder": "توضیح تصویر برای دسترس‌پذیری"
            }),
            "published_date": forms.DateTimeInput(attrs={
                "type": "datetime-local"
            }),
        }


FAQFormSet = inlineformset_factory(
    Article,
    ArticleFAQ,
    fields=["question", "answer"],
    extra=1,
    can_delete=True
)

InternalLinkFormSet = inlineformset_factory(
    Article,
    ArticleInternalLink,
    fields=["title", "url"],
    extra=1,
    can_delete=True
)
