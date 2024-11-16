# -*- coding: utf-8 -*-
# !/usr/bin/env python

import io
import random
import sys
from base64 import b64encode
from io import BytesIO

import cv2
import numpy as np
import PIL.Image
import torch
import torchvision.transforms.functional as TF
import yaml
from diffusers import (AutoencoderKL, EulerAncestralDiscreteScheduler,
                       StableDiffusionXLAdapterPipeline, T2IAdapter)
from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for)
from flask_socketio import SocketIO
from deep_translator import GoogleTranslator


app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'apple'

socketio = SocketIO(app, cors_allowed_origins='*')

with open('style_list.yaml', 'r') as f:
    style_list = yaml.load(f, Loader=yaml.FullLoader)

styles = {k['name']: (k['prompt'], k['negative_prompt']) for k in style_list}
STYLE_NAMES = list(styles.keys())
DEFAULT_STYLE_NAME = '(스타일 없음)'

def translate(text:str)->str:
    translated = GoogleTranslator(source='auto', target='en').translate(text)
    return translated


def apply_style(style_name: str,
                positive: str,
                negative: str = '') -> tuple[str, str]:
    p, n = styles.get(style_name, styles[DEFAULT_STYLE_NAME])
    p=translate(p)
    n=translate(n)
    positive=translate(positive)
    return p.replace('{prompt}', positive), n + negative + ', extra digit, fewer digits, cropped, worst quality, low quality, glitch, deformed, mutated, ugly, disfigured ,Unnatural, complicated, not in the picture, unsolicited elements.'


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
if torch.cuda.is_available():
    model_id = 'stabilityai/stable-diffusion-xl-base-1.0'
    adapter = T2IAdapter.from_pretrained(
        'TencentARC/t2i-adapter-sketch-sdxl-1.0',
        torch_dtype=torch.float16,
        variant='fp16')
    scheduler = EulerAncestralDiscreteScheduler.from_pretrained(
        model_id, subfolder='scheduler')
    pipe = StableDiffusionXLAdapterPipeline.from_pretrained(
        model_id,
        vae=AutoencoderKL.from_pretrained('madebyollin/sdxl-vae-fp16-fix',
                                          torch_dtype=torch.float16),
        adapter=adapter,
        scheduler=scheduler,
        torch_dtype=torch.float16,
        variant='fp16',
    )
    pipe.to(device)
else:
    sys.exit(0)

MAX_SEED = np.iinfo(np.int32).max


def randomize_seed_fn(seed: int, randomize_seed: bool) -> int:
    if randomize_seed:
        seed = random.randint(0, MAX_SEED)
    return seed


def progress(step, timestep, latents):

    socketio.emit('datas', {
        'step': int(step),
        'timestep': int(timestep)
    },
                  namespace='/',
                  to=session['sid'])


def run(
    image: PIL.Image.Image,
    prompt: str,
    negative_prompt: str,
    style_name: str = DEFAULT_STYLE_NAME,
    num_steps: int = 25,
    guidance_scale: float = 5,
    adapter_conditioning_scale: float = 0.8,
    adapter_conditioning_factor: float = 0.8,
) -> str:
    image = image.convert('RGB')
    image = TF.to_tensor(image) > 0.5
    image = TF.to_pil_image(image.to(torch.float32))

    prompt, negative_prompt = apply_style(style_name, prompt, negative_prompt)
    seed = random.randint(1, MAX_SEED)
    generator = torch.Generator(device=device).manual_seed(seed)
    processed_img = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        image=image,
        num_inference_steps=num_steps,
        generator=generator,
        guidance_scale=guidance_scale,
        adapter_conditioning_scale=adapter_conditioning_scale,
        adapter_conditioning_factor=adapter_conditioning_factor,
        callback=progress,
        callback_steps=3).images[0]
    buffered = BytesIO()
    processed_img.save(buffered, format='JPEG')
    base64_img = b64encode(buffered.getvalue()).decode('utf-8')
    return base64_img


if __name__ == '__main__':

    @app.route('/')
    def root():
        return render_template('index.html', style_names=STYLE_NAMES)

    @socketio.on('upload_image', namespace='/')
    def handle_upload(data):



        sid = request.sid
        session['sid'] = sid

        contents = data['file']
        style_name = data.get('style','')
        prompt = data.get('prompt','')
        negative_prompt = data.get('negative_prompt', '')

        image = PIL.Image.open(io.BytesIO(contents))
        img_array = np.array(image)

        img = cv2.resize(img_array, (1024, 1024))
        edges = cv2.Canny(img, 80, 80)
        edges_image = PIL.Image.fromarray(edges.astype(np.uint8))

        base64_img = run(image=edges_image,
                         prompt=prompt,
                         negative_prompt=negative_prompt,
                         style_name=style_name)

        socketio.emit('datas', {
            'step': 25,
            'timestep': 0,
            'latents': base64_img
        },
                      namespace='/',
                      to=session['sid'])

    socketio.run(app, host='0.0.0.0', port=20004)
