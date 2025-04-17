
import base64
import os
import requests
from datetime import datetime
from actions.IActions import IAction
from typing import List, Dict, Any
from LocalConfigManager import LocalConfigManager
from openai import OpenAI

class ImageGen(IAction):
    modes = ["openai", "stable_diffusion"]
    def __init__(self, config_manager: LocalConfigManager, persona: str, query: str, conversation_history: List[Dict[str, Any]]):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.mode = self.modes[0]
        self.conversation_history = conversation_history
        if self.mode == self.modes[1]:
            self.stable_diffusion_config = config_manager.get_config().get_stable_diffusion_config()
            self.base_url = self.stable_diffusion_config.get("url", None)
            self.negative_prompt = self.stable_diffusion_config.get("negative_prompt", None)
            self.prompt = self.stable_diffusion_config.get("prompt", None)
            self.steps = self.stable_diffusion_config.get("steps", None)
            self.guidance_scale = self.stable_diffusion_config.get("guidance_scale", None)

    def getTools(self) -> List[tuple]:
        return [(self.generate_image, "generate_image", "Generate an image with a prompt", {"prompt": "<prompt to generate an image>"})]

    def context_template(self, image_path: str, prompt: str) -> str:
        return f"""
Here is the image that was generated:

[![{prompt}]({image_path} "Title")]({image_path})

Output the markdown for the image to the user exactly as shown above.
"""

    def context_template_error(self, error: str) -> str:
        return f"""
Image generation is unavailable at this time. Please try again later.

Inform the user that image generation is unavailable at this time.
"""

    def generate_image(self, arguments: Dict[str, Any]) -> str:
        yield ("system", "Generating image...")
        if self.mode == "openai":
            yield from self.generate_image_with_openai(arguments)
        elif self.mode == "stable_diffusion":
            yield from self.generate_image_with_stable_diffusion(arguments)

    def generate_image_with_openai(self, arguments: Dict[str, Any]) -> str:
        api_key = self.config_manager.get_config().get_ollama_api_key(self.persona)
        if not api_key:
            print("No API key found for OpenAI")
            yield ("result", self.context_template_error("Image generation is not available right now try again later"))
            return
        client = OpenAI(
            api_key=api_key
        )
        response = client.images.generate(
            model="dall-e-3",
            prompt=arguments["prompt"],
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        yield ("result", self.context_template(image_url, arguments["prompt"]))

    def generate_image_with_stable_diffusion(self, arguments: Dict[str, Any]) -> str:
        try:
            image_dir = os.path.join(self.config_manager.get_path("images"), self.persona)
            if not os.path.exists(image_dir):
                os.makedirs(image_dir)

            image_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            image_path = os.path.join(image_dir, image_name)
            url = self.base_url + "/sdapi/v1/txt2img"
            data = {
                "prompt": arguments["prompt"] + ", " + self.prompt,
                "negative_prompt": self.negative_prompt,
                "width": 1024,
                "height": 1024,
                "steps": self.steps,
                "cfg_scale": self.guidance_scale,
            }
            response = requests.post(url, json=data)
            response.raise_for_status()
            data = response.json()
            #base64 encoded image
            image_data64 = data["images"][0]
            #save to file
            with open(image_path, "wb") as f:
                f.write(base64.b64decode(image_data64))
            name = "/generated_images" + self.config_manager.get_http_path(self.persona + "/" + os.path.basename(image_path))
            yield ("result", self.context_template(name, arguments["prompt"]))
        except Exception as e:
            yield ("result", self.context_template_error(str(e)))

