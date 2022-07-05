from setuptools import setup

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name='strata-cli',
    version='0.1.1',
    description='The easy way to ship Stan models',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/ankane/strata',
    author='Andrew Kane',
    author_email='andrew@ankane.org',
    license='BSD-3-Clause',
    packages=['strata'],
    entry_points={
        'console_scripts': [
            'strata=strata:main'
        ]
    },
    # for ubuntu-16.04
    python_requires='>=3.5',
    install_requires=[],
    include_package_data=True,
    zip_safe=False
)
