"""Adresses de moteurs sur ce PC, sans résolution DNS ni accès distant."""
import ipaddress
from urllib.parse import urlsplit


def validate_engine_url(value, local_only=True):
    value = value.strip().rstrip('/')
    try:
        parsed = urlsplit(value)
        port = parsed.port
        hostname = parsed.hostname
    except ValueError as exc:
        raise ValueError('Adresse ou port du moteur invalide.') from exc
    if (parsed.scheme not in ('http', 'https') or not hostname or
            parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment):
        raise ValueError('Indiquez une adresse HTTP(S) sans identifiants ni paramètres.')
    if local_only:
        local = hostname.lower() == 'localhost'
        try: local = local or ipaddress.ip_address(hostname).is_loopback
        except ValueError: pass
        if not local:
            raise ValueError('Mode local : utilisez localhost, 127.0.0.1 ou [::1], avec le port du moteur lancé sur ce PC. Les adresses distantes sont bloquées.')
    return value


LOCAL_HELP = (
    'Les modèles proposés peuvent fonctionner sur le PC après installation de leur moteur, '
    'de leurs poids et de leurs dépendances. Internet est nécessaire pour ces téléchargements initiaux. '
    'Utilisez ensuite les modèles téléchargés et les workflows locaux, sans fournisseur API ni nœud cloud. '
    'Le contrôle d’adresse garantit que vous ouvrez un moteur sur ce PC ; il ne contrôle pas les connexions '
    'effectuées par ce moteur. Pour vérifier le fonctionnement hors ligne, coupez Internet après installation '
    'puis lancez un petit essai. Une interface web sur localhost fonctionne sans cloud.'
)
