"""Español."""

MESSAGES: dict[str, str] = {
    "start.greeting": (
        "👋 ¡Hola! Soy el bot de horarios de la NCFU.\n\n"
        "Pregúntame en lenguaje natural:\n"
        "  • <i>Horario de ISS-b-o-22-3 esta semana</i>\n"
        "  • <i>¿Dónde está la clase de Podzolko en 5 minutos?</i>\n"
        "  • <i>Aulas libres en el edificio 11</i>\n"
        "  • <i>¿Qué tiene ahora el grupo AIS-b-o-25-1?</i>\n\n"
        "📋 <b>Comandos:</b>\n"
        "  /me         — panel personal 👤\n"
        "  /miniapp    — horario en la app 📅\n"
        "  /grades     — mis notas de eCampus\n"
        "  /stats      — estadísticas 📊\n"
        "  /classmates — compañeros de clase 👥\n"
        "  /teacher    — buscar un profesor\n"
        "  /help       — ayuda completa"
    ),
    "start.login_welcome": "👋 ¡Hola, {name}!\n\n🔐 <b>Nueva forma de iniciar sesión</b>\n\n1. Abre <a href=\"{web_url}/profile\">{web_url}/profile</a>\n2. Pulsa <b>«Iniciar sesión con Telegram»</b>\n3. Envíame el <b>código de 6 dígitos</b> que aparece\n4. Confirma — la página se actualizará automáticamente ✨",

    "help.full": (
        "📖 <b>Ayuda del bot de horarios NCFU</b>\n\n"
        "Pregunta en lenguaje natural:\n\n"
        "📅 <b>Horario:</b>\n"
        "  <i>Horario de ISS-b-o-22-3</i>\n"
        "  <i>¿Qué tiene el grupo AIS25 mañana?</i>\n\n"
        "👤 <b>Profesor:</b>\n"
        "  <i>¿Dónde está Podzolko ahora?</i>  ·  <i>Horario de Ivanov</i>\n\n"
        "🚪 <b>Aulas:</b>\n"
        "  <i>Aulas libres ahora mismo</i>\n\n"
        "📋 <b>Comandos:</b>\n"
        "  /me          — panel personal 👤\n"
        "  /miniapp     — horario en la app 📅\n"
        "  /grades      — mis notas de eCampus\n"
        "  /stats       — estadísticas académicas 📊\n"
        "  /subjects    — lista de asignaturas\n"
        "  /classmates  — mis compañeros 👥\n"
        "  /teacher     — buscar un profesor\n"
        "  /ecampus     — estado de eCampus\n"
        "  /limit       — límite de consultas\n"
        "  /language    — idioma de la interfaz 🌐\n"
        "  /support     — soporte\n"
        "  /suggest     — sugerir una idea\n\n"
        "💡 <i>En grupos, mencióname: @botname tu consulta</i>"
    ),
    "help.quick": (
        "📖 <b>Ayuda rápida</b>\n\n"
        "/me       — esta pantalla\n"
        "/grades   — notas de eCampus\n"
        "/stats    — estadísticas (elegir semestre)\n"
        "/subjects — lista de asignaturas\n"
        "/teacher  — buscar un profesor\n"
        "/classmates — compañeros de clase\n"
        "/limit    — límite de consultas\n"
        "/miniapp  — abrir la app\n"
        "/help     — ayuda completa"
    ),

    "group_welcome.text": (
        "👋 ¡Hola! Encantado de unirme a <b>{chat_title}</b>!\n\n"
        "📌 <b>Lo que puedo hacer:</b>\n"
        "  • Horario de un grupo, profesor o aula\n"
        "  • Aulas libres ahora mismo\n"
        "  • Buscar profesores y grupos\n\n"
        "💬 <b>Cómo hablarme:</b>\n"
        "  Mencióname: <code>@{bot_username} horario ISS-b-o-22-3</code>\n"
        "  O usa comandos:\n"
        "  /help — todo lo que puedo hacer\n"
        "  /miniapp — horario en la app 📅\n\n"
        "🔕 <i>No sigo todo el chat — solo respondo a menciones y comandos.</i>"
    ),
    "group_welcome.default_title": "este grupo",
    "common.open_schedule_button": "📅 Abrir horario",

    "mykey.disabled": "El comando /mykey está desactivado.",

    "roles.role.admin": "Administrador",
    "roles.role.moderator": "Moderador",
    "roles.role.vip": "VIP",
    "roles.role.beta": "Probador beta",
    "roles.role.user": "Usuario",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>Roles:</b>",
    "roles.privileges_label": "\n🔓 <b>Privilegios:</b>",
    "roles.priv_admin_panel": "⚙️ <b>Panel de administración</b> → <a href=\"{url}\">abrir</a>",
    "roles.priv_beta": "🧪 <b>Acceso beta</b> — filtros de horario ampliados",
    "roles.priv_floorplan_edit": "🗺 <b>Edición</b> de planos de planta",
    "roles.priv_floorplan_view": "🗺 <b>Visualización</b> de planos de planta",
    "roles.priv_personal_limit": "📊 <b>Límite personal</b>: {limit} consultas / período",
    "roles.profile_link": "\n💼 <b>Panel personal:</b> <a href=\"{url}\">abrir</a>",

    "suggest.prompt": (
        "💡 <b>Sugerencias e ideas</b>\n\n"
        "¿Tienes una idea para mejorar el bot o el horario?\n"
        "Escríbela después del comando:\n\n"
        "<code>/suggest Tu idea aquí</code>\n\n"
        "<i>Ejemplo: /suggest Añadir un recordatorio 10 minutos antes de clase</i>"
    ),
    "suggest.accepted": "✅ <b>¡Sugerencia recibida!</b>\n\nGracias, tu idea ayudará a mejorar el bot.\nNúmero: <code>{ticket_id}</code>\n",

    "about.text": (
        "🎓 <b>Bot de horarios de la NCFU</b>\n\n"
        "Un asistente inteligente para estudiantes y profesores "
        "de la Universidad Federal del Cáucaso Norte.\n\n"
        "📌 <b>Funciones:</b>\n"
        "  • Horario de grupos, profesores, aulas\n"
        "  • Aulas libres en tiempo real\n"
        "  • Búsqueda de grupos y profesores\n"
        "  • Mini App con el horario completo 📅\n\n"
        "🔗 <b>Enlaces:</b>\n"
        "  • <a href=\"{miniapp_url}\">Mini App del horario</a>\n"
        "🛠 <b>Versión:</b> 2.0\n"
        "💬 Preguntas y sugerencias: /support · /suggest"
    ),

    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — el horario completo en una app\n\n"
        "• Búsqueda flexible por grupo, profesor, aula\n"
        "• Aulas libres en tiempo real\n"
        "• Planos de planta de los edificios\n"
        "• Favoritos y configuración personal\n\n"
        "Pulsa el botón de abajo 👇"
    ),

    "support.prompt": "📬 <b>Soporte</b>\n\nEscribe tu pregunta después del comando:\n<code>/support Tu pregunta aquí</code>",
    "support.accepted": "✅ <b>Solicitud recibida</b>\n\nTe responderemos lo antes posible.\nNúmero de ticket: <code>{ticket_id}</code>",

    "limit.header": "📊 <b>Límite de {scope}</b>",
    "limit.scope_private": "consultas personales",
    "limit.scope_chat": "consultas en este chat",
    "limit.used": "✅ Usadas: <b>{used}</b>",
    "limit.remaining": "💬 Restantes: <b>{remaining}</b>",
    "limit.max": "🏁 Máximo: <b>{cap}</b>",
    "limit.reset_in": "🔄 Se reinicia en: <b>{reset_str}</b>",
    "limit.reset_done": "🔄 El límite ya se reinició — puedes usarlo de nuevo",
    "limit.exhausted_note": "<i>Límite agotado. Espera el reinicio o contacta a un administrador.</i>",
    "limit.normal_note": "<i>Este límite cuenta las consultas a la IA (horario, búsqueda). /start, /help y otros comandos no cuentan.</i>",

    "login.instructions": (
        "🔐 <b>Iniciar sesión en el sitio</b>\n\n"
        "1. Abre <a href=\"{web_url}/profile\">{web_url}/profile</a>\n"
        "2. Pulsa <b>«Iniciar sesión con Telegram»</b>\n"
        "3. Verás un <b>código de 6 letras</b> (latinas mayúsculas)\n"
        "4. Envíalo con <code>/code XXXXXX</code>\n"
        "5. Confirma — la página se actualizará automáticamente\n\n"
        "💡 O simplemente escribe <code>/code</code> y el código, separados por un espacio."
    ),
    "login.code_missing": "❓ Indica el código después del comando:\n<code>/code XXXXXX</code>\n\nEl código aparece en el sitio al pulsar «Iniciar sesión con Telegram».",
    "login.code_invalid_format": "❌ El código debe tener <b>6 letras mayúsculas y números</b>.\nEjemplo: <code>/code ABCDEF</code>",
    "login.account_blocked": "❌ Tu cuenta está bloqueada.",
    "login.server_error": "⚠️ Error del servidor. Inténtalo más tarde.",
    "login.code_error": "❌ <b>{error}</b>\n\nRevisa el código en el sitio y vuelve a intentarlo.\nEl código es válido durante <b>3 minutos</b>.",
    "login.code_error_default": "Código incorrecto o caducado",
    "login.code_error_server": "Error del servidor",
    "login.confirm_prompt": "🔐 <b>Confirmar inicio de sesión</b>\n\n¡Hola, {name}! Alguien está iniciando sesión en el sitio con tu cuenta.\n\n¿Confirmar el inicio de sesión?",
    "login.confirm_button": "✅ Confirmar inicio de sesión",
    "login.cancel_button": "❌ Cancelar",
    "login.cancelled": "❌ <b>Inicio de sesión cancelado.</b>\n\nSi no fuiste tú, no te preocupes — el enlace ya no es válido.",
    "login.cancelled_toast": "Inicio de sesión cancelado",
    "login.confirm_error": "⚠️ <b>Error de confirmación.</b>\n\nLa sesión puede haber caducado. Intenta iniciar sesión de nuevo.",
    "login.confirm_error_toast": "Error, inténtalo de nuevo",
    "login.confirmed": "✅ <b>¡Inicio de sesión confirmado!</b>\n\nLa página del sitio se actualizará automáticamente.",
    "login.confirmed_toast": "Sesión iniciada ✅",
    "login.default_name": "usuario",

    "disambig.stale_data": "⏱ Los datos están desactualizados. Vuelve a intentarlo.",
    "disambig.stale_button": "⚠️ Botón desactualizado. Vuelve a intentarlo.",
    "disambig.expired": "⏱ Tiempo de selección agotado. Vuelve a intentarlo.",
    "disambig.loading": "⏳ Cargando horario…",
    "disambig.unknown_intent": "❓ Tipo de consulta desconocido.",
    "disambig.error": "❌ Error al cargar el horario.\n<code>{eid}</code>",
    "disambig.format_error": "❌ Error al procesar el horario.",
    "disambig.day_of": "Día {idx} de {total}",
    "disambig.prev_page": "◀ Ant.",
    "disambig.next_page": "Sig. ▶",
    "disambig.group_label": "grupo #{id}",
    "disambig.room_label": "aula #{id}",
    "disambig.schedule_title": "Horario · {title}",

    "feedback.error_toast": "⚠️ Error",
    "feedback.already_rated_toast": "Ya valorado ✓",
    "feedback.save_failed_toast": "⚠️ No se pudo guardar la valoración",
    "feedback.thanks_toast": "{icon} Valoración guardada, ¡gracias!",

    "classmates.profile_not_found": "👤 No se encontró tu perfil.",
    "classmates.no_group": "👥 <b>Grupo no configurado</b>\n\nConfigura tu perfil en el sitio para ver a tus compañeros.",
    "classmates.query_error": "❌ Error al obtener la lista de compañeros.",
    "classmates.header": "👥 <b>Compañeros · {group_label}</b>\n",
    "classmates.registered_count": "<i>Registrados: {count}</i>\n",
    "classmates.none_registered": "👥 <b>Compañeros · {group_label}</b>\n\nTodavía nadie de tu grupo se ha registrado en el bot.",
    "classmates.group_fallback_label": "grupo #{id}",
    "classmates.more_suffix": "\n<i>…y más</i>",

    "teacher.search_prompt": "👤 <b>Buscar un profesor</b>\n\nEscribe el apellido (o parte de él):\n<code>/teacher Ivanov</code>",
    "teacher.search_error": "❌ Error de búsqueda.",
    "teacher.not_found": "🔍 No se encontró nada para <b>{query}</b>.\n\nPrueba con otro apellido.",
    "teacher.found_count": "🔍 Profesores encontrados: <b>{count}</b>\n\nElige uno:",
    "teacher.not_found_short": "❌ Profesor no encontrado.",
    "teacher.subjects_label": "\n📚 <b>Asignaturas:</b>",
    "teacher.more_subjects": "  <i>…y {count} más</i>",
    "teacher.lesson_types_label": "\n🗂 <b>Tipos de clase:</b> {types}",
    "teacher.groups_label": "\n👥 <b>Grupos ({count}):</b> {names}",
    "teacher.more_groups": "  <i>…y {count} más</i>",
    "teacher.lessons_in_db": "\n📊 Clases en la base de datos: <b>{count}</b>",
    "teacher.schedule_loaded": "🕐 Horario: <b>cargado</b>",
    "teacher.alltime_stats_label": "\n📈 <b>Estadísticas históricas:</b>",
    "teacher.total_lessons": "  Total de clases: <b>{count}</b>",
    "teacher.types_label": "  Tipos: {types}",
    "teacher.buildings_label": "  Edificios: {buildings}",
    "teacher.rooms_label": "  Aulas: {rooms}",
    "teacher.schedule_button": "📅 Horario",

    "me.profile_not_found": "👤 Perfil no encontrado.",
    "me.header": "👤 <b>Panel personal</b>\n",
    "me.role_student": "Estudiante",
    "me.role_teacher": "Profesor",
    "me.role_unset": "No configurado",
    "me.group_line": "\n📌 Grupo: <b>{group_name}</b>",
    "me.teacher_line": "\n📌 Profesor: <b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 Límite de consultas: <code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 Mi horario",
    "me.miniapp_button": "📱 Horario (app)",
    "me.subjects_button": "📚 Asignaturas",
    "me.stats_button": "📊 Estadísticas",
    "me.classmates_button": "👥 Compañeros",
    "me.my_lessons_button": "📈 Mis clases",
    "me.profile_button": "⚙️ Perfil",
    "me.map_button": "🗺 Mapa",
    "me.limit_button": "💬 Límite de consultas",
    "me.help_button": "❓ Ayuda",
    "me.no_ecampus_data": "📭 Sin datos de eCampus.",
    "me.stats_choose_period": "📊 <b>Estadísticas académicas</b>\n\nElige un período:",

    "grades.not_connected": "📚 <b>eCampus no conectado</b>\n\nConecta tu cuenta de eCampus en <b>Perfil → eCampus</b> en el sitio o en la mini app.",
    "grades.sync_running": "⏳ La sincronización con eCampus sigue en curso — los datos se están actualizando.\nInténtalo de nuevo en un minuto.",
    "grades.empty": "📭 Los datos de eCampus todavía están vacíos.\nPulsa «Actualizar» en la mini app o espera la sincronización automática.",
    "grades.semester_label": "Semestre {n}",
    "grades.current_semester_label": "Semestre actual",
    "grades.no_grades": "📭 <b>Sin notas</b> ({sem_label})\n\nLas notas aparecerán cuando el profesor las registre.",
    "grades.header": "📊 <b>Notas · {sem_label}</b>\n",
    "grades.total": "\n<i>Total de notas: {count}</i>",
    "grades.page_suffix": "\n\n({page}/{total})",

    "stats.not_connected_short": "📚 <b>eCampus no conectado</b>\n\nConecta tu cuenta en Perfil en el sitio.",
    "stats.no_data": "📭 Sin datos de eCampus. Actualiza la sincronización.",
    "stats.no_term_data": "📭 Sin datos para este semestre.",
    "stats.all_time_suffix": " · Todo el tiempo",
    "stats.term_fallback": " · sem.{id}",
    "stats.header": "📊 <b>Estadísticas académicas{suffix}</b>\n",
    "stats.subjects_count": "📚 Asignaturas:   <b>{count}</b>",
    "stats.grades_count": "✏️  Notas:        <b>{count}</b>",
    "stats.exams_count": "🎓 Exámenes:    <b>{count}</b>",
    "stats.credits_count": "📝 Evaluaciones: <b>{count}</b>",
    "stats.rating": "⭐ Puntuación:  {icon} <b>{avg:.1f}</b> / {max:.1f} ({pct:.0f}%)",
    "stats.updated_at": "\n<i>Actualizado: {dt}</i>",
    "stats.choose_period": "📊 <b>Estadísticas académicas</b>\n\nElige un período:",
    "stats.all_time_button": "📊 Todo el tiempo",

    "subjects.not_connected": "📚 <b>eCampus no conectado</b>\n\nConecta tu cuenta en Perfil en el sitio.",
    "subjects.no_data": "📭 Sin datos. Actualiza la sincronización.",
    "subjects.none_for_term": "📭 No se encontraron asignaturas ({sem_label}).",
    "subjects.header": "📚 <b>Asignaturas · {sem_label}</b>  ({count})\n",
    "subjects.no_type_data": "sin datos",
    "subjects.rating_line": "\n    {icon} Puntuación: <b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>Examen</i>",
    "subjects.credit_tag": " 📝<i>Evaluación</i>",

    "ecampus.not_connected": (
        "📚 <b>NCFU eCampus</b>\n\n"
        "La cuenta <b>no está conectada</b>.\n\n"
        "Conéctala en <b>Perfil → eCampus</b> en el sitio "
        "o en la mini app para obtener:\n"
        "  • Una lista de asignaturas y notas\n"
        "  • Estadísticas académicas\n"
        "  • Puntuaciones de cada curso\n\n"
        "Comandos (tras conectar):\n"
        "  /grades   — mis notas\n"
        "  /stats    — estadísticas académicas\n"
        "  /subjects — lista de asignaturas"
    ),
    "ecampus.status_ok": "✅ Sincronizado",
    "ecampus.status_running": "⏳ Sincronizando...",
    "ecampus.status_error": "❌ Error de sincronización",
    "ecampus.status_pending": "🕐 Esperando sincronización",
    "ecampus.header": "📚 <b>NCFU eCampus</b>\n",
    "ecampus.status_line": "🔗 Estado: {status}",
    "ecampus.subjects_count": "📦 Asignaturas: <b>{count}</b>",
    "ecampus.grades_count": "✏️  Notas: <b>{count}</b>",
    "ecampus.updated_at": "🕐 Actualizado: <b>{dt}</b>",
    "ecampus.current_term": "\n📅 Semestre actual: <b>{term}</b>",
    "ecampus.term_subjects": "   Asignaturas: <b>{count}</b>",
    "ecampus.term_grades": "   Notas: <b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>Comandos:</b>\n"
        "  /grades   — mis notas del semestre actual\n"
        "  /grades 2 — notas del semestre 2\n"
        "  /stats    — estadísticas completas\n"
        "  /subjects — lista de asignaturas"
    ),

    "ai.empty_message": "Escribe algo 🙂",
    "ai.processing": "⏳ Procesando...",
    "ai.unknown_request": "❓ Consulta desconocida.",
    "ai.parse_failed": "❌ No se pudo entender la consulta. Intenta reformularla.",
    "ai.execution_error": "❌ Error al ejecutar la consulta.\n<code>{eid}</code>",
    "ai.processing_error": "❌ Error al procesar la consulta.",

    "language.prompt": "🌐 <b>Elige el idioma de la interfaz</b>\n\nEsta elección se sincroniza con el sitio web y la mini app.",
    "language.saved": "✅ Idioma cambiado a <b>{name}</b>.",
    "language.save_failed": "⚠️ No se pudo guardar el idioma. Inténtalo de nuevo.",

    "cmd.start": "Empezar",
    "cmd.me": "Panel personal 👤",
    "cmd.help": "Ayuda",
    "cmd.miniapp": "Abrir horario (Mini App) 📅",
    "cmd.grades": "Mis notas de eCampus",
    "cmd.stats": "Estadísticas académicas 📊",
    "cmd.subjects": "Lista de asignaturas",
    "cmd.classmates": "Mis compañeros 👥",
    "cmd.teacher": "Buscar un profesor 👤",
    "cmd.ecampus": "Estado de eCampus",
    "cmd.limit": "Límite de consultas",
    "cmd.language": "Idioma de la interfaz 🌐",
    "cmd.login": "Iniciar sesión en el sitio",
    "cmd.code": "Introducir código (/code XXXXXX)",
    "cmd.support": "Soporte",
    "cmd.suggest": "Sugerir una idea",
    "cmd.about": "Acerca del bot",
}
