from django import forms
from crispy_forms.helper import FormHelper as helper
from crispy_forms.layout import Layout, Fieldset, Div, Field, Submit, ButtonHolder
from crispy_forms.bootstrap import FormActions
from .models import AutomationJob
from django.core.urlresolvers import reverse
from model_utils import Choices
from django.utils.translation import ugettext_lazy as _
from geonode.cephgeo.models import DataClassification
from django_enumfield import enum
from geonode.cephgeo.utils import copy_model_instance


class MetaDataJobForm(forms.ModelForm):

    class Meta:
        model = AutomationJob
        fields = ['input_dir', 'output_dir', 'datatype', 'processor', 'target_os']

    # datatype = forms.ModelChoiceField(
    #    queryset=AutomationJob.objects.all()
    # )

    def __init__(self, *args, **kwargs):
        super(MetaDataJobForm, self).__init__(*args, **kwargs)
        self.helper = helper()
        self.helper.form_method = 'post'
        self.helper.field_class = 'col-md-6 col-md-offset-1'
        self.helper.layout = Layout(
            Fieldset('',
                     Div(
                         Field('input_dir', css_class='form-control'),
                         Field('output_dir', css_class='form-control'),

                     ),
                     Div(

                         Field('datatype'),
                         Field('processor'),
                         Field('target_os'),
                     ),
                     ),
            ButtonHolder(
                Submit('submit', 'Submit')
            )
        )
        # self.helper.add_input(Submit('submit', 'Submit'))


# datatype
# input directory
# processor

class DemJobForm(forms.ModelForm):

    class Meta:
        model = AutomationJob
        fields = ['dem_name', 'lidar_blocks', 'input_dir', 'output_dir', 'datatype', 'processor', 'target_os']
        
    dem_name        = forms.CharField(widget=forms.TextInput(attrs={'style' : 'resize:none; size:40;', 'wrap' : 'virtual'}),
                                                             label='DEM Name',
                                                             help_text='Official name for the DEM')
    lidar_blocks    = forms.CharField(widget=forms.Textarea(attrs={'style' : 'resize:none; width:100%; height:20%;', 'wrap' : 'virtual'}),
                                                             label='LiDAR Blocks for this DEM',
                                                             help_text='Comma separated values of the LiDAR Block Names contained in this DEM.\
                                                             NOTE: DO NOT include spaces within names, they will be edited out. Use underscores instead.')
    
    # datatype = forms.ModelChoiceField(
    #    queryset=AutomationJob.objects.all()
    # )

    def __init__(self, *args, **kwargs):
        super(DemJobForm, self).__init__(*args, **kwargs)
        self.helper = helper()
        self.helper.form_method = 'post'
        self.helper.field_class = 'col-md-6 col-md-offset-1'
        self.helper.layout = Layout(
            Fieldset('',
                     Div(
                         Field('dem_name', css_class='form-control'),
                         Field('lidar_blocks', css_class='form-control'),
                         Field('input_dir', css_class='form-control'),
                         Field('output_dir', css_class='form-control'),

                     ),
                     Div(

                         Field('datatype'),
                         Field('processor'),
                         Field('target_os'),
                     ),
                     ),
            ButtonHolder(
                Submit('submit', 'Submit')
            )
        )
    
    def save(self, commit=True, *args, **kwargs):
        m = super(DemJobForm, self).save(commit=False, *args, **kwargs)
        
        """
        results = []
        for cr in self.callResult:
            for c in self.campain:
                for ct in self.callType:
                    m_new = copy_model_instance(m)
                    m_new.callResult = cr
                    m_new.campaign = c
                    m_new.calltype = ct
                    if commit:
                        m_new.save()
                    results.append(m_new)
        return results
        # self.helper.add_input(Submit('submit', 'Submit'))
        """
