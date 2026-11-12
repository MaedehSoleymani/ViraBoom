from django.db import models

class Order (models.Model):

    class Status(models.TextChoices):
        CANCELLED= 'cancelled' , 'کنسل شده'
        COMPLETED= 'completed', 'تکمیل شده'
        ONGOING= 'ongoing', 'در حال تکمیل'
    #user= models.ForeignKey
    order_no= models.IntegerField(max_length=255, null=False)
    email= models.EmailField(null=True, blank=True)
    total_cost= models.IntegerField(max_length=255, null=False)
    order_date= models.DateTimeField(null=False, blank=False, auto_now_add=True)
    order_status= models.CharField(max_length=20, choices=Status.choices)
    # order_items=
    item_number= models.IntegerField(max_length=255)

class Payments(models.Model):
    class Status(models.TextChoices):
        FAILED= 'failed'
        SUCCESSFULL= 'successfull'

    order= ForeignKey(Order, null=False)
    cost= models.IntegerField(max_length=255, null=False)
    payments_status= models.CharField (max_length=20, choices=Status.choices))
    payment_date= models.DateTimeField(null=False, blank=False, auto_now_add=True)
    # شناسه تراکنش درگاه
    sh_t_d= models.IntegerField(max_length=255, null=False)
    # شماره مرجع
    sh_m= models.IntegerField(max_length=255, null=False)
