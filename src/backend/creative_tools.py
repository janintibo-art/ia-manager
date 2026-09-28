"""Recettes explicites pour environnements créatifs séparés, sans shell."""
import json
import os
from pathlib import Path

TOOLS = {
    'comfyui': dict(name='ComfyUI — images et vidéo', repo='https://github.com/comfyanonymous/ComfyUI.git',
        guide='https://github.com/comfyanonymous/ComfyUI#installing', port=8188, python='Python 3.10 ou 3.11',
        note='Moteur images + workflows Wan/LTX/FLUX. Les poids et les workflows adaptés restent à télécharger dans ComfyUI. Les nœuds API sont désactivés au lancement.'),
    'audiocraft': dict(name='AudioCraft — musique et sons', repo='https://github.com/facebookresearch/audiocraft.git',
        guide='https://github.com/facebookresearch/audiocraft#installation', port=7861, python='Python 3.9',
        note='MusicGen Small, Melody et AudioGen dans une interface locale fournie. PyTorch 2.1 / CUDA 11.8 pour NVIDIA : les GPU récents peuvent ne pas être compatibles avec cette ancienne pile.'),
    'triposr': dict(name='TripoSR — reconstruction 3D', repo='https://github.com/VAST-AI-Research/TripoSR.git',
        guide='https://github.com/VAST-AI-Research/TripoSR#installation', port=7862, python='Python 3.10 ou 3.11',
        note='Les dépendances incluent torchmcubes : compilateur C++ requis, CUDA Toolkit correspondant à PyTorch pour son accélération GPU. Le journal indique les composants manquants.'),
    'hunyuan3d': dict(name='Hunyuan3D 2 — forme et texture', repo='https://github.com/Tencent-Hunyuan/Hunyuan3D-2.git',
        guide='https://github.com/Tencent-Hunyuan/Hunyuan3D-2#install-requirements', port=7863, python='Python 3.10 ou 3.11',
        note='Les modules de texture sont compilés pendant l’installation. Nécessite compilateur C++, CUDA Toolkit compatible et GPU adapté pour la texture. Une installation peut échouer si ces prérequis manquent.'),
}


def paths(root, key, windows=None):
    if key not in TOOLS: raise ValueError('Outil inconnu.')
    if not str(root).strip(): raise ValueError('Choisissez un dossier d’installation.')
    base = Path(root).expanduser().resolve() / key
    windows = os.name == 'nt' if windows is None else windows
    return dict(base=base, source=base/'source', env=base/'venv',
                python=base/'venv'/('Scripts/python.exe' if windows else 'bin/python'),
                cache=base/'cache', outputs=base/'resultats', manifest=base/'ia_manager_tool.json')


def write_json(path, data):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def read_manifest(root, key):
    p=paths(root,key)['manifest']
    try:
        value=json.loads(p.read_text(encoding='utf-8'))
        return value if value.get('tool')==key and value.get('managed_by')=='IA Manager' else {}
    except (OSError, ValueError, AttributeError): return {}


def prepare(root, key, hardware):
    p=paths(root,key)
    if p['base'].exists() and any(p['base'].iterdir()) and not read_manifest(root,key):
        raise ValueError('Ce sous-dossier contient une installation non gérée. Choisissez un autre dossier parent ; aucun fichier n’a été remplacé.')
    old=read_manifest(root,key)
    if old.get('hardware') and old['hardware']!=hardware:
        raise ValueError('Cette installation utilise un autre profil matériel. Choisissez un nouveau dossier parent pour créer un environnement séparé.')
    if p['source'].exists() and not (p['source']/'.git').is_dir():
        raise ValueError('Le dossier source est incomplet. Choisissez un nouveau dossier parent pour reprendre sans écraser les fichiers existants.')
    for name in ('base','cache','outputs'):p[name].mkdir(parents=True,exist_ok=True)
    write_json(p['manifest'],dict(managed_by='IA Manager',tool=key,hardware=hardware,state='installation en cours'))
    if key=='audiocraft':(p['base']/'audio_local.py').write_text(AUDIO_APP,encoding='utf-8')
    return p


def command(label, program, args, cwd):
    return dict(label=label, program=str(program), args=[str(v) for v in args], cwd=str(cwd))


def install_plan(root, key, python, git, hardware, windows=None):
    if hardware not in ('cpu','nvidia'):raise ValueError('Profil matériel inconnu.')
    if not python or not git:raise ValueError('Sélectionnez Python et installez Git.')
    p=paths(root,key,windows)
    version='sys.version_info[:2] == (3,9)' if key=='audiocraft' else 'sys.version_info[:2] in ((3,10),(3,11))'
    code="import sys; print(sys.version); assert "+version+", 'Version Python attendue : "+TOOLS[key]['python']+"'"
    steps=[command('Vérifier Python',python,['-c',code],p['base'])]
    if not (p['source']/'.git').is_dir():
        steps.append(command('Télécharger le code officiel',git,['clone','--depth','1',TOOLS[key]['repo'],p['source']],p['base']))
    steps.append(command('Version du code téléchargé',git,['-C',p['source'],'rev-parse','HEAD'],p['base']))
    steps.append(command('Créer l’environnement isolé',python,['-m','venv',p['env']],p['base']))
    exe=p['python']
    def pip(label,args,cwd=None):steps.append(command(label,exe,['-m','pip','install']+args,cwd or p['source']))
    pip('Préparer pip et outils de compilation',['--upgrade','pip','setuptools','wheel'])
    if key=='audiocraft':
        packages=['torch==2.1.0','torchvision==0.16.0','torchaudio==2.1.0']
        index='cu118' if hardware=='nvidia' else 'cpu'
    else:
        packages=['torch','torchvision','torchaudio']
        index='cu128' if hardware=='nvidia' else 'cpu'
    pip('Installer PyTorch — '+hardware,packages+['--index-url','https://download.pytorch.org/whl/'+index])
    pip('Installer FFmpeg privé et outils',['imageio-ffmpeg','cmake','ninja'])
    if key=='audiocraft':
        # Le code officiel impose une pile ancienne : limiter les API dont il dépend.
        pip('Installer AudioCraft et son interface',['-e','.', 'numpy<2','transformers<4.50','gradio>=4,<5','huggingface-hub<1'])
    else:
        pip('Installer les dépendances du moteur',['-r','requirements.txt'])
        if key in ('triposr','hunyuan3d'):
            pip('Installer le moteur de détourage CPU',['onnxruntime'])
        if key=='hunyuan3d':
            pip('Installer Hunyuan3D',['-e','.'])
            for folder in ('custom_rasterizer','differentiable_renderer'):
                steps.append(command('Compiler la texture : '+folder,exe,['setup.py','install'],p['source']/'hy3dgen'/'texgen'/folder))
    ffmpeg="import imageio_ffmpeg,shutil,sys,pathlib; d=pathlib.Path(sys.executable).parent/('ffmpeg.exe' if sys.platform=='win32' else 'ffmpeg'); shutil.copy2(imageio_ffmpeg.get_ffmpeg_exe(),d); print(d)"
    steps.append(command('Rendre FFmpeg disponible dans cet environnement',exe,['-c',ffmpeg],p['source']))
    steps.append(command('Contrôler les dépendances',exe,['-m','pip','check'],p['source']))
    steps.append(diagnostic_command(root,key,windows))
    return steps


def diagnostic_command(root,key,windows=None):
    p=paths(root,key,windows)
    extra={'comfyui':"import importlib.util; assert importlib.util.find_spec('comfy') is not None", 'audiocraft':'from audiocraft.models import MusicGen, AudioGen',
           'triposr':'from tsr.system import TSR; import torchmcubes',
           'hunyuan3d':'from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline'}[key]
    code="import sys,shutil,torch; print('Python',sys.version); print('Torch',torch.__version__); print('CUDA disponible',torch.cuda.is_available()); print('FFmpeg',shutil.which('ffmpeg')); "+extra+"; print('Imports du moteur OK ; poids et génération non vérifiés')"
    return command('Diagnostic du moteur',p['python'],['-c',code],p['source'])


def launch_command(root,key,hardware='nvidia',windows=None):
    p=paths(root,key,windows);port=TOOLS[key]['port']
    if key=='comfyui':
        args=['main.py','--listen','127.0.0.1','--port',str(port),'--disable-api-nodes']
        if hardware=='cpu':args.append('--cpu')
    elif key=='audiocraft':args=[p['base']/'audio_local.py','--port',str(port),'--output',p['outputs'],'--device','cpu' if hardware=='cpu' else 'cuda']
    elif key=='triposr':args=['gradio_app.py','--port',str(port)]
    else:
        args=['gradio_app.py','--host','127.0.0.1','--port',str(port),'--device','cpu' if hardware=='cpu' else 'cuda']
        if hardware=='cpu':args.append('--disable_tex')
    return command('Démarrer '+TOOLS[key]['name'],p['python'],['-u']+args,p['source'])


def environment(root,key,offline=False):
    p=paths(root,key)
    values={'PYTHONUNBUFFERED':'1','PYTHONIOENCODING':'utf-8', 'GRADIO_SERVER_NAME':'127.0.0.1',
            'GRADIO_ANALYTICS_ENABLED':'False','HF_HUB_DISABLE_TELEMETRY':'1',
            'HF_HOME':str(p['cache']/'huggingface'),'TORCH_HOME':str(p['cache']/'torch'),
            'AUDIOCRAFT_CACHE_DIR':str(p['cache']/'audiocraft'),
            'U2NET_HOME':str(p['cache']/'rembg'),
            'HF_HUB_OFFLINE':'1' if offline else '0','TRANSFORMERS_OFFLINE':'1' if offline else '0',
            'PATH':str(p['python'].parent)+os.pathsep+os.environ.get('PATH','')}
    return values


AUDIO_APP = r'''
"""Interface locale IA Manager pour MusicGen et AudioGen."""
import argparse
from pathlib import Path
import uuid
import gradio as gr
import torch
import torchaudio
from audiocraft.models import MusicGen, AudioGen
from audiocraft.data.audio import audio_write
parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,default=7861)
parser.add_argument('--output',required=True)
parser.add_argument('--device',default='cuda')
args=parser.parse_args()
output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
loaded_name=None
loaded=None
choices={'MusicGen Small':'facebook/musicgen-small','MusicGen Melody':'facebook/musicgen-melody','AudioGen':'facebook/audiogen-medium'}
def generate(choice,prompt,duration,reference):
    global loaded,loaded_name
    if not prompt.strip():raise gr.Error('Décrivez la musique ou le son.')
    name=choices[choice]
    if args.device=='cuda' and not torch.cuda.is_available():raise gr.Error('CUDA indisponible. Vérifiez PyTorch/pilote ou installez le profil CPU dans un autre dossier.')
    if name!=loaded_name:
        loaded=None;loaded_name=None
        if torch.cuda.is_available():torch.cuda.empty_cache()
        cls=AudioGen if choice=='AudioGen' else MusicGen
        loaded=cls.get_pretrained(name,device=args.device);loaded_name=name
    loaded.set_generation_params(duration=float(duration))
    if reference and choice=='MusicGen Melody':
        melody,sr=torchaudio.load(reference)
        wave=loaded.generate_with_chroma([prompt],melody.unsqueeze(0),sr)
    else:wave=loaded.generate([prompt])
    filename=output/('creation_'+uuid.uuid4().hex)
    audio_write(str(filename),wave[0].cpu(),loaded.sample_rate,strategy='loudness',loudness_compressor=True)
    return str(filename)+'.wav'
with gr.Blocks() as app:
    gr.Markdown('# Musique et sons — IA Manager\nCalcul sur ce PC. Premier essai en ligne pour récupérer les poids, puis relancer hors ligne. Les WAV restent dans le dossier de résultats.')
    model=gr.Dropdown(list(choices),value='MusicGen Small',label='Modèle')
    prompt=gr.Textbox(label='Description',lines=3)
    seconds=gr.Slider(1,20,value=5,step=1,label='Durée (secondes)')
    reference=gr.Audio(type='filepath',label='Référence facultative — MusicGen Melody uniquement')
    button=gr.Button('Générer sur ce PC')
    result=gr.Audio(type='filepath',label='Résultat WAV')
    button.click(generate,[model,prompt,seconds,reference],result)
app.queue().launch(server_name='127.0.0.1',server_port=args.port,share=False)
'''
