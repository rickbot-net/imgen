from io import BytesIO

from flask import send_file
from wand import image
from PIL import Image, ImageDraw
from utils.textutils import render_text_with_emoji, wrap

from utils import http
from utils.endpoint import Endpoint, setup
from utils.exceptions import BadRequest


@setup
class Maidenless(Endpoint):
    params = ['text']

    def generate(self, avatars, text, usernames, kwargs):
        base = Image.open(self.assets.get('assets/maidenless/noBitches.png'))
        font = self.assets.get_font('assets/fonts/impact.ttf', size=50)
        canv = ImageDraw.Draw(base)
        render_text_with_emoji(base, canv, (155, 7), wrap(font, "lolololo", 220), font, 'white')

        base = base.convert('RGB')
        b = BytesIO()
        base.save(b, format='jpeg')
        b.seek(0)
        return send_file(b, mimetype='image/jpeg')
