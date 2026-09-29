"""Runner externe ErisForge v145."""
import argparse
import json
import random
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from erisforge import Forge
from erisforge.scorers import ExpressionRefusalScorer


def load_lines(path, limit):
    rows = [
        line.strip()
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    if len(rows) < 5:
        raise ValueError(f"{path}: au moins 5 instructions non vides sont requises.")
    return rows[:limit]


def model_dtype():
    if torch.cuda.is_available():
        return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    return torch.float32


def load_model_and_tokenizer(model_name):
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        if tokenizer.eos_token is not None:
            tokenizer.pad_token = tokenizer.eos_token
        elif tokenizer.unk_token is not None:
            tokenizer.pad_token = tokenizer.unk_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=model_dtype(),
        low_cpu_mem_usage=True,
    )
    if tokenizer.pad_token_id is not None:
        model.generation_config.pad_token_id = tokenizer.pad_token_id
    return model, tokenizer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    random.seed(int(cfg.get("seed", 42)))
    torch.manual_seed(int(cfg.get("seed", 42)))

    objective = load_lines(cfg["objective_file"], int(cfg["max_instructions"]))
    reference = load_lines(cfg["reference_file"], int(cfg["max_instructions"]))

    forge = Forge(batch_size=int(cfg["batch_size"]))
    forge.load_instructions(
        objective_behaviour_instructions=objective,
        anti_behaviour_instructions=reference,
    )

    print("Chargement du modèle :", cfg["model"], flush=True)
    model, tokenizer = load_model_and_tokenizer(cfg["model"])
    try:
        print("Nombre de couches :", len(model.model.layers), flush=True)
    except Exception:
        pass

    direction_path = Path(cfg["direction_path"])
    if cfg["action"] == "measure":
        scorer = ExpressionRefusalScorer()
        print("Calcul de la direction comportementale…", flush=True)
        direction = forge.approx_best_objective_behaviour_dir(
            model=model,
            tokenizer=tokenizer,
            scorer=scorer,
            eval_objective_behaviour_instructions=objective,
            eval_antiobjective_instructions=reference,
            min_layer=int(cfg["layer_start"]),
            max_layer=int(cfg["layer_end"]) + 1,
            batch_size=int(cfg["batch_size"]),
        )
        direction_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(direction.cpu(), direction_path)
        print("Direction sauvegardée :", direction_path, flush=True)
        return

    if not direction_path.is_file():
        raise FileNotFoundError(
            "Direction absente. Lancez d’abord l’étape de mesure."
        )

    direction = torch.load(direction_path, map_location="cpu")
    scale = float(cfg["strength"])
    if cfg["intervention"] == "addition":
        scale = -scale

    output = Path(cfg["output"])
    output.mkdir(parents=True, exist_ok=True)

    print(
        "Transformation ErisForge :",
        cfg["intervention"],
        "couches",
        cfg["layer_start"],
        "à",
        cfg["layer_end"],
        "intensité",
        scale,
        flush=True,
    )

    forge.save_model(
        model=model,
        tokenizer=tokenizer,
        behaviour_dir=direction,
        scale_factor=scale,
        min_layer=int(cfg["layer_start"]),
        max_layer=int(cfg["layer_end"]) + 1,
        output_model_name=str(output),
        to_hub=False,
        model_architecture="",
    )

    metadata = {
        "tool": "ErisForge",
        "model": cfg["model"],
        "objective_file": cfg["objective_file"],
        "reference_file": cfg["reference_file"],
        "direction_path": str(direction_path),
        "intervention": cfg["intervention"],
        "strength": float(cfg["strength"]),
        "layer_start": int(cfg["layer_start"]),
        "layer_end": int(cfg["layer_end"]),
        "seed": int(cfg["seed"]),
    }
    (output / "ia_manager_erisforge.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Modèle ErisForge sauvegardé :", output, flush=True)


if __name__ == "__main__":
    main()
