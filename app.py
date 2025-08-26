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

# Initialiser la session_state pour la sélection
if "selected_user" not in st.session_state:
    st.session_state.selected_user = None

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

            # Data editor interactif
            selected_rows = st.data_editor(
                df_filtered[["displayname", "mail", "userprincipalname"]],
                column_config={
                    "displayname": st.column_config.TextColumn("Nom"),
                    "mail": st.column_config.TextColumn("Email"),
                    "userprincipalname": st.column_config.TextColumn("UPN"),
                },
                hide_index=True,
                key="user_table",
                disabled=True,
                on_change=None,
                use_container_width=True,
                num_rows="dynamic",
                select_rows=True,  # active la sélection
            )

            # Récupérer l'utilisateur sélectionné (la première ligne sélectionnée)
            if selected_rows.selected_rows:
                idx = selected_rows.selected_rows[0]
                st.session_state.selected_user = df_filtered.iloc[idx]["userprincipalname"]

# Affichage des rôles de l'utilisateur sélectionné
if st.session_state.selected_user:
    roles = get_user_roles(token, st.session_state.selected_user)
    if roles:
        roles_df = pd.DataFrame(roles)
        st.subheader(f"Rôles de {st.session_state.selected_user}")
        st.dataframe(roles_df)
    else:
        st.info(f"{st.session_state.selected_user} n'a aucun rôle attribué")
