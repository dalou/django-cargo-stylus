from setuptools import setup, find_packages

setup(
    name="django-cargo-fontforge",
    version = "1.0",
    url='http://github.com/dalou/django-cargo-fontforge',
    license='BSD',
    platforms=['OS Independent'],
    description="[Cargo collections] Stylus utilities and watchers, include and wrap nib and shortcuts lib",
    setup_requires = [

    ],
    install_requires = [
        "django>=1.4",
        "pyinotify>=0.9.4",
        "stylus>=0.1.1"
    ],
    long_description=open('README.md').read(),
    author='Damien Autrusseau',
    author_email='autrusseau.damien@gmail.com',
    maintainer='Damien Autrusseau',
    maintainer_email='autrusseau.damien@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: Beta',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ]
)