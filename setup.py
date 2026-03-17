from setuptools import setup, find_packages

setup(
    name="email-unsub-manager",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "python-dotenv",
        "rich",
        "beautifulsoup4",
    ],
    python_requires=">=3.10",
)
