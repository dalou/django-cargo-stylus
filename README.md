django-cargo-stylus
================

install : pip install django-cargo-stylus

configure django settings :

CARGO_STYLUS = {
    'watchers': [
        ('relative_or_absolute_input_stylus_file_path', 'relative_or_absolute_output_css_file_path'),
        ...

    ]
}


then run : python manage.py stylus_watcher

