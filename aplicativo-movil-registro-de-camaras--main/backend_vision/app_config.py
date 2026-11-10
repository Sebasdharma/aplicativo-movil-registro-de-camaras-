import os


class FlaskConfig:
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0
    MAX_CONTENT_LENGTH = 12 * 1024 * 1024

    MICROSOFT_TENANT_ID = os.environ.get(
        "MICROSOFT_TENANT_ID",
        "0a42bec9-732b-45d1-977d-3b8d3ac98c2b",
    )
    MICROSOFT_CLIENT_ID = os.environ.get(
        "MICROSOFT_CLIENT_ID",
        "6a39d754-3c15-4599-b074-3925b7c7e77e",
    )
