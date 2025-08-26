import streamlit as st
import pandas as pd
import requests
from msal import ConfidentialClientApplication

# -------------------
# Config Azure AD
# -------------------
tenant_id = st.secrets["AZURE_TENANT_ID"]
client_id = st.secrets["AZURE_CLIENT_ID"]
client_secret = st.secrets["AZURE_CLIENT_SECRET"]

AUTHORITY = f"https://login.microsoftonline.com/{tenant_id }"

# -------------------
# Connexion à Microsoft Graph
# -------------------
def get_access_token():
    app = ConfidentialClientApplication(
        client_id, authority=AUTHORITY, client_credential=client_secret 
    )
    token_response = app.acquire_token_for_client(scopes=SCOPE)
    return token_response.get("access_token", None)

def get_users(token):
    url = "https://graph.microsoft.com/v1.0/users?$select=displayName,mail,userPrincipalName"
    headers = {"Authorization": f"Bearer {token}"}
    users = []
    while url:
        response = requests.get(url, headers=headers)
        data = response.json()
        users.extend(data.get("value", []))
        url = data.get("@odata.nextLink", None)
    return users

def get_user_roles(token, user_id):
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/appRoleAssignments"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    return response.json().get("value", [])

# -------------------
# Streamlit UI
# -------------------
st.title("Azure AD - Visualisation des utilisateurs et rôles")

token = get_access_token()
if not token:
    st.error("Impossible d'obtenir un token Azure AD")
    st.stop()

users = get_users(token)
df_users = pd.DataFrame(users)

# Filtrage par nom ou email
search = st.text_input("Filtrer par nom ou email")
if search:
    df_users = df_users[
        df_users["displayName"].str.contains(search, case=False) |
        df_users["mail"].str.contains(search, case=False)
    ]

st.dataframe(df_users)

# Voir les rôles d'un utilisateur sélectionné
selected_user = st.selectbox("Sélectionnez un utilisateur pour voir ses rôles", df_users["userPrincipalName"])
if selected_user:
    roles = get_user_roles(token, selected_user)
    if roles:
        roles_df = pd.DataFrame(roles)
        st.dataframe(roles_df)
    else:
        st.info("Cet utilisateur n'a aucun rôle attribué")
