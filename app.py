import streamlit as st
import pandas as pd
import requests
from msal import ConfidentialClientApplication
import plotly.express as px

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

@st.cache_data(ttl=600)
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

@st.cache_data(ttl=600)
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

# Récupération des utilisateurs
users = get_users(token)
df_users = pd.DataFrame(users)
df_users.columns = [col.lower() for col in df_users.columns]
for col in ["displayname", "mail", "userprincipalname"]:
    if col not in df_users.columns:
        df_users[col] = ""

# Input et bouton de recherche
search = st.text_input("Filtrer par nom ou email")
search_clicked = st.button("Recherche")

if search_clicked:
    if search:
        df_filtered = df_users[
            df_users["displayname"].str.contains(search, case=False, na=False) |
            df_users["mail"].str.contains(search, case=False, na=False)
        ]
    else:
        df_filtered = df_users.copy()
else:
    df_filtered = df_users.copy()

st.dataframe(df_filtered)

# -------------------
# Heatmap des rôles
# -------------------
if not df_filtered.empty:
    # Récupérer tous les rôles des utilisateurs filtrés
    roles_data = []
    for user_id, display_name in zip(df_filtered["userprincipalname"], df_filtered["displayname"]):
        roles = get_user_roles(token, user_id)
        for role in roles:
            role_name = role.get("appRoleId", role.get("id", "unknown"))
            roles_data.append({"user": display_name, "role": role_name})

    if roles_data:
        df_roles = pd.DataFrame(roles_data)
        # Créer un pivot pour la heatmap
        df_pivot = df_roles.assign(value=1).pivot_table(
            index="user", columns="role", values="value", fill_value=0
        )
        # Afficher avec plotly
        fig = px.imshow(
            df_pivot,
            labels=dict(x="Rôle", y="Utilisateur", color="Présence"),
            color_continuous_scale="Blues"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun rôle trouvé pour les utilisateurs filtrés")
else:
    st.info("Aucun utilisateur trouvé avec ce filtre")
