import geonode.settings as settings
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Button, \
    Div, Field
from crispy_forms.bootstrap import FormActions

from geonode.layers.models import Layer, Style
from geoserver.catalog import Catalog


class DataInputForm(forms.Form):
    data = forms.CharField(widget=forms.Textarea(
        attrs={'style': 'resize:none; width:100%; height:60%;', 'wrap': 'virtual'}))
    update_grid = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Metadata output from bulk_upload.py:',
                'data',
                'update_grid',
            ),
            ButtonHolder(
                Submit('submit', 'Submit', css_class='button white')
            )
        )
        super(DataInputForm, self).__init__(*args, **kwargs)
        self.fields['update_grid'].initial = True


class RequestDataClassForm(forms.Form):
    LAZ = forms.BooleanField()
    DEM = forms.BooleanField()
    DSM = forms.BooleanField()
    DTM = forms.BooleanField()
    Orthophoto = forms.BooleanField()

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Choose which data to download :',
                'LAZ',
                'DEM',
                'DSM',
                'DTM',
                'Orthophoto',
            ),
            FormActions(
                Submit('submit', 'Create FTP Folder',
                       css_class='button white'),
                Button('clear', 'Remove All Items', css_class='button white')
            )
        )
        super(RequestDataClassForm, self).__init__(*args, **kwargs)


class FhmMetadataForm(forms.Form):
    date_field = forms.DateField(
        widget=forms.TextInput(
            attrs={'type': 'date'}
        )
    )
    fhm_coverage_name = forms.CharField(initial='fhm_coverage')
    style_template = forms.CharField(initial='fhm')
    suc_muni_layer = forms.CharField(initial='pl1_suc_munis')

    def __init__(self, *args, **kwargs):

        super(FhmMetadataForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                'date_field',
                'fhm_coverage_name',
                'style_template',
                'suc_muni_layer',
            ),
            FormActions(
                Submit('submit', 'Submit', css_class='button white'),
            )
        )


# class UpdateMetadataForm(forms.Form):
#     date_field = forms.DateField(
#         widget=forms.TextInput(
#             attrs={'type': 'date', 'style': 'width:50%'}
#         )
#     )
#     fhm_coverage_name = forms.CharField(
#         help_text='FHM Coverage Layer Name', initial='fhm_coverage')
#     style_template = forms.CharField(initial='fhm', help_text='SLD Name')
#     suc_muni_layer = forms.CharField(
#         initial='pl1_suc_munis', help_text='Layer Name of SUC Municipal Boundary')
#     CHOICES = (('1', 'Update Flood Hazard Map Metadata + SUC/FP Tag'),
#                ('2', 'Update Resource Layer Metadata'),
#                ('3', 'Update SAR DEM Metadata'),
#                ('4', 'Tag FHM w SUC and FP'))
#     choice_field = forms.ChoiceField(
#         widget=forms.RadioSelect, choices=CHOICES, label='Metadata Update')

#     def __init__(self, *args, **kwargs):

#         super(UpdateMetadataForm, self).__init__(*args, **kwargs)

#         self.helper = FormHelper()
#         self.helper.layout = Layout(
#             Fieldset(
#                 '',
#                 Div(
#                     Field('choice_field', css_class='form-control'),
#                     Div(
#                         Field('date_field', css_class='form-control'),
#                         # Field('fhm_coverage_name', css_class='form-control'),
#                         # Field('style_template', css_class='form-control'),
#                         # Field('suc_muni_layer', css_class='form-control'),
#                         style='display:none',
#                         # css_id='div1'
#                     ),
#                     css_id='update-metadata',
#                 ),
#             ),
#             FormActions(
#                 Submit('submit', 'Submit', css_class='button white'),
#             )
#         )

class FhmMetadataForm(forms.Form):
    day_counter = forms.IntegerField(label='Update FHM within the last X days')
    fhm_coverage = forms.CharField(initial='fhm_coverage')
    style = forms.CharField(initial='fhm')
    suc_municipality_layer = forms.CharField(initial='pl1_suc_munis')
    abstract = forms.CharField(widget=forms.Textarea(
        attrs={'style': 'resize:none; width:100%; height:60%;', 'wrap': 'virtual'}),
        label='Abstract', help_text='Layer abstract. To replace variables with value, \
                                    enclose placeholders with # eg #year#')

    def __init__(self, *args, **kwargs):
        super(FhmMetadataForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                'day_counter',
                'fhm_coverage',
                'style',
                'suc_municipality_layer',
                'abstract',
            ),
            FormActions(
                Submit('submit', 'Update metadata', css_class='button white')
            )
        )

    # check if layer exists
    def clean_fhm_coverage(self):
        fhm_coverage = self.cleaned_data['fhm_coverage']
        cat = Catalog(settings.OGC_SERVER['default']['LOCATION'] + 'rest',
                      username=settings.OGC_SERVER['default']['USER'],
                      password=settings.OGC_SERVER['default']['PASSWORD'])
        if not Layer.objects.get(name=fhm_coverage):
            raise forms.ValidationError(
                _('Layer does not exist in geonode! Upload layer first %(value)s'), params={'value': fhm_coverage},)
        if not cat.get_layer(fhm_coverage):
            raise forms.ValidationError(
                _('Layer does not exist in geoserver! Upload layer first %(value)s'), params={'value': fhm_coverage},)

        return self.cleaned_data.get('fhm_coverage', '')

    def clean_style(self):
        cat = Catalog(settings.OGC_SERVER['default']['LOCATION'] + 'rest',
                      username=settings.OGC_SERVER['default']['USER'],
                      password=settings.OGC_SERVER['default']['PASSWORD'])
        style = self.cleaned_data['style']
        if not Style.objects.get(name=style):
            raise forms.ValidationError(
                _('Style not found in geonode! Upload style first %(value)s'), params={'value': style},)
        if not cat.get_style(style):
            raise forms.ValidationError(
                _('Style not found in geoserver! Upload style first %(value)s'), params={'value': style},)

        return self.cleaned_data.get('style', '')

    def clean_suc_municipality_layer(self):
        cat = Catalog(settings.OGC_SERVER['default']['LOCATION'] + 'rest',
                      username=settings.OGC_SERVER['default']['USER'],
                      password=settings.OGC_SERVER['default']['PASSWORD'])
        suc_municipality_layer = self.cleaned_data['suc_municipality_layer']
        if not Layer.objects.get(name=suc_municipality_layer):
            raise forms.ValidationError(
                _('Layer does not exist in geonode!: %(value)s'), params={'value': suc_municipality_layer},)
        if not cat.get_layer(suc_municipality_layer):
            raise forms.ValidationError(
                _('Layer does not exist in geoserver!: %(value)s'), params={'value': suc_municipality_layer},)

        return self.cleaned_data.get('suc_municipality_layer', '')
