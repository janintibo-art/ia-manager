"""Streaming HTTP annulable, y compris avant les en-têtes et entre deux tokens."""
import asyncio
import json
import time
import httpx


async def ollama_options(client, model, ref):
    from src.backend import model_options as mo, providers as pv
    from src.backend.system_analyzer import SystemAnalyzer, detect_gpu
    meta = mo._meta_cache.get(model)
    if meta is None:
        meta = {"size_gb": 0.0, "layers": 0, "max_ctx": 0}
        try:
            tags = await client.get(pv.OLLAMA_URL + "/api/tags", timeout=10)
            tags.raise_for_status()
            for item in tags.json().get("models", []):
                if model in (item.get("name"), item.get("model")):
                    meta["size_gb"] = item.get("size", 0) / 1024**3
            info = await client.post(pv.OLLAMA_URL + "/api/show", json={"model": model}, timeout=10)
            info.raise_for_status()
            for key, value in (info.json().get("model_info") or {}).items():
                if key.endswith(".block_count") and isinstance(value, int):
                    meta["layers"] = value
                if key.endswith(".context_length") and isinstance(value, int):
                    meta["max_ctx"] = value
            if meta["size_gb"]:
                mo._meta_cache[model] = meta
        except (httpx.HTTPError, ValueError):
            pass
    # Ne pas lancer nvidia-smi/PowerShell pendant un échange annulable.
    hardware = SystemAnalyzer.get_system_info() if detect_gpu.cache_info().currsize else None
    options = mo.get_options(ref)
    if hardware is None and options.get("gpu_layers", -1) < 0:
        options["mode"] = "auto"
    plan = mo.plan(options, meta, hardware)
    result = {"temperature": plan["temperature"]}
    if plan["num_ctx"]:
        result["num_ctx"] = plan["num_ctx"]
    if plan["num_gpu"] is not None:
        result["num_gpu"] = plan["num_gpu"]
    return result


def stream(ref, messages, system="", on_token=None, should_stop=None):
    from src.backend import providers as pv
    on_token = on_token or (lambda text: None)
    should_stop = should_stop or (lambda: False)
    pid, model = pv.split_ref(ref)
    parts, stats = [], {"stopped": False}
    started = time.perf_counter()
    first = None

    def emit(text):
        nonlocal first
        if text:
            first = first or time.perf_counter()
            parts.append(text)
            on_token(text)

    async def request():
        async with httpx.AsyncClient(timeout=httpx.Timeout(900, connect=10), follow_redirects=False) as client:
            if pid == "ollama":
                stats["options"] = await ollama_options(client, model, ref)
                body = {"model": model, "messages": pv._ollama_payload(messages, system),
                        "stream": True, "options": stats["options"]}
                url, headers, kind, name = pv.OLLAMA_URL + "/api/chat", {}, "ollama", "Ollama"
            else:
                provider = pv.get_provider(pid)
                if not provider or not pv.is_configured(provider):
                    raise ValueError(f"Fournisseur {pid} absent ou non configuré.")
                kind, name = provider["kind"], provider["name"]
                base, headers = provider["base_url"].rstrip("/"), pv._headers(provider)
                if kind == "anthropic":
                    body = {"model": model, "max_tokens": 8192, "stream": True,
                            "messages": pv._anthropic_messages(messages)}
                    if system.strip():
                        body["system"] = system
                    url = base + "/messages"
                else:
                    body = {"model": model, "stream": True, "messages": pv._openai_messages(messages, system)}
                    url = base + "/chat/completions"
            async with client.stream("POST", url, headers=headers, json=body) as response:
                if response.status_code != 200:
                    raise ValueError(f"{name} : HTTP {response.status_code}")
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if kind != "ollama":
                        if not line.startswith("data:"):
                            continue
                        line = line[5:].strip()
                        if line == "[DONE]":
                            break
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if event.get("error"):
                        raise ValueError(f"{name} : {event['error']}")
                    if kind == "ollama":
                        emit((event.get("message") or {}).get("content", ""))
                        if event.get("done"):
                            count, duration = event.get("eval_count"), event.get("eval_duration")
                            if count and duration:
                                stats.update(tokens=count, tokens_per_s=count/(duration/1e9))
                            break
                    elif kind == "anthropic":
                        if event.get("type") == "content_block_delta":
                            emit((event.get("delta") or {}).get("text", ""))
                        elif event.get("type") == "message_delta":
                            stats["tokens"] = (event.get("usage") or {}).get("output_tokens")
                        elif event.get("type") == "message_stop":
                            break
                    else:
                        choices = event.get("choices") or []
                        if choices:
                            emit((choices[0].get("delta") or {}).get("content") or "")
                        if (event.get("usage") or {}).get("completion_tokens"):
                            stats["tokens"] = event["usage"]["completion_tokens"]

    async def supervise():
        if should_stop():
            stats["stopped"] = True
            return
        task = asyncio.create_task(request())
        try:
            while not task.done():
                await asyncio.wait({task}, timeout=0.05)
                if should_stop() and not task.done():
                    stats["stopped"] = True
                    task.cancel()
                    break
            await task
        except asyncio.CancelledError:
            stats["stopped"] = True
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    error = ""
    try:
        asyncio.run(supervise())
    except Exception as exc:
        error = str(exc) or type(exc).__name__
        if parts:
            stats.update(stopped=True, error=error)
    text = "".join(parts)
    if error and not text and not stats["stopped"]:
        text = "Erreur : " + error
    stats["seconds"] = time.perf_counter() - started
    if parts and "tokens_per_s" not in stats:
        stats["tokens_estimated"] = not bool(stats.get("tokens"))
        stats["tokens"] = stats.get("tokens") or max(1, len(text)//4)
        stats["tokens_per_s"] = stats["tokens"] / max(time.perf_counter() - (first or started), .001)
    return text, stats
