from setuptools import setup, find_packages

setup(
    name="datamigrator",
    version="0.1.0",
    description="Automated CSV and Excel to Database Migration Tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="DataMigrator Team",
    author_email="support@datamigrator.com",
    url="https://github.com/yourusername/datamigrator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.5.0",
        "SQLAlchemy>=2.0.0",
        "pymongo>=4.0.0",
        "psycopg2-binary>=2.9.0",
        "PyMySQL>=1.0.0",
        "pyodbc>=4.0.0",
        "openpyxl>=3.0.0",
        "xlrd>=2.0.0",
        "chardet>=5.0.0",
        "click>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "migrate-data=datamigrator.cli:main",
        ],
    },
) 