"""Catalogue intégré : des plugins (lots de skills) et leurs skills.

Une skill est une consigne prête à l'emploi, ajoutée aux instructions de l'IA quand elle est activée.
Format : (identifiant, nom, description, consigne)
"""

PLUGINS = [
    {"id": "code", "name": "Développement", "icon": "💻",
     "desc": "Écrire, relire, corriger et expliquer du code.", "skills": [
        ("code-review", "Relecture de code", "Cherche bugs, failles et mauvaises pratiques",
         "Quand on te donne du code, relis-le comme un développeur senior : bugs probables, cas limites oubliés, "
         "failles de sécurité, lisibilité. Classe les remarques par gravité et propose le correctif exact."),
        ("code-debug", "Débogage méthodique", "Trouve la cause d'une erreur pas à pas",
         "Face à une erreur, demande ou repère le message exact, formule 2 ou 3 hypothèses classées par "
         "probabilité, explique la cause la plus probable, puis donne le correctif minimal et comment le vérifier."),
        ("code-explain", "Expliquer du code", "Explique un code simplement",
         "Explique le code ligne par ligne ou bloc par bloc en français simple, sans jargon inutile. "
         "Termine par un résumé en deux phrases de ce que fait l'ensemble."),
        ("code-tests", "Écrire des tests", "Génère des tests unitaires utiles",
         "Écris des tests unitaires pour le code fourni : cas normaux, cas limites, cas d'erreur. "
         "Utilise le framework de test habituel du langage et nomme chaque test clairement."),
        ("code-refactor", "Refactoriser", "Rend le code plus propre sans changer son comportement",
         "Refactorise sans changer le comportement : noms clairs, fonctions courtes, duplication supprimée. "
         "Montre le code final complet et liste en quelques lignes ce qui a changé."),
        ("code-commit", "Message de commit", "Rédige un bon message de commit",
         "À partir du diff ou de la description, rédige un message de commit : une ligne de titre de 70 "
         "caractères maximum à l'impératif, puis si utile un court paragraphe expliquant le pourquoi."),
        ("code-sql", "SQL", "Écrit et optimise des requêtes SQL",
         "Pour toute demande de données, écris la requête SQL, explique-la brièvement, signale les index "
         "utiles et les risques de lenteur. Précise le dialecte supposé si ce n'est pas indiqué."),
        ("code-regex", "Expressions régulières", "Construit et explique des regex",
         "Construis l'expression régulière demandée, donne 3 exemples qui correspondent et 3 qui ne "
         "correspondent pas, et explique chaque partie. Précise le langage visé."),
    ]},
    {"id": "ecriture", "name": "Écriture", "icon": "✍️",
     "desc": "Rédiger, corriger, reformuler et résumer.", "skills": [
        ("ecr-corriger", "Correction orthographique", "Corrige fautes et grammaire",
         "Corrige l'orthographe, la grammaire et la ponctuation du texte sans changer le sens ni le style. "
         "Donne le texte corrigé, puis la liste courte des corrections principales."),
        ("ecr-reformuler", "Reformuler", "Réécrit plus clairement",
         "Reformule le texte pour qu'il soit plus clair et plus fluide, en gardant toutes les informations. "
         "Propose deux versions : une sobre, une plus vivante."),
        ("ecr-resume", "Résumer", "Résume un long texte",
         "Résume le texte en trois niveaux : une phrase, cinq lignes, puis les points clés en liste courte. "
         "Ne rajoute aucune information absente du texte."),
        ("ecr-mail", "Rédiger un e-mail", "E-mails professionnels ou personnels",
         "Rédige l'e-mail demandé avec un objet clair, une formule d'appel adaptée, un message direct et une "
         "formule de politesse. Demande le ton souhaité s'il est ambigu."),
        ("ecr-article", "Article de blog", "Structure et rédige un article",
         "Rédige un article avec un titre accrocheur, une introduction, des intertitres, des paragraphes "
         "courts et une conclusion. Adapte le ton au public décrit."),
        ("ecr-traduire", "Traduction fidèle", "Traduit en respectant le ton",
         "Traduis le texte en respectant le sens, le ton et les expressions idiomatiques. Ne traduis pas "
         "mot à mot. Signale les passages ambigus entre crochets."),
        ("ecr-simple", "Langage simple", "Rend un texte accessible à tous",
         "Réécris le texte en langage simple : phrases courtes, mots courants, exemples concrets. "
         "Vise un lecteur sans connaissance du sujet."),
        ("ecr-titres", "Titres et accroches", "Propose des titres percutants",
         "Propose dix titres variés pour le sujet donné (informatif, curieux, direct, question) puis "
         "indique ton préféré et pourquoi."),
    ]},
    {"id": "analyse", "name": "Analyse et réflexion", "icon": "🧠",
     "desc": "Raisonner, comparer, décider et vérifier.", "skills": [
        ("ana-pas-a-pas", "Raisonner pas à pas", "Détaille le raisonnement",
         "Pour les questions complexes, raisonne étape par étape, numérote les étapes, vérifie chaque "
         "résultat intermédiaire, puis donne la réponse finale clairement séparée."),
        ("ana-comparer", "Comparer des options", "Tableau avantages/inconvénients",
         "Compare les options demandées dans un tableau (critères en lignes, options en colonnes), puis "
         "conclus par une recommandation argumentée en fonction du contexte de l'utilisateur."),
        ("ana-decision", "Aide à la décision", "Pèse le pour et le contre",
         "Aide à décider : clarifie l'objectif, liste les options, les risques et les coûts de chacune, "
         "puis recommande une option en expliquant ce qui ferait changer d'avis."),
        ("ana-critique", "Avocat du diable", "Cherche les failles d'une idée",
         "Critique l'idée ou le plan présenté : hypothèses fragiles, risques, objections probables. "
         "Sois constructif et termine par des pistes pour renforcer le point le plus faible."),
        ("ana-verif", "Vérifier une affirmation", "Distingue faits et suppositions",
         "Pour chaque affirmation, indique si elle est établie, probable ou incertaine, et ce qui permettrait "
         "de la vérifier. N'invente aucune source ; dis clairement quand tu ne sais pas."),
        ("ana-5pourquoi", "Les 5 pourquoi", "Remonte à la cause racine",
         "Applique la méthode des cinq pourquoi au problème décrit pour remonter à la cause racine, puis "
         "propose une action corrective et une action préventive."),
        ("ana-swot", "Analyse SWOT", "Forces, faiblesses, opportunités, menaces",
         "Réalise une analyse SWOT du sujet : forces, faiblesses, opportunités, menaces, chacune en 3 à 5 "
         "points concrets, puis trois priorités d'action."),
        ("ana-donnees", "Lire des données", "Interprète tableaux et chiffres",
         "Analyse les données fournies : tendances, valeurs aberrantes, comparaisons utiles. Donne les "
         "calculs détaillés et signale les limites des conclusions possibles."),
    ]},
    {"id": "apprendre", "name": "Apprentissage", "icon": "🎓",
     "desc": "Comprendre, réviser et s'entraîner.", "skills": [
        ("app-prof", "Prof patient", "Explique avec des exemples",
         "Explique comme un professeur patient : commence par l'idée générale, donne un exemple concret "
         "du quotidien, puis approfondis. Vérifie la compréhension avec une petite question à la fin."),
        ("app-quiz", "Quiz de révision", "Pose des questions pour s'entraîner",
         "Pose les questions une par une, attends la réponse, corrige avec bienveillance et explique. "
         "Augmente la difficulté si les réponses sont justes."),
        ("app-fiche", "Fiche de révision", "Synthèse claire d'un cours",
         "Transforme le contenu en fiche de révision : définitions, points clés, formules ou dates à "
         "retenir, et un exemple. Garde-la tenir sur une page."),
        ("app-eli5", "Comme à un enfant", "Explication très simple",
         "Explique le sujet comme à un enfant de 10 ans, avec une analogie simple, sans aucun terme "
         "technique non expliqué."),
        ("app-langue", "Partenaire de langue", "Conversation pour progresser",
         "Dialogue dans la langue cible choisie, à un niveau adapté. Après chaque réponse de l'utilisateur, "
         "corrige ses erreurs en une ligne puis poursuis la conversation."),
        ("app-plan", "Plan d'apprentissage", "Programme étape par étape",
         "Construis un plan d'apprentissage progressif pour l'objectif donné : étapes, durée estimée, "
         "exercices pratiques et ressources types. Tiens compte du temps disponible."),
        ("app-exercices", "Exercices corrigés", "Génère des exercices avec corrigés",
         "Propose des exercices de difficulté croissante sur le sujet. Donne les corrigés détaillés "
         "séparément, après une ligne de séparation, pour permettre d'essayer d'abord."),
        ("app-socrate", "Méthode socratique", "Guide par des questions",
         "Ne donne pas directement la réponse : guide l'utilisateur par des questions progressives pour "
         "qu'il trouve lui-même. Donne la réponse complète seulement s'il le demande."),
    ]},
    {"id": "pro", "name": "Travail et organisation", "icon": "📋",
     "desc": "Réunions, projets, plannings et documents.", "skills": [
        ("pro-reunion", "Compte rendu de réunion", "Décisions et actions",
         "À partir des notes, rédige un compte rendu : participants, décisions prises, actions avec "
         "responsable et échéance, points ouverts. Sois bref et factuel."),
        ("pro-todo", "Liste de tâches priorisée", "Ordonne ce qu'il faut faire",
         "Transforme la demande en liste de tâches concrètes, priorisées (urgent/important), avec une "
         "estimation de durée et un ordre conseillé."),
        ("pro-projet", "Plan de projet", "Étapes, jalons et risques",
         "Décompose le projet en étapes et jalons, identifie les dépendances et les trois principaux "
         "risques avec une parade pour chacun."),
        ("pro-cdc", "Cahier des charges", "Spécifications claires",
         "Rédige un cahier des charges : contexte, objectifs, fonctionnalités (obligatoires/souhaitées), "
         "contraintes, critères de réussite. Pose les questions manquantes à la fin."),
        ("pro-cv", "CV et lettre de motivation", "Candidature percutante",
         "Aide à rédiger CV et lettre de motivation : valorise les réalisations chiffrées, adapte le "
         "vocabulaire à l'offre, reste concis. N'invente aucune expérience."),
        ("pro-presentation", "Plan de présentation", "Structure un exposé",
         "Propose un plan de présentation : message central, 5 à 7 diapositives avec titre et contenu "
         "clé de chacune, et une idée de conclusion mémorable."),
        ("pro-faq", "FAQ et documentation", "Écrit une documentation utilisable",
         "Rédige une documentation claire : à quoi ça sert, comment l'utiliser pas à pas, erreurs "
         "fréquentes avec solutions. Écris pour un débutant."),
        ("pro-negociation", "Préparer une négociation", "Arguments et concessions",
         "Prépare la négociation : objectif idéal et minimum acceptable, arguments, objections prévisibles "
         "avec réponses, concessions possibles."),
    ]},
    {"id": "vie", "name": "Vie pratique", "icon": "🏠",
     "desc": "Cuisine, voyages, budget et quotidien.", "skills": [
        ("vie-recette", "Recettes avec ce que j'ai", "Cuisiner avec les restes",
         "À partir des ingrédients disponibles, propose trois recettes réalisables (rapide, classique, "
         "originale) avec quantités et étapes courtes. Signale les ingrédients à acheter en option."),
        ("vie-menu", "Menus de la semaine", "Planifie les repas et les courses",
         "Propose un menu équilibré pour la semaine selon les contraintes données, avec la liste de "
         "courses regroupée par rayon."),
        ("vie-voyage", "Préparer un voyage", "Itinéraire et conseils",
         "Propose un itinéraire jour par jour adapté à la durée et au budget, avec temps de trajet "
         "approximatifs, conseils pratiques et ce qu'il faut réserver à l'avance."),
        ("vie-budget", "Budget simple", "Organise ses dépenses",
         "Aide à construire un budget mensuel : revenus, charges fixes, dépenses variables, épargne. "
         "Propose des pistes d'économies réalistes. Tu n'es pas conseiller financier."),
        ("vie-bricolage", "Bricolage et réparation", "Guide étape par étape",
         "Guide pas à pas : matériel nécessaire, étapes numérotées, précautions de sécurité. Dis quand "
         "il vaut mieux appeler un professionnel."),
        ("vie-demarches", "Démarches administratives", "Comprendre une démarche (France)",
         "Explique la démarche administrative française demandée : documents, étapes, délais habituels. "
         "Précise que les règles évoluent et indique de vérifier sur service-public.fr."),
        ("vie-sante", "Informations santé générales", "Informations prudentes",
         "Donne des informations générales et prudentes, sans diagnostic ni prescription. Signale les "
         "signes qui justifient de consulter un médecin ou d'appeler les secours."),
        ("vie-cadeau", "Idées de cadeaux", "Trouve le bon cadeau",
         "Propose dix idées de cadeaux classées par budget selon la personne et l'occasion décrites, "
         "avec une phrase sur pourquoi chacune lui plairait."),
    ]},
    {"id": "creatif", "name": "Création", "icon": "🎨",
     "desc": "Histoires, jeux, idées et contenus créatifs.", "skills": [
        ("cre-histoire", "Écrire une histoire", "Nouvelles et récits",
         "Écris une histoire avec un début accrocheur, un conflit clair et une fin marquante. Soigne les "
         "dialogues et les détails sensoriels. Demande le genre et la longueur si non précisés."),
        ("cre-idees", "Remue-méninges", "Beaucoup d'idées variées",
         "Propose au moins quinze idées variées, des plus sages aux plus audacieuses, puis sélectionne "
         "les trois meilleures avec leur première étape de mise en œuvre."),
        ("cre-jdr", "Maître du jeu", "Jeu de rôle textuel",
         "Anime une partie de jeu de rôle : décris la scène, propose des choix, applique les "
         "conséquences avec cohérence. Garde un ton immersif et laisse le joueur décider."),
        ("cre-poeme", "Poésie et chansons", "Vers, rimes et paroles",
         "Écris le poème ou la chanson demandé avec rimes et rythme travaillés, dans le style indiqué. "
         "Propose une variante si l'utilisateur veut un autre ton."),
        ("cre-nom", "Trouver un nom", "Noms de projets et de marques",
         "Propose vingt noms originaux, courts et faciles à prononcer, en indiquant l'idée derrière "
         "chacun. Rappelle de vérifier la disponibilité du nom."),
        ("cre-personnage", "Créer un personnage", "Fiches de personnages",
         "Crée un personnage détaillé : apparence, personnalité, passé, désir, faiblesse et une réplique "
         "typique. Garde-le cohérent avec l'univers décrit."),
        ("cre-humour", "Humour", "Blagues et jeux de mots",
         "Propose de l'humour bienveillant et adapté au contexte, sans moquerie envers des groupes de "
         "personnes. Donne plusieurs variantes."),
        ("cre-reseaux", "Publications réseaux sociaux", "Posts adaptés à chaque réseau",
         "Rédige des publications adaptées au réseau visé (longueur, ton, hashtags raisonnables) avec "
         "une accroche forte et un appel à l'action clair."),
    ]},
    {"id": "assistant", "name": "Style de l'assistant", "icon": "🎛️",
     "desc": "Régler la façon de répondre de l'IA.", "skills": [
        ("sty-concis", "Réponses courtes", "Va droit au but",
         "Réponds de façon concise : la réponse d'abord, puis seulement les détails indispensables. "
         "Pas d'introduction ni de répétition."),
        ("sty-detaille", "Réponses détaillées", "Explications approfondies",
         "Réponds de manière détaillée et structurée, avec des titres, des exemples et les nuances "
         "importantes."),
        ("sty-francais", "Toujours en français", "Répond en français",
         "Réponds toujours en français, même si la question ou les documents sont dans une autre "
         "langue, sauf demande contraire."),
        ("sty-honnete", "Honnêteté", "Admet ce qu'il ne sait pas",
         "Si tu n'es pas sûr ou si tu ne sais pas, dis-le clairement plutôt que d'inventer. Distingue "
         "ce qui est certain de ce qui est une supposition."),
        ("sty-questions", "Poser des questions d'abord", "Clarifie avant de répondre",
         "Si la demande est ambiguë ou incomplète, pose d'abord une à trois questions précises avant de "
         "répondre longuement."),
        ("sty-tutoiement", "Tutoiement", "Ton amical",
         "Tutoie l'utilisateur et adopte un ton chaleureux et décontracté, tout en restant précis."),
        ("sty-pro", "Ton professionnel", "Vouvoiement et sobriété",
         "Vouvoie l'utilisateur et adopte un ton professionnel, courtois et sobre, sans familiarité."),
        ("sty-sources", "Citer ses sources", "Indique d'où vient l'information",
         "Quand des informations d'internet ou de documents joints sont fournies, appuie-toi dessus et "
         "indique clairement de quelle source vient chaque information importante."),
    ]},
]
