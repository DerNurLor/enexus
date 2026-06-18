"""Français."""

MESSAGES: dict[str, str] = {
    "start.greeting": (
        "👋 Bonjour ! Je suis le bot d'emploi du temps de la NCFU.\n\n"
        "Posez-moi vos questions en langage naturel :\n"
        "  • <i>Emploi du temps de ISS-b-o-22-3 cette semaine</i>\n"
        "  • <i>Où est le cours de Podzolko dans 5 minutes ?</i>\n"
        "  • <i>Salles libres dans le bâtiment 11</i>\n"
        "  • <i>Que fait le groupe AIS-b-o-25-1 maintenant ?</i>\n\n"
        "📋 <b>Commandes :</b>\n"
        "  /me         — espace personnel 👤\n"
        "  /miniapp    — emploi du temps dans l'appli 📅\n"
        "  /grades     — mes notes eCampus\n"
        "  /stats      — statistiques 📊\n"
        "  /classmates — camarades de classe 👥\n"
        "  /teacher    — trouver un enseignant\n"
        "  /help       — aide complète"
    ),
    "start.login_welcome": "👋 Bonjour {name} !\n\n🔐 <b>Nouvelle méthode de connexion</b>\n\n1. Ouvrez <a href=\"{web_url}/profile\">{web_url}/profile</a>\n2. Appuyez sur <b>« Se connecter avec Telegram »</b>\n3. Envoyez-moi le <b>code à 6 chiffres</b> affiché\n4. Confirmez — la page se rafraîchira automatiquement ✨",

    "help.full": (
        "📖 <b>Aide du bot d'emploi du temps NCFU</b>\n\n"
        "Posez simplement votre question en langage naturel :\n\n"
        "📅 <b>Emploi du temps :</b>\n"
        "  <i>Emploi du temps de ISS-b-o-22-3</i>\n"
        "  <i>Qu'a le groupe AIS25 demain ?</i>\n\n"
        "👤 <b>Enseignant :</b>\n"
        "  <i>Où est Podzolko maintenant ?</i>  ·  <i>Emploi du temps d'Ivanov</i>\n\n"
        "🚪 <b>Salles :</b>\n"
        "  <i>Salles libres actuellement</i>\n\n"
        "📋 <b>Commandes :</b>\n"
        "  /me          — espace personnel 👤\n"
        "  /miniapp     — emploi du temps dans l'appli 📅\n"
        "  /grades      — mes notes eCampus\n"
        "  /stats       — statistiques académiques 📊\n"
        "  /subjects    — liste des matières\n"
        "  /classmates  — mes camarades 👥\n"
        "  /teacher     — trouver un enseignant\n"
        "  /ecampus     — statut eCampus\n"
        "  /limit       — limite de requêtes\n"
        "  /language    — langue de l'interface 🌐\n"
        "  /support     — assistance\n"
        "  /suggest     — proposer une idée\n\n"
        "💡 <i>Dans les groupes, mentionnez-moi : @botname votre requête</i>"
    ),
    "help.quick": (
        "📖 <b>Aide rapide</b>\n\n"
        "/me       — cet écran\n"
        "/grades   — notes eCampus\n"
        "/stats    — statistiques (choix du semestre)\n"
        "/subjects — liste des matières\n"
        "/teacher  — trouver un enseignant\n"
        "/classmates — camarades de classe\n"
        "/limit    — limite de requêtes\n"
        "/miniapp  — ouvrir l'appli\n"
        "/help     — aide complète"
    ),

    "group_welcome.text": (
        "👋 Bonjour ! Heureux de rejoindre <b>{chat_title}</b> !\n\n"
        "📌 <b>Ce que je sais faire :</b>\n"
        "  • Emploi du temps d'un groupe, enseignant ou salle\n"
        "  • Salles libres en ce moment\n"
        "  • Recherche d'enseignants et de groupes\n\n"
        "💬 <b>Comment me parler :</b>\n"
        "  Mentionnez-moi : <code>@{bot_username} emploi du temps ISS-b-o-22-3</code>\n"
        "  Ou utilisez les commandes :\n"
        "  /help — toutes mes fonctionnalités\n"
        "  /miniapp — emploi du temps dans l'appli 📅\n\n"
        "🔕 <i>Je ne suis pas tout le chat — je réponds seulement aux mentions et commandes.</i>"
    ),
    "group_welcome.default_title": "ce groupe",
    "common.open_schedule_button": "📅 Ouvrir l'emploi du temps",

    "mykey.disabled": "La commande /mykey est désactivée.",

    "roles.role.admin": "Administrateur",
    "roles.role.moderator": "Modérateur",
    "roles.role.vip": "VIP",
    "roles.role.beta": "Testeur bêta",
    "roles.role.user": "Utilisateur",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>Rôles :</b>",
    "roles.privileges_label": "\n🔓 <b>Privilèges :</b>",
    "roles.priv_admin_panel": "⚙️ <b>Panneau d'administration</b> → <a href=\"{url}\">ouvrir</a>",
    "roles.priv_beta": "🧪 <b>Accès bêta</b> — filtres d'emploi du temps étendus",
    "roles.priv_floorplan_edit": "🗺 <b>Modification</b> des plans d'étage",
    "roles.priv_floorplan_view": "🗺 <b>Consultation</b> des plans d'étage",
    "roles.priv_personal_limit": "📊 <b>Limite personnelle</b> : {limit} requêtes / période",
    "roles.profile_link": "\n💼 <b>Espace personnel :</b> <a href=\"{url}\">ouvrir</a>",

    "suggest.prompt": (
        "💡 <b>Suggestions et idées</b>\n\n"
        "Une idée pour améliorer le bot ou l'emploi du temps ?\n"
        "Écrivez-la après la commande :\n\n"
        "<code>/suggest Votre idée ici</code>\n\n"
        "<i>Exemple : /suggest Ajouter un rappel 10 minutes avant le cours</i>"
    ),
    "suggest.accepted": "✅ <b>Suggestion reçue !</b>\n\nMerci, votre idée aidera à améliorer le bot.\nNuméro : <code>{ticket_id}</code>\n",

    "about.text": (
        "🎓 <b>Bot d'emploi du temps NCFU</b>\n\n"
        "Un assistant intelligent pour les étudiants et le personnel "
        "de l'Université fédérale du Caucase du Nord.\n\n"
        "📌 <b>Fonctionnalités :</b>\n"
        "  • Emploi du temps des groupes, enseignants, salles\n"
        "  • Salles libres en temps réel\n"
        "  • Recherche de groupes et d'enseignants\n"
        "  • Mini App avec l'emploi du temps complet 📅\n\n"
        "🔗 <b>Liens :</b>\n"
        "  • <a href=\"{miniapp_url}\">Mini App de l'emploi du temps</a>\n"
        "🛠 <b>Version :</b> 2.0\n"
        "💬 Questions et suggestions : /support · /suggest"
    ),

    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — l'emploi du temps complet dans une appli\n\n"
        "• Recherche flexible par groupe, enseignant, salle\n"
        "• Salles libres en temps réel\n"
        "• Plans d'étage des bâtiments\n"
        "• Favoris et réglages personnels\n\n"
        "Appuyez sur le bouton ci-dessous 👇"
    ),

    "support.prompt": "📬 <b>Assistance</b>\n\nÉcrivez votre question après la commande :\n<code>/support Votre question ici</code>",
    "support.accepted": "✅ <b>Demande reçue</b>\n\nNous vous répondrons dès que possible.\nNuméro de ticket : <code>{ticket_id}</code>",

    "limit.header": "📊 <b>Limite de {scope}</b>",
    "limit.scope_private": "requêtes personnelles",
    "limit.scope_chat": "requêtes dans cette discussion",
    "limit.used": "✅ Utilisées : <b>{used}</b>",
    "limit.remaining": "💬 Restantes : <b>{remaining}</b>",
    "limit.max": "🏁 Maximum : <b>{cap}</b>",
    "limit.reset_in": "🔄 Réinitialisation dans : <b>{reset_str}</b>",
    "limit.reset_done": "🔄 La limite a déjà été réinitialisée — vous pouvez l'utiliser à nouveau",
    "limit.exhausted_note": "<i>Limite atteinte. Attendez la réinitialisation ou contactez un administrateur.</i>",
    "limit.normal_note": "<i>Cette limite compte les requêtes à l'IA (emploi du temps, recherche). /start, /help et les autres commandes ne comptent pas.</i>",

    "login.instructions": (
        "🔐 <b>Connexion au site</b>\n\n"
        "1. Ouvrez <a href=\"{web_url}/profile\">{web_url}/profile</a>\n"
        "2. Appuyez sur <b>« Se connecter avec Telegram »</b>\n"
        "3. Un <b>code à 6 lettres</b> (majuscules latines) s'affichera\n"
        "4. Envoyez-le avec <code>/code XXXXXX</code>\n"
        "5. Confirmez — la page se rafraîchira automatiquement\n\n"
        "💡 Ou tapez simplement <code>/code</code> puis le code, séparés par un espace."
    ),
    "login.code_missing": "❓ Indiquez le code après la commande :\n<code>/code XXXXXX</code>\n\nLe code s'affiche sur le site lorsque vous appuyez sur « Se connecter avec Telegram ».",
    "login.code_invalid_format": "❌ Le code doit comporter <b>6 lettres majuscules et chiffres</b>.\nExemple : <code>/code ABCDEF</code>",
    "login.account_blocked": "❌ Votre compte est bloqué.",
    "login.server_error": "⚠️ Erreur serveur. Réessayez plus tard.",
    "login.code_error": "❌ <b>{error}</b>\n\nVérifiez le code sur le site et réessayez.\nLe code est valable <b>3 minutes</b>.",
    "login.code_error_default": "Code invalide ou expiré",
    "login.code_error_server": "Erreur serveur",
    "login.confirm_prompt": "🔐 <b>Confirmer la connexion</b>\n\nBonjour {name} ! Quelqu'un se connecte au site avec votre compte.\n\nConfirmer la connexion ?",
    "login.confirm_button": "✅ Confirmer la connexion",
    "login.cancel_button": "❌ Annuler",
    "login.cancelled": "❌ <b>Connexion annulée.</b>\n\nSi ce n'était pas vous, pas de souci — le lien n'est déjà plus valide.",
    "login.cancelled_toast": "Connexion annulée",
    "login.confirm_error": "⚠️ <b>Erreur de confirmation.</b>\n\nLa session a peut-être expiré. Réessayez de vous connecter.",
    "login.confirm_error_toast": "Erreur, réessayez",
    "login.confirmed": "✅ <b>Connexion confirmée !</b>\n\nLa page du site se rafraîchira automatiquement.",
    "login.confirmed_toast": "Connexion réussie ✅",
    "login.default_name": "utilisateur",

    "disambig.stale_data": "⏱ Données obsolètes. Veuillez réessayer.",
    "disambig.stale_button": "⚠️ Bouton obsolète. Veuillez réessayer.",
    "disambig.expired": "⏱ Délai de sélection expiré. Veuillez réessayer.",
    "disambig.loading": "⏳ Chargement de l'emploi du temps…",
    "disambig.unknown_intent": "❓ Type de requête inconnu.",
    "disambig.error": "❌ Erreur lors du chargement de l'emploi du temps.\n<code>{eid}</code>",
    "disambig.format_error": "❌ Erreur de traitement de l'emploi du temps.",
    "disambig.day_of": "Jour {idx} sur {total}",
    "disambig.prev_page": "◀ Préc.",
    "disambig.next_page": "Suiv. ▶",
    "disambig.group_label": "groupe #{id}",
    "disambig.room_label": "salle #{id}",
    "disambig.schedule_title": "Emploi du temps · {title}",

    "feedback.error_toast": "⚠️ Erreur",
    "feedback.already_rated_toast": "Déjà noté ✓",
    "feedback.save_failed_toast": "⚠️ Impossible d'enregistrer la note",
    "feedback.thanks_toast": "{icon} Note enregistrée, merci !",

    "classmates.profile_not_found": "👤 Impossible de trouver votre profil.",
    "classmates.no_group": "👥 <b>Groupe non configuré</b>\n\nConfigurez votre profil sur le site pour voir vos camarades.",
    "classmates.query_error": "❌ Erreur lors de la récupération de la liste des camarades.",
    "classmates.header": "👥 <b>Camarades · {group_label}</b>\n",
    "classmates.registered_count": "<i>Inscrits : {count}</i>\n",
    "classmates.none_registered": "👥 <b>Camarades · {group_label}</b>\n\nPersonne de votre groupe n'est encore inscrit au bot.",
    "classmates.group_fallback_label": "groupe #{id}",
    "classmates.more_suffix": "\n<i>…et plus encore</i>",

    "teacher.search_prompt": "👤 <b>Rechercher un enseignant</b>\n\nÉcrivez le nom de famille (ou une partie) :\n<code>/teacher Ivanov</code>",
    "teacher.search_error": "❌ Erreur de recherche.",
    "teacher.not_found": "🔍 Aucun résultat pour <b>{query}</b>.\n\nEssayez un autre nom.",
    "teacher.found_count": "🔍 Enseignants trouvés : <b>{count}</b>\n\nChoisissez :",
    "teacher.not_found_short": "❌ Enseignant non trouvé.",
    "teacher.subjects_label": "\n📚 <b>Matières :</b>",
    "teacher.more_subjects": "  <i>…et {count} de plus</i>",
    "teacher.lesson_types_label": "\n🗂 <b>Types de cours :</b> {types}",
    "teacher.groups_label": "\n👥 <b>Groupes ({count}) :</b> {names}",
    "teacher.more_groups": "  <i>…et {count} de plus</i>",
    "teacher.lessons_in_db": "\n📊 Cours dans la base : <b>{count}</b>",
    "teacher.schedule_loaded": "🕐 Emploi du temps : <b>chargé</b>",
    "teacher.alltime_stats_label": "\n📈 <b>Statistiques globales :</b>",
    "teacher.total_lessons": "  Total des cours : <b>{count}</b>",
    "teacher.types_label": "  Types : {types}",
    "teacher.buildings_label": "  Bâtiments : {buildings}",
    "teacher.rooms_label": "  Salles : {rooms}",
    "teacher.schedule_button": "📅 Emploi du temps",

    "me.profile_not_found": "👤 Profil non trouvé.",
    "me.header": "👤 <b>Espace personnel</b>\n",
    "me.role_student": "Étudiant",
    "me.role_teacher": "Enseignant",
    "me.role_unset": "Non configuré",
    "me.group_line": "\n📌 Groupe : <b>{group_name}</b>",
    "me.teacher_line": "\n📌 Enseignant : <b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 Limite de requêtes : <code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 Mon emploi du temps",
    "me.miniapp_button": "📱 Emploi du temps (appli)",
    "me.subjects_button": "📚 Matières",
    "me.stats_button": "📊 Statistiques",
    "me.classmates_button": "👥 Camarades",
    "me.my_lessons_button": "📈 Mes cours",
    "me.profile_button": "⚙️ Profil",
    "me.map_button": "🗺 Carte",
    "me.limit_button": "💬 Limite de requêtes",
    "me.help_button": "❓ Aide",
    "me.no_ecampus_data": "📭 Aucune donnée eCampus.",
    "me.stats_choose_period": "📊 <b>Statistiques académiques</b>\n\nChoisissez une période :",

    "grades.not_connected": "📚 <b>eCampus non connecté</b>\n\nConnectez votre compte eCampus dans <b>Profil → eCampus</b> sur le site ou dans la mini app.",
    "grades.sync_running": "⏳ La synchronisation avec eCampus est encore en cours — les données se mettent à jour.\nRéessayez dans une minute.",
    "grades.empty": "📭 Les données eCampus sont encore vides.\nAppuyez sur « Actualiser » dans la mini app ou attendez la synchronisation automatique.",
    "grades.semester_label": "Semestre {n}",
    "grades.current_semester_label": "Semestre actuel",
    "grades.no_grades": "📭 <b>Aucune note</b> ({sem_label})\n\nLes notes apparaîtront une fois saisies par l'enseignant.",
    "grades.header": "📊 <b>Notes · {sem_label}</b>\n",
    "grades.total": "\n<i>Total des notes : {count}</i>",
    "grades.page_suffix": "\n\n({page}/{total})",

    "stats.not_connected_short": "📚 <b>eCampus non connecté</b>\n\nConnectez votre compte dans Profil sur le site.",
    "stats.no_data": "📭 Aucune donnée eCampus. Actualisez la synchronisation.",
    "stats.no_term_data": "📭 Aucune donnée pour ce semestre.",
    "stats.all_time_suffix": " · Toute la période",
    "stats.term_fallback": " · sem.{id}",
    "stats.header": "📊 <b>Statistiques académiques{suffix}</b>\n",
    "stats.subjects_count": "📚 Matières :    <b>{count}</b>",
    "stats.grades_count": "✏️  Notes :        <b>{count}</b>",
    "stats.exams_count": "🎓 Examens :    <b>{count}</b>",
    "stats.credits_count": "📝 Contrôles :   <b>{count}</b>",
    "stats.rating": "⭐ Note :       {icon} <b>{avg:.1f}</b> / {max:.1f} ({pct:.0f}%)",
    "stats.updated_at": "\n<i>Mis à jour : {dt}</i>",
    "stats.choose_period": "📊 <b>Statistiques académiques</b>\n\nChoisissez une période :",
    "stats.all_time_button": "📊 Toute la période",

    "subjects.not_connected": "📚 <b>eCampus non connecté</b>\n\nConnectez votre compte dans Profil sur le site.",
    "subjects.no_data": "📭 Aucune donnée. Actualisez la synchronisation.",
    "subjects.none_for_term": "📭 Aucune matière trouvée ({sem_label}).",
    "subjects.header": "📚 <b>Matières · {sem_label}</b>  ({count})\n",
    "subjects.no_type_data": "aucune donnée",
    "subjects.rating_line": "\n    {icon} Note : <b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>Examen</i>",
    "subjects.credit_tag": " 📝<i>Contrôle</i>",

    "ecampus.not_connected": (
        "📚 <b>NCFU eCampus</b>\n\n"
        "Le compte <b>n'est pas connecté</b>.\n\n"
        "Connectez-le dans <b>Profil → eCampus</b> sur le site "
        "ou dans la mini app pour obtenir :\n"
        "  • La liste des matières et des notes\n"
        "  • Les statistiques académiques\n"
        "  • Les notes de chaque cours\n\n"
        "Commandes (après connexion) :\n"
        "  /grades   — mes notes\n"
        "  /stats    — statistiques académiques\n"
        "  /subjects — liste des matières"
    ),
    "ecampus.status_ok": "✅ Synchronisé",
    "ecampus.status_running": "⏳ Synchronisation...",
    "ecampus.status_error": "❌ Erreur de synchronisation",
    "ecampus.status_pending": "🕐 En attente de synchronisation",
    "ecampus.header": "📚 <b>NCFU eCampus</b>\n",
    "ecampus.status_line": "🔗 Statut : {status}",
    "ecampus.subjects_count": "📦 Matières : <b>{count}</b>",
    "ecampus.grades_count": "✏️  Notes : <b>{count}</b>",
    "ecampus.updated_at": "🕐 Mis à jour : <b>{dt}</b>",
    "ecampus.current_term": "\n📅 Semestre actuel : <b>{term}</b>",
    "ecampus.term_subjects": "   Matières : <b>{count}</b>",
    "ecampus.term_grades": "   Notes : <b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>Commandes :</b>\n"
        "  /grades   — mes notes du semestre actuel\n"
        "  /grades 2 — notes du semestre 2\n"
        "  /stats    — statistiques complètes\n"
        "  /subjects — liste des matières"
    ),

    "ai.empty_message": "Écrivez quelque chose 🙂",
    "ai.processing": "⏳ Traitement en cours...",
    "ai.unknown_request": "❓ Requête inconnue.",
    "ai.parse_failed": "❌ Impossible de comprendre la requête. Essayez de la reformuler.",
    "ai.execution_error": "❌ Erreur lors de l'exécution de la requête.\n<code>{eid}</code>",
    "ai.processing_error": "❌ Erreur de traitement de la requête.",

    "language.prompt": "🌐 <b>Choisissez la langue de l'interface</b>\n\nCe choix est synchronisé avec le site web et la mini app.",
    "language.saved": "✅ Langue changée en <b>{name}</b>.",
    "language.save_failed": "⚠️ Impossible d'enregistrer la langue. Réessayez.",

    "cmd.start": "Démarrer",
    "cmd.me": "Espace personnel 👤",
    "cmd.help": "Aide",
    "cmd.miniapp": "Ouvrir l'emploi du temps (Mini App) 📅",
    "cmd.grades": "Mes notes eCampus",
    "cmd.stats": "Statistiques académiques 📊",
    "cmd.subjects": "Liste des matières",
    "cmd.classmates": "Mes camarades 👥",
    "cmd.teacher": "Trouver un enseignant 👤",
    "cmd.ecampus": "Statut eCampus",
    "cmd.limit": "Limite de requêtes",
    "cmd.language": "Langue de l'interface 🌐",
    "cmd.login": "Se connecter au site",
    "cmd.code": "Entrer le code (/code XXXXXX)",
    "cmd.support": "Assistance",
    "cmd.suggest": "Proposer une idée",
    "cmd.about": "À propos du bot",
}
