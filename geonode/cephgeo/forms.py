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

from model_utils import Choices


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

    TITLE_CHOICES = Choices(
        ('muni', _('Municipality and Province')),
        ('rb', _('Riverbasin Floodplain')),
    )

    day_counter = forms.IntegerField(label='Update FHM within the last X days')

    title = forms.ChoiceField(choices=TITLE_CHOICES,
                              help_text='Replace title variables',
                              initial=TITLE_CHOICES.muni)

    rb_field = forms.CharField(
        initial='RB_FP',
        help_text='Column name of Riverbasin/Floodplain in FHM Coverage')

    fhm_coverage = forms.CharField(initial='fhm_coverage')

    style = forms.CharField(initial='fhm')

    suc_municipality_layer = forms.CharField(initial='pl1_suc_munis')

    abstract = forms.CharField(widget=forms.Textarea(
        attrs={'style': 'resize:none; width:100%; height:80%;', 'wrap': 'virtual'}),
        label='Abstract',
        help_text='Layer abstract. To replace variables with value, \
                                    enclose placeholders with \"##\" eg #year',
        initial="""This shapefile, with a resolution of #map_resolution# meters, \
        illustrates the inundation extents in the area if the actual \
        amount of rain exceeds that of a #flood_year# year-rain return period.

Note: There is a 1/#flood_year# (#flood_year_probability#%) probability of a \
flood with #flood_year# year return period occurring in a single year. \
The Rainfall Intesity Duration Frequency is #ridf#mm.

3 levels of hazard:
Low Hazard (YELLOW)
Height: 0.1m-0.5m

Medium Hazard (ORANGE)
Height: 0.5m-1.5m

High Hazard (RED)
Height: beyond 1.5m""")

    def __init__(self, *args, **kwargs):
        super(FhmMetadataForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset('FHM Metadata Update',
                     'day_counter',
                     'title',
                     Fieldset('Riverbasin Column',
                              Div(
                                  Field('rb_field', css_class=''),
                                  css_class='form-group'
                              ),
                              css_class='rb-fieldset'
                              ),

                     'fhm_coverage',
                     'style',
                     'suc_municipality_layer',
                     'abstract'
                     ),
            # Div(
            #     Field('day_counter', css_class=''),
            #     css_class='form-group'
            # ),
            # Div(
            #     Field('title', css_class=''),
            #     css_class='form-group'
            # ),
            # Div(
            #     Field('fhm_coverage', css_class=''),
            #     css_class='form-group'
            # ),
            # Div(
            #     Field('style', css_class=''),
            #     css_class='form-group'
            # ),
            # Div(
            #     Field('suc_municipality_layer', css_class=''),
            #     css_class='form-group'
            # ),
            # Div(
            #     Field('abstract', css_class=''),
            #     css_class='form-group'
            # ),

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
