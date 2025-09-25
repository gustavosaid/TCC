from django import forms
from .models import Funcionario, ColetaFaces, RegistroEntrada
from django.utils import timezone
from django.core.exceptions import ValidationError
from .utils import validar_cpf # Importa a função de validação de CPF
import re


SETORES = [
    ('', 'Selecione um setor...'),  # Opção padrão
    ('Gab. Antonio Jorge (Toninho Cury)', 'Gab. Antonio Jorge (Toninho Cury)'),
    ('Gab. Brenda Evelly', 'Gab. Brenda Evelly'),
    ('Gab. Elizabeth (Profº Beth)', 'Gab. Elizabeth (Profº Beth)'),
    ('Gab. Ezequiel', 'Gab. Ezequiel'),
    ('Gab. Gladston', 'Gab. Gladston'),
    ('Gab. Itamar', 'Gab. Itamar'),
    ('Gab. Jõao Batista (Cabo Batista)', 'Gab. Jõao Batista (Cabo Batista)'),
    ('Gab. José Carlos (Carlito)', 'Gab. José Carlos (Carlito)'),
    ('Gab. José Eustáquio', 'Gab. José Eustáquio'),
    ('Gab. José Luiz', 'Gab. José Luiz'),
    ('Gab. Júlio César', 'Gab. Júlio César'),
    ('Gab. Leomar (Sgt Leomar)', 'Gab. Leomar (Sgt Leomar)'),
    ('Gab. Mauri (Mauri da JL)', 'Gab. Mauri (Mauri da JL)'),
    ('Gab. Otaviano', 'Gab. Otaviano'),
    ('Gab. Paulo Augusto (Paulinho)', 'Gab. Paulo Augusto (Paulinho)'),
    ('Gab. Paulo Henrique', 'Gab. Paulo Henrique'),
    ('Gab. Willian ', 'Gab. Willian '),
    ('Plenário ', 'Plenário'),
    ('Presidência', 'Presidência'),
]

class FuncionarioForm(forms.ModelForm):

    observacao = forms.ChoiceField(
        choices=SETORES,
        label='Destino', # Rótulo que aparecerá no formulário
        widget=forms.Select(attrs={
            'class': 'form-select' # Adiciona uma classe para estilização (ex: Bootstrap)
        })
    )

    class Meta:
        model = Funcionario
        fields = ['nome', 'cpf','observacao']
        widgets = {
            'nome': forms.TextInput(
                attrs={'placeholder': 'Digite o nome completo.'}
            ),
            'cpf': forms.TextInput(
                attrs={'placeholder': 'Digite o CPF.'}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
            
    def clean_observacao(self):
        return self.cleaned_data['observacao'].lower()
    
    #Validação do CPF
    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')  # Acessando corretamente o CPF

        # Remover caracteres não numéricos
        cpf = re.sub(r'\D', '', cpf)

        # Verifica se já existe um funcionário com esse CPF
        if Funcionario.objects.filter(cpf=cpf).exists():
            raise ValidationError("Funcionário já cadastrado.")

        # Verifica se o CPF é válido
        if not validar_cpf(cpf):
            raise ValidationError("CPF inválido. Digite um CPF válido.")
        return cpf


    def save(self, commit=True):
    #     """
    #     Sobrescreve o método save para definir a data e hora da modificação automaticamente.
    #     """
        instance = super().save(commit=False)
        instance.dataHora = timezone.now()
        if commit:
            instance.save()
        return instance

# Multiplos arquivos
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result

class ColetaFacesForm(forms.ModelForm):
    images = MultipleFileField()

    class Meta:
        model = ColetaFaces
        fields = ['images', 'observacao']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Não permite a edição da foto já cadastrada no funcionário
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'






class ColetaEntradaForms(forms.ModelForm):
    # 2. Substituímos a definição automática do campo 'gabinete'
    # por uma definição explícita, usando ChoiceField.
    gabinete = forms.ChoiceField(
        choices=SETORES,
        label='Setor de Destino',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }) # Usamos o widget 'Select' para criar o dropdown
    )

    class Meta:
        model = RegistroEntrada
        # O campo 'gabinete' continua listado aqui para que o ModelForm
        # saiba que deve salvá-lo no banco de dados.
        fields = ['gabinete']
