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

# Input et bouton de recherche
search = st.text_input("Filtrer par nom, email ou UPN")
search_clicked = st.button("Recherche")

# Initialiser la session_state pour l'utilisateur sélectionné
if "selected_user" not in st.session_state:
    st.session_state.selected_user = None

# --- Recherche ---
if search_clicked:
    with st.spinner("Chargement des utilisateurs..."):
        users = get_users(token)
        df_users = pd.DataFrame(users)
        df_users.columns = [col.lower() for col in df_users.columns]
        for col in ["displayname", "mail", "userprincipalname"]:
            if col not in df_users.columns:
                df_users[col] = ""

        # Filtrage sur displayName, mail et userPrincipalName
        if search:
            df_filtered = df_users[
                df_users["displayname"].str.contains(search, case=False, na=False) |
                df_users["mail"].str.contains(search, case=False, na=False) |
                df_users["userprincipalname"].str.contains(search, case=False, na=False)
            ]
        else:
            df_filtered = df_users.copy()

        if df_filtered.empty:
            st.info("Aucun utilisateur trouvé avec ce filtre")
        else:
            st.subheader("Résultats de la recherche")

            # Tableau avec bouton "Voir les rôles" pour chaque utilisateur
            for idx, row in df_filtered.iterrows():
                cols = st.columns([4, 4, 3, 2])
                cols[0].write(row["displayname"])
                cols[1].write(row["mail"])
                cols[2].write(row["userprincipalname"])
                if cols[3].button("Voir les rôles", key=row["userprincipalname"]):
                    st.session_state.selected_user = row["userprincipalname"]

# --- Affichage des rôles ---
if st.session_state.selected_user:
    roles = get_user_roles(token, st.session_state.selected_user)
    if roles:
        roles_df = pd.DataFrame(roles)
        st.subheader(f"Rôles de {st.session_state.selected_user}")
        st.dataframe(roles_df)
    else:
        st.info(f"{st.session_state.selected_user} n'a aucun rôle attribué")
