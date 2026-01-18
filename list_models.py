import os
from dotenv import load_dotenv
from google import genai

def list_gemini_models():
    """
    Lista todos os modelos Gemini disponíveis para sua API Key.
    """
    # 1. Carrega a API Key do arquivo .env
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("❌ Erro: GOOGLE_API_KEY não encontrada. Verifique seu arquivo .env")
        return

    try:
        # 2. Inicializa o cliente (mesma lógica do seu brain.py)
        client = genai.Client(api_key=api_key)
        
        print(f"\n{'='*60}")
        print(f"{'MODEL ID':<35} | {'DISPLAY NAME'}")
        print(f"{'='*60}")

        # 3. Busca e itera sobre os modelos
        # O método client.models.list() retorna um iterável de objetos Model
        for model in client.models.list():
            # Filtramos para mostrar apenas os modelos 'gemini' que servem para geração
            if "gemini" in model.name:
                display_name = getattr(model, 'display_name', 'N/A')
                print(f"{model.name:<35} | {display_name}")

        print(f"{'='*60}\n")

    except Exception as e:
        print(f"❌ Falha ao conectar na API do Google: {e}")

if __name__ == "__main__":
    list_gemini_models()