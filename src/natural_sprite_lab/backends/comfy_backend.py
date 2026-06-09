from __future__ import annotations

import json
import random
import time
import urllib.parse
import urllib.request
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from natural_sprite_lab.backends.base import AnimationBackend
from natural_sprite_lab.models import AnimationSpec, GeneratedFrames
from natural_sprite_lab.utils.paths import frame_filename


class ComfyBackend(AnimationBackend):
    """Generate new frames with a local ComfyUI text-to-image workflow."""

    name = "comfy"

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:8188",
        checkpoint: str | None = None,
        width: int = 768,
        height: int = 768,
        steps: int = 24,
        cfg: float = 6.5,
        sampler: str = "dpmpp_2m",
        scheduler: str = "karras",
        seed: int | None = None,
        controlnet: str | None = None,
        controlnet_strength: float = 0.8,
        seed_step: int = 1,
        timeout_seconds: float = 240.0,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.checkpoint = checkpoint
        self.width = width
        self.height = height
        self.steps = steps
        self.cfg = cfg
        self.sampler = sampler
        self.scheduler = scheduler
        self.seed = seed if seed is not None else random.randint(1, 2**48)
        self.controlnet = controlnet
        self.controlnet_strength = controlnet_strength
        self.seed_step = seed_step
        self.timeout_seconds = timeout_seconds
        self.client_id = str(uuid.uuid4())

    def generate_frames(
        self,
        source_image: Path,
        spec: AnimationSpec,
        frames_dir: Path,
        retake: int = 1,
    ) -> GeneratedFrames:
        frames_dir.mkdir(parents=True, exist_ok=True)
        checkpoint = self.checkpoint or self._default_checkpoint()
        controlnet = self.controlnet
        prompt_pack = spec.prompt_pack or _fallback_prompt_pack(spec)
        frame_paths: list[Path] = []
        prompt_ids: list[str] = []
        pose_images: list[str] = []

        for index in range(spec.frame_count):
            item = prompt_pack[index % len(prompt_pack)]
            pose_image_name = None
            if controlnet:
                pose_image_name = self._upload_pose_image(spec, index)
                pose_images.append(pose_image_name)
            workflow = self._workflow(
                checkpoint=checkpoint,
                positive=str(item["positive"]),
                negative=str(item["negative"]),
                seed=self.seed + index * self.seed_step,
                prefix=f"natural_sprite_lab_{spec.character_id}_{spec.action.value}_{index:02d}",
                controlnet=controlnet,
                pose_image_name=pose_image_name,
            )
            prompt_id = self._queue_prompt(workflow)
            prompt_ids.append(prompt_id)
            image_bytes = self._wait_for_first_image(prompt_id)
            path = frames_dir / frame_filename(spec.character_id, spec.action.value, index, retake)
            _save_generated_frame(image_bytes, path)
            frame_paths.append(path)

        return GeneratedFrames(
            frame_paths=frame_paths,
            backend_name=self.name,
            backend_metadata={
                "description": "Generated new character frames through ComfyUI from director prompt_pack.",
                "server_url": self.server_url,
                "checkpoint": checkpoint,
                "controlnet": controlnet,
                "controlnet_strength": self.controlnet_strength,
                "seed": self.seed,
                "seed_step": self.seed_step,
                "prompt_ids": prompt_ids,
                "pose_images": pose_images,
                "source_image": str(source_image),
                "note": (
                    "Reference image is interpreted by the director. If controlnet is set, generated "
                    "pose maps constrain the requested motion."
                ),
            },
        )

    def _default_checkpoint(self) -> str:
        data = self._get_json("/object_info/CheckpointLoaderSimple")
        values = data["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        return values[0]

    def _workflow(
        self,
        checkpoint: str,
        positive: str,
        negative: str,
        seed: int,
        prefix: str,
        controlnet: str | None = None,
        pose_image_name: str | None = None,
    ) -> dict[str, Any]:
        workflow: dict[str, Any] = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": checkpoint},
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": ["1", 1], "text": positive},
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": ["1", 1], "text": negative},
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": self.width, "height": self.height, "batch_size": 1},
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                    "seed": seed,
                    "steps": self.steps,
                    "cfg": self.cfg,
                    "sampler_name": self.sampler,
                    "scheduler": self.scheduler,
                    "denoise": 1.0,
                },
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"images": ["6", 0], "filename_prefix": prefix},
            },
        }
        if controlnet and pose_image_name:
            workflow["8"] = {"class_type": "LoadImage", "inputs": {"image": pose_image_name}}
            workflow["9"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": controlnet}}
            workflow["10"] = {
                "class_type": "ControlNetApplyAdvanced",
                "inputs": {
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "control_net": ["9", 0],
                    "image": ["8", 0],
                    "strength": self.controlnet_strength,
                    "start_percent": 0.0,
                    "end_percent": 0.85,
                },
            }
            workflow["5"]["inputs"]["positive"] = ["10", 0]
            workflow["5"]["inputs"]["negative"] = ["10", 1]
        return workflow

    def _queue_prompt(self, workflow: dict[str, Any]) -> str:
        data = json.dumps({"prompt": workflow, "client_id": self.client_id}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.server_url}/prompt",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = self._open(request, timeout=30)
        payload = json.loads(response.decode("utf-8"))
        return str(payload["prompt_id"])

    def _wait_for_first_image(self, prompt_id: str) -> bytes:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            history = self._get_json(f"/history/{prompt_id}", timeout=15)
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                for output in outputs.values():
                    for image in output.get("images", []):
                        return self._download_image(image)
            time.sleep(1.0)
        raise TimeoutError(f"Timed out waiting for ComfyUI prompt: {prompt_id}")

    def _download_image(self, image: dict[str, Any]) -> bytes:
        query = urllib.parse.urlencode(
            {
                "filename": image["filename"],
                "subfolder": image.get("subfolder", ""),
                "type": image.get("type", "output"),
            }
        )
        request = urllib.request.Request(f"{self.server_url}/view?{query}", method="GET")
        return self._open(request, timeout=30)

    def _upload_pose_image(self, spec: AnimationSpec, index: int) -> str:
        image = _make_pose_image(spec, index, self.width, self.height)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        filename = f"natural_sprite_lab_pose_{self.client_id}_{index:02d}.png"
        body, content_type = _multipart_image("image", filename, buffer.getvalue())
        request = urllib.request.Request(
            f"{self.server_url}/upload/image",
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        response = json.loads(self._open(request, timeout=30).decode("utf-8"))
        return str(response.get("name") or filename)

    def _get_json(self, path: str, timeout: float = 30.0) -> dict[str, Any]:
        request = urllib.request.Request(f"{self.server_url}{path}", method="GET")
        return json.loads(self._open(request, timeout=timeout).decode("utf-8"))

    @staticmethod
    def _open(request: urllib.request.Request, timeout: float) -> bytes:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()


def _fallback_prompt_pack(spec: AnimationSpec) -> list[dict[str, Any]]:
    base = (
        "anime game sprite, full-body side-view walking animation frame, same character design, "
        "clean line art, soft cel shading, transparent or plain background"
    )
    negative = "low quality, blurry, bad anatomy, extra limbs, missing limbs, cropped feet, text, watermark"
    return [
        {
            "frame": index,
            "label": f"frame_{index:02d}",
            "positive": f"masterpiece, best quality, {base}, {spec.action.value} frame {index}",
            "negative": negative,
        }
        for index in range(spec.frame_count)
    ]


def _make_pose_image(spec: AnimationSpec, index: int, width: int, height: int) -> Image.Image:
    plan = spec.frame_plan[index % len(spec.frame_plan)] if spec.frame_plan else {}
    front = float(plan.get("front_leg_angle", 18))
    back = float(plan.get("back_leg_angle", -18))
    body_y = int(plan.get("body_y", 0))

    image = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    cx = width // 2
    head_y = int(height * 0.22) + body_y
    neck = (cx, head_y + int(height * 0.08))
    pelvis = (cx, int(height * 0.55) + body_y)
    shoulder_l = (cx - int(width * 0.08), neck[1] + int(height * 0.035))
    shoulder_r = (cx + int(width * 0.08), neck[1] + int(height * 0.035))
    hip_l = (cx - int(width * 0.045), pelvis[1])
    hip_r = (cx + int(width * 0.045), pelvis[1])

    left_forward = front < back
    left_leg = front if left_forward else back
    right_leg = back if left_forward else front
    left_arm = -right_leg * 0.75
    right_arm = -left_leg * 0.75
    if spec.action.value == "attack":
        left_arm = front * 1.2 + 18
        right_arm = front * 1.1 + 24
    elif spec.action.value == "hit":
        left_arm = -28
        right_arm = -24
        neck = (neck[0] - 18, neck[1])
    elif spec.action.value == "idle":
        left_arm *= 0.25
        right_arm *= 0.25
        left_leg *= 0.25
        right_leg *= 0.25

    left_knee, left_foot = _leg_points(hip_l, left_leg, height)
    right_knee, right_foot = _leg_points(hip_r, right_leg, height)
    left_elbow, left_hand = _arm_points(shoulder_l, left_arm, height, side=-1)
    right_elbow, right_hand = _arm_points(shoulder_r, right_arm, height, side=1)

    draw.ellipse((cx - 32, head_y - 32, cx + 32, head_y + 32), outline=(255, 255, 255), width=5)
    _draw_bone(draw, neck, pelvis, (255, 255, 255))
    _draw_bone(draw, shoulder_l, shoulder_r, (255, 255, 0))
    _draw_bone(draw, shoulder_l, left_elbow, (255, 0, 0))
    _draw_bone(draw, left_elbow, left_hand, (255, 128, 0))
    _draw_bone(draw, shoulder_r, right_elbow, (0, 255, 0))
    _draw_bone(draw, right_elbow, right_hand, (0, 255, 128))
    _draw_bone(draw, pelvis, hip_l, (0, 255, 255))
    _draw_bone(draw, pelvis, hip_r, (0, 128, 255))
    _draw_bone(draw, hip_l, left_knee, (0, 0, 255))
    _draw_bone(draw, left_knee, left_foot, (128, 0, 255))
    _draw_bone(draw, hip_r, right_knee, (255, 0, 255))
    _draw_bone(draw, right_knee, right_foot, (255, 0, 128))
    return image


def _leg_points(hip: tuple[int, int], angle: float, height: int) -> tuple[tuple[int, int], tuple[int, int]]:
    thigh = int(height * 0.19)
    shin = int(height * 0.20)
    knee = (hip[0] + int(angle * 1.2), hip[1] + thigh)
    foot = (knee[0] + int(angle * 1.7), knee[1] + shin)
    return knee, foot


def _arm_points(
    shoulder: tuple[int, int],
    angle: float,
    height: int,
    side: int,
) -> tuple[tuple[int, int], tuple[int, int]]:
    upper = int(height * 0.14)
    lower = int(height * 0.14)
    elbow = (shoulder[0] + int(angle * 0.9) + side * 8, shoulder[1] + upper)
    hand = (elbow[0] + int(angle * 0.8) + side * 6, elbow[1] + lower)
    return elbow, hand


def _draw_bone(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int]) -> None:
    draw.line([start, end], fill=color, width=6)
    r = 5
    draw.ellipse((start[0] - r, start[1] - r, start[0] + r, start[1] + r), fill=color)
    draw.ellipse((end[0] - r, end[1] - r, end[0] + r, end[1] + r), fill=color)


def _multipart_image(field_name: str, filename: str, data: bytes) -> tuple[bytes, str]:
    boundary = f"----natural-sprite-lab-{uuid.uuid4().hex}"
    chunks = [
        f"--{boundary}\r\n".encode("ascii"),
        (
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode("ascii"),
        data,
        f"\r\n--{boundary}--\r\n".encode("ascii"),
    ]
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _save_generated_frame(image_bytes: bytes, path: Path) -> None:
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    image = _remove_light_background(image)
    image.save(path)


def _remove_light_background(image: Image.Image, threshold: int = 14) -> Image.Image:
    width, height = image.size
    pixels = image.load()
    sample_points = [
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
        (width // 2, 0),
        (width // 2, height - 1),
    ]
    samples = [pixels[x, y] for x, y in sample_points]
    background = tuple(sum(sample[channel] for sample in samples) // len(samples) for channel in range(3))
    sample_spread = max(
        abs(sample[0] - background[0]) + abs(sample[1] - background[1]) + abs(sample[2] - background[2])
        for sample in samples
    )
    if sample_spread > 24:
        return image
    output = image.copy()
    output_pixels = output.load()
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            distance = abs(red - background[0]) + abs(green - background[1]) + abs(blue - background[2])
            if distance < threshold and min(red, green, blue) > 238:
                output_pixels[x, y] = (red, green, blue, 0)
    return output
