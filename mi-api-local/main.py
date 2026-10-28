# `main.py` — API local de Kiru


import time
import json
import threading

import torch
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TextIteratorStreamer,
)

# ============================================================
# CONFIGURACIÓN DE LA API
# ============================================================

app = FastAPI(
    title="Kiru API",
    version="1.6.1",
    description="API local de Kiru compatible con Open WebUI y n8n, utilizando Qwen 2.5 1.5B en CPU."
)

# Ruta real del modelo en Hugging Face.
# Si el modelo está descargado localmente, también puedes
# utilizar la ruta local de sus archivos.
MODEL_PATH = "Qwen/Qwen2.5-1.5B-Instruct"

# Nombre público que utilizarán Kiru, Open WebUI y n8n.
MODEL_NAME = "kiru-model"

# ============================================================
# CARGA DEL MODELO: UNA SOLA VEZ
# ============================================================

print(f"⌛ Cargando tokenizador: {MODEL_PATH}")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

print(f"⌛ Cargando modelo {MODEL_PATH} en CPU...")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
)

model = model.to("cpu")# type: ignore
model.eval()

# Evitar errores si el tokenizador no tiene pad_token configurado.
if tokenizer.pad_token_id is None:
    tokenizer.pad_token = tokenizer.eos_token

print("✅ Modelo cargado correctamente.")
print(f"✅ Nombre público del modelo: {MODEL_NAME}")

# ============================================================
# AUTENTICACIÓN POR API KEY
# ============================================================

security = HTTPBearer(auto_error=False)

# Debe coincidir con la clave configurada en Open WebUI y n8n.
# Cámbiala por una clave privada antes de exponer la API
# a otras máquinas o a Internet.
VALID_API_KEY: Optional[str] = "sk-kiru-12345"


async def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        security
    ),
):
    """Verifica el token Bearer enviado por el cliente."""

    if VALID_API_KEY is not None:
        if (
            credentials is None
            or credentials.credentials != VALID_API_KEY
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key inválida o no proporcionada",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return True


# ============================================================
# MODELO DE DATOS DE LAS PETICIONES
# ============================================================

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = MODEL_NAME
    messages: Optional[List[Dict[str, Any]]] = None
    prompt: Optional[Any] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False

    class Config:
        extra = "allow"


# ============================================================
# REGISTRO DE PETICIONES
# ============================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(
        f"📥 [REQUEST] {request.method} "
        f"{request.url.path}"
    )

    try:
        response = await call_next(request)
        print(
            f"📤 [RESPONSE] Status: {response.status_code}"
        )
        return response

    except Exception as exc:
        print(f"❌ Error HTTP: {exc}")
        raise


# ============================================================
# ENDPOINT RAÍZ
# ============================================================

@app.get("/")
async def root_ping():
    return {
        "status": "online",
        "message": "API Local Kiru / Qwen en ejecución",
        "model": MODEL_NAME,
    }


# ============================================================
# LISTADO DE MODELOS
# ============================================================

@app.get("/models", dependencies=[Depends(verify_api_key)])
@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local",
            }
        ],
    }


# ============================================================
# GENERACIÓN DE TEXTO
# ============================================================

@app.post("/", dependencies=[Depends(verify_api_key)])
@app.post("/v1", dependencies=[Depends(verify_api_key)])
@app.post("/api/generate", dependencies=[Depends(verify_api_key)])
@app.post("/api/chat", dependencies=[Depends(verify_api_key)])
@app.post("/responses", dependencies=[Depends(verify_api_key)])
@app.post("/v1/responses", dependencies=[Depends(verify_api_key)])
@app.post("/chat/completions", dependencies=[Depends(verify_api_key)])
@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def create_chat_completion(
    request: ChatCompletionRequest,
):
    try:
        # ----------------------------------------------------
        # PREPARAR MENSAJES
        # ----------------------------------------------------

        formatted_messages = []

        if request.messages:
            for message in request.messages:
                role = message.get("role", "user")
                content = message.get("content", "")

                # Compatibilidad básica con contenidos que llegan
                # como listas de bloques de texto.
                if isinstance(content, list):
                    parts = []

                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                parts.append(
                                    str(item.get("text", ""))
                                )
                        else:
                            parts.append(str(item))

                    content = "\n".join(parts)

                formatted_messages.append(
                    {
                        "role": role,
                        "content": str(content),
                    }
                )

        elif request.prompt:
            if isinstance(request.prompt, list):
                content = " ".join(
                    str(part) for part in request.prompt
                )
            else:
                content = str(request.prompt)

            formatted_messages.append(
                {
                    "role": "user",
                    "content": content,
                }
            )

        else:
            formatted_messages.append(
                {
                    "role": "user",
                    "content": "Hola",
                }
            )

        # ----------------------------------------------------
        # VALIDAR PARÁMETROS
        # ----------------------------------------------------

        temperature = (
            request.temperature
            if request.temperature is not None
            else 0.7
        )

        if not 0 <= temperature <= 2:
            raise HTTPException(
                status_code=400,
                detail="temperature debe estar entre 0 y 2",
            )

        max_tokens = (
            request.max_tokens
            if request.max_tokens is not None
            else 512
        )

        if not 1 <= max_tokens <= 4096:
            raise HTTPException(
                status_code=400,
                detail="max_tokens debe estar entre 1 y 4096",
            )

        is_stream = bool(request.stream)

        # ----------------------------------------------------
        # CONSTRUIR ENTRADA DEL MODELO
        # ----------------------------------------------------

        text_prompt = tokenizer.apply_chat_template(
            formatted_messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = tokenizer(
            [text_prompt],
            return_tensors="pt",
        ).to("cpu")

        input_token_len = inputs.input_ids.shape[1]

        generation_kwargs = {
            **inputs,
            "max_new_tokens": max_tokens,
            "do_sample": temperature > 0,
            "pad_token_id": tokenizer.pad_token_id,
            "eos_token_id": tokenizer.eos_token_id,
        }

        if temperature > 0:
            generation_kwargs["temperature"] = temperature

        # ----------------------------------------------------
        # RESPUESTA EN STREAMING: SSE
        # ----------------------------------------------------

        if is_stream:
            streamer = TextIteratorStreamer(
                tokenizer,
                skip_prompt=True,
                skip_special_tokens=True,
            )

            generation_kwargs["streamer"] = streamer

            def run_generation():
                try:
                    with torch.inference_mode():
                        model.generate(**generation_kwargs)# type: ignore
                except Exception as exc:
                    print(
                        f"❌ Error en generación streaming: {exc}"
                    )
                    # Desbloquear el iterador si la generación falla.
                    streamer.end()

            thread = threading.Thread(
                target=run_generation,
                daemon=True,
            )
            thread.start()

            async def generate_stream():
                chunk_id = f"chatcmpl-{int(time.time())}"

                for new_text in streamer:
                    if not new_text:
                        continue

                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model or MODEL_NAME,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "content": new_text,
                                },
                                "finish_reason": None,
                            }
                        ],
                    }

                    yield (
                        f"data: {json.dumps(chunk, ensure_ascii=False)}"
                        "\n\n"
                    )

                final_chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model or MODEL_NAME,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }

                yield (
                    f"data: {json.dumps(final_chunk, ensure_ascii=False)}"
                    "\n\n"
                )
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )

        # ----------------------------------------------------
        # RESPUESTA NORMAL: JSON
        # ----------------------------------------------------

        with torch.inference_mode():
            outputs = model.generate(**generation_kwargs)# type: ignore

        generated_ids = outputs[0][input_token_len:]

        response_text = tokenizer.decode(
            generated_ids,
            skip_special_tokens=True,
        )

        output_token_len = len(generated_ids)

        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model or MODEL_NAME,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": input_token_len,
                "completion_tokens": output_token_len,
                "total_tokens": (
                    input_token_len + output_token_len
                ),
            },
        }

    except HTTPException:
        raise

    except Exception as exc:
        print(f"❌ Error en generación: {exc}")

        raise HTTPException(
            status_code=500,
            detail="Error interno durante la generación de texto",
        )


# ============================================================
# COMPROBACIÓN DE SALUD
# ============================================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": MODEL_NAME,
    }

