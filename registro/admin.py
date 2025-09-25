from django.contrib import admin

from .models import (Funcionario, ColetaFaces, Treinamento)

class ColetaFacesInline(admin.StackedInline):
    model = ColetaFaces
    extra = 0

class FuncionarioAdmin(admin.ModelAdmin):
    readonly_fields = ['slug']
    readonly_fields = ['cpf']
    fields = ['nome', 'cpf', 'observacao', 'dataHora']
    inlines = (ColetaFacesInline,)

admin.site.register(Funcionario, FuncionarioAdmin)



# admin.site.register(Funcionario)
# admin.site.register(ColetaFaces)


admin.site.register(Treinamento)

