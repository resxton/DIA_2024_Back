from django.db import models

class Airplane(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    passenger_count = models.IntegerField()
    range = models.IntegerField()


    def __str__(self):
        return self.name