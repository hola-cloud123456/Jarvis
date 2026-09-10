# Reemplaza la función home() existente por esta:
@app.route("/")
def home():
    profile = load_user_profile()
    if profile:
        return f"¡Perfil cargado con éxito para {profile.get('user_info', {}).get('name')}!"
    return "ALERTA: profile.json NO encontrado o no se puede leer."
