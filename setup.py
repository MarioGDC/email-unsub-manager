from setuptools import setup, find_packages

setup(
    name="email-unsub-manager",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-auth",
        "google-auth-oauthlib",
        "google-auth-httplib2",
        "google-api-python-client",
        "msal",
        "requests",
        "python-dotenv",
        "rich",
        "beautifulsoup4",
    ],
    python_requires=">=3.10",
)
