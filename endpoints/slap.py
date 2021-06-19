from io import BytesIO

from PIL import Image
from flask import send_file

from utils import http
from utils.endpoint import Endpoint, setup


@setup
class Slap(Endpoint):
    params = ['avatar0', 'avatar1']

    def generate(self, avatars, kwargs):
        sprite = Image.open(self.assets.get('assets/petpet/hand.png')).resize((1000, 500)).convert('RGBA')
        avatar = http.get_image(avatars[0]).resize((200, 200)).convert('RGBA')
        sprite.paste(avatar, (580, 260), avatar)
        sprite = sprite.convert('RGB')

        images = []
        b = BytesIO()

        images[0].save(
            fp,
            "GIF",
            save_all=True,
            append_images=images[1:],
            loop=0,
            disposal=2,
        )

        for index in range(5):
            im = Image.new("RGBA", (100, 100), None)
            im.paste(avatars[0], (25, 25), avatars[0])
            im.paste(sprite, (0 - (112 * index), 0), sprite)
            images.append(im)
        sprite.close()

        b.seek(0)

        
        

        sprite.save(b, format='png')
        
        return send_file(b, mimetype='image/png')
