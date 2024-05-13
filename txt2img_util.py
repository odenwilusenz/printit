import requests as r
import time, io
from PIL import Image
import toml

config = toml.load('.streamlit/secrets.toml')

headers = {
    "apikey": config['hordeAPi'],
    "Client-Agent": "mommy:6.9:daddy"
}



class txt2img:

    def __init__(self):
        self.negative_prompt = "nsfw, boobs, hentai, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, <bad_prompt>, missing arms, text error, long neck, fisheye lens, looking at viewer, cursed, cursed fingers, bad fingers, cursed eyes, bad eyes, bad face, cursed face"
        #self.prompt = "masterpiece, best quality, androgynous cyborg-elven sorcerer, casting a spell emerging from the staff and a sword, smart, light, cool, magic, magia, cloak, boy, long hair, fog, bloom, dramatic, wide lens, 4k, serious, angry, Science fiction, future, futuristic, futuristic clothes, time traveler, scientist, futuristic city"
        models_url = "https://raw.githubusercontent.com/db0/AI-Horde-image-model-reference/main/stable_diffusion.json"

        pass

    def start_generation(self, prompt):
        body = {
          "ModelGenerationInputStable": {
            "steps": 35,
            "karras": True,
            # "height": 512,
            # "width": 512,
            # "height": 768,
            # "width": 768,
            "height": 512,
            "width": 512,
          },
          "nsfw": True,
          "slow_workers": False,
          "prompt": f"{prompt} ### {self.negative_prompt}",
          "models": ["Deliberate"],
        }
    
        res = r.post("https://stablehorde.net/api/v2/generate/async", headers=headers, json=body)
        return res.json()
    
    
    def get_status(self, id):
        #https://stablehorde.net/api/v2/generate/check/7b8621e5-892a-4434-afdc-94e8ac0b66a9
        res = r.get(f"https://stablehorde.net/api/v2/generate/check/{id}", headers=headers)
        return res.json()
    
    def generate(self, prompt):
        generate_res = self.start_generation(prompt)
        id = generate_res.get("id")

        if id == None:
            print("yippie error")
            pass
        print(f"id={id}\nkudos={generate_res.get('kudos')}")
        res = self.get_status(id)
        done = res.get("done")
        while not done:
            time.sleep(1)
            res = self.get_status(id)
            done = res.get("done") and res.get("processing") == 0

        res = r.get(f"https://stablehorde.net/api/v2/generate/status/{id}", headers=headers)
        gens = res.json().get("generations")
        img_url = gens[0].get("img")
        print(img_url)
        img = r.get(img_url).content
        f = open(f"latest.webp","wb+")
        f.write(img)
        f.close()
        return Image.open(io.BytesIO(img))
        # return img

if __name__ == "__main__":
    txt2img.generate()