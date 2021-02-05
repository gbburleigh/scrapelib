from faker_schema.faker_schema import faker_schema
import datetime

schema = {'url':{'pkg_creation_stamp': \
            'date_time', 'title': 'text', 'post_date': 'date'\
            ,'edit_date': 'date', 'contributors': {'name': \
            'pytuple'}\
            ,'messages': {'name': 'pylist'}, \
            'moderated': 'pybool', 'update_version': 'pyint'}}

#nb_elements=2, value_types=[url, date]
#value_types=text