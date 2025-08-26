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

SCOPE = ["https://graph.microsoft.com/.default"]
AUTHORITY = f"https://login.microsoftonline.com/{tenant_id}"

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

# Normaliser les colonnes en minuscules
df_users.columns = [col.lower() for col in df_users.columns]

# S'assurer que les colonnes essentielles existent
for col in ["displayname", "mail", "userprincipalname"]:
    if col not in df_users.columns:
        df_users[col] = ""

# Input et bouton de recherche
search = st.text_input("Filtrer par nom ou email")
if st.button("Recherche"):
    if search:
        df_filtered = df_users[
            df_users["displayname"].str.contains(search, case=False, na=False) |
            df_users["mail"].str.contains(search, case=False, na=False)
        ]
    else:
        df_filtered = df_users.copy()

    st.dataframe(df_filtered)

    # Voir les rôles d'un utilisateur sélectionné
    if not df_filtered.empty:
        selected_user = st.selectbox(
            "Sélectionnez un utilisateur pour voir ses rôles", df_filtered["userprincipalname"]
        )
        if selected_user:
            roles = get_user_roles(token, selected_user)
            if roles:
                roles_df = pd.DataFrame(roles)
                st.dataframe(roles_df)
            else:
                st.info("Cet utilisateur n'a aucun rôle attribué")
    else:
        st.info("Aucun utilisateur trouvé avec ce filtre")
