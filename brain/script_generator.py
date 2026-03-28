# brain/script_generator.py
from google import genai
import sys
import os

# Panggil config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Inisialisasi Client baru dengan API Key
client = genai.Client(api_key=config.GEMINI_API_KEY)

def generate_viral_script(idea):
    prompt = f"""
    Kamu adalah copywriter TikTok/Reels profesional. 
    Buatkan 1 script video pendek (durasi 15-20 detik) berdasarkan ide ini: "{idea}"
    
    Target audiens: Karyawan dengan gaji 3-10 juta yang uangnya selalu habis sebelum tanggal 20.
    
    Gunakan format ini secara ketat:
    [HOOK] : Kalimat pertama yang brutal/nyelekit (Pain attack).
    [RELATE] : 1-2 kalimat yang bikin mereka merasa "ini gue banget".
    [SOLUSI] : Kenalkan Jatahku (Sistem uang harian tanpa ribet via Telegram @JatahkuBot).
    [CTA] : Ajak klik link di bio untuk coba gratis sekarang.
    
    Jangan berikan salam atau penjelasan, langsung berikan output script-nya saja.
    """
    
    try:
        # Menggunakan model flash terbaru via SDK baru
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"❌ Error API: {e}"

# Untuk testing manual
if __name__ == "__main__":
    test_idea = "Gaji 5 juta tapi tiap hari ngopi 50rb"
    print("Memicu otak AI...\n")
    hasil = generate_viral_script(test_idea)
    print(hasil)
