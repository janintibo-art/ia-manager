"""Modèles créatifs : fiches et points d'accès aux moteurs externes."""
from urllib.parse import urlsplit

CATEGORIES = ('Musique et sons', 'Vidéo', 'Modélisation 3D')
MODELS = (
    dict(id='musicgen-small', category=CATEGORIES[0], name='MusicGen Small',
         specialty='Musique instrumentale depuis une description', input='Texte',
         engine='AudioCraft / interface MusicGen',
         model_url='https://huggingface.co/facebook/musicgen-small',
         guide_url='https://github.com/facebookresearch/audiocraft/blob/main/docs/MUSICGEN.md',
         hardware='Version 300 millions de paramètres ; plus petite que Medium. Commencer par un extrait court. GPU recommandé ; vérifier les prérequis AudioCraft.',
         instructions='Installer AudioCraft selon sa documentation, puis lancer son interface MusicGen. Choisir le modèle small et coller votre description.',
         example='Instrumental underground techno, 145 BPM, deep bass, punchy kick, dark analog synthesizers, no vocals.',
         tip='Décrire le style, le tempo, les instruments et l’ambiance. Le tempo demandé et la continuité d’une boucle ne sont pas garantis.'),
    dict(id='musicgen-melody', category=CATEGORIES[0], name='MusicGen Melody',
         specialty='Musique guidée par une mélodie de référence', input='Texte + audio de référence',
         engine='AudioCraft / interface MusicGen',
         model_url='https://huggingface.co/facebook/musicgen-melody',
         guide_url='https://github.com/facebookresearch/audiocraft/blob/main/docs/MUSICGEN.md',
         hardware='Modèle 1,5 milliard de paramètres. La documentation AudioCraft recommande 16 Go de mémoire GPU pour les modèles de cette taille.',
         instructions='Installer AudioCraft et ouvrir son interface MusicGen. Choisir melody, importer la référence audio dans cette interface et décrire l’arrangement.',
         example='Instrumental folk dance with accordion, fast hand percussion and warm bass, energetic live atmosphere.',
         tip='La référence guide la mélodie ; elle ne remplace pas un séquenceur MIDI ni un éditeur multipiste.'),
    dict(id='audiogen', category=CATEGORIES[0], name='AudioGen Medium',
         specialty='Bruitages, ambiances et effets sonores', input='Texte',
         engine='AudioCraft / AudioGen',
         model_url='https://huggingface.co/facebook/audiogen-medium',
         guide_url='https://github.com/facebookresearch/audiocraft/blob/main/docs/AUDIOGEN.md',
         hardware='Modèle 1,5 milliard de paramètres. Installation Python/PyTorch compatible nécessaire ; mémoire requise selon la durée et la configuration.',
         instructions='Suivre le guide AudioGen pour générer depuis Python. Si vous utilisez une interface web compatible, enregistrer son adresse ci-dessous. Une interface web n’est pas installée par IA Manager.',
         example='A small friendly creature squeaks twice, then bounces on a wooden floor, quiet indoor background.',
         tip='Décrire une source sonore, son action et son environnement. AudioGen est destiné aux sons et ambiances.'),
    dict(id='wan21', category=CATEGORIES[1], name='Wan 2.1 T2V 1.3B',
         specialty='Courtes vidéos depuis une description', input='Texte → vidéo',
         engine='ComfyUI avec workflow Wan ou outil officiel Wan',
         model_url='https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B',
         guide_url='https://github.com/Wan-Video/Wan2.1',
         hardware='La variante 1,3 milliard est la plus petite variante T2V de cette série. Commencer en 480p ; la vidéo reste exigeante en mémoire et en calcul.',
         instructions='Installer Wan ou charger un workflow Wan compatible dans ComfyUI, puis les poids et composants demandés. Choisir précisément T2V 1.3B. Le workflow SDXL de l’onglet Images ne convient pas.',
         example='A tiny fantasy creature walks slowly through a mossy forest, soft morning light, gentle camera tracking, consistent character, single continuous shot.',
         tip='Décrire le sujet, son mouvement et le mouvement de caméra. Cette fiche T2V ne transforme pas une image en vidéo et ne génère pas une bande-son synchronisée.'),
    dict(id='ltx-video', category=CATEGORIES[1], name='LTX-Video',
         specialty='Vidéo depuis du texte ou une image selon le workflow', input='Texte ou image + texte',
         engine='ComfyUI avec workflow LTX ou outil officiel LTX-Video',
         model_url='https://huggingface.co/Lightricks/LTX-Video',
         guide_url='https://github.com/Lightricks/LTX-Video',
         hardware='Plusieurs variantes et tailles existent. Choisir un workflow correspondant exactement aux poids ; réduire résolution et durée pour les premiers essais.',
         instructions='Suivre l’installation officielle ou le workflow ComfyUI indiqué par le projet. Charger ses composants, puis le texte et éventuellement une image dans cette interface.',
         example='A wide landscape of a magical island above the clouds, trees moving gently in the wind, slow cinematic camera pan, soft sunset light.',
         tip='Cette fiche concerne LTX-Video. Les réglages et composants des autres générations LTX ne sont pas interchangeables.'),
    dict(id='hunyuan3d', category=CATEGORIES[2], name='Hunyuan3D 2',
         specialty='Maillage 3D depuis une image, puis texture', input='Image de référence',
         engine='Interface locale Hunyuan3D',
         model_url='https://huggingface.co/tencent/Hunyuan3D-2',
         guide_url='https://github.com/Tencent-Hunyuan/Hunyuan3D-2',
         hardware='Le projet distingue la génération de forme et celle de texture. Le besoin mémoire dépend de la variante et des options ; consulter le guide avant de télécharger.',
         instructions='Installer le projet Hunyuan3D et lancer son interface Gradio selon le guide. Importer l’image dans cette interface, générer la forme puis la texture avec les composants appropriés.',
         example='Préparer une image du personnage entier, de face, bras décollés du torse et jambes séparées, sur un fond simple, sans objet cachant la silhouette.',
         tip='Ces notes servent à préparer l’image de référence. Le résultat n’est pas automatiquement riggé : nettoyer le maillage et préparer le squelette dans un outil 3D.'),
    dict(id='triposr', category=CATEGORIES[2], name='TripoSR',
         specialty='Reconstruction rapide d’un objet 3D depuis une image', input='Une image de référence',
         engine='Interface locale TripoSR',
         model_url='https://huggingface.co/stabilityai/TripoSR',
         guide_url='https://github.com/VAST-AI-Research/TripoSR',
         hardware='Le projet annonce environ 6 Go de mémoire GPU avec les options par défaut pour une image. Ce chiffre dépend des réglages et ne garantit pas la compatibilité du PC.',
         instructions='Installer TripoSR selon le guide, puis utiliser sa démo Gradio ou son script de reconstruction. Importer l’image dans l’outil ; exporter le maillage depuis cet outil.',
         example='Préparer une vue claire d’un objet isolé : coffre, rocher, arbre ou petit monstre, entièrement visible, avec un fond simple et une lumière régulière.',
         tip='Les faces cachées sont reconstruites par estimation. Vérifier le dos et les côtés ; le modèle n’inclut pas automatiquement un squelette ou des animations.'),
)


def filter_models(category, query=''):
    query = query.strip().casefold()
    return [m for m in MODELS if m['category'] == category and
            (not query or query in ' '.join((m['name'], m['specialty'], m['input'], m['engine'])).casefold())]


def engine_url(value):
    value = value.strip().rstrip('/')
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Indiquez une adresse HTTP(S) sans identifiant ni paramètres, telle qu’affichée par votre moteur local.')
    return value
