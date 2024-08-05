import firebase_admin # type: ignore
from firebase_admin import credentials, auth  # type: ignore

cred = credentials.Certificate("C:/Users/drkir/Downloads/pdfai-a4d51-firebase-adminsdk-evca6-510c6c3a14.json")
firebase_admin.initialize_app(cred)