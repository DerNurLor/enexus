"""Қазақ тілі — ru.py негізінде жасалған аударма."""

MESSAGES: dict[str, str] = {
    # ── /start ───────────────────────────────────────────────────────────────
    "start.greeting": (
        "👋 Сәлем! Мен СКФУ кестесінің боты.\n\n"
        "Сұрағыңызды табиғи тілде жазыңыз:\n"
        "  • <i>ИСС-б-о-22-3 топтың осы аптадағы кестесі</i>\n"
        "  • <i>Подзолконың сабағы 5 минуттан кейін қайда?</i>\n"
        "  • <i>11-корпустағы бос аудиториялар</i>\n"
        "  • <i>АИС-б-о-25-1 тобында қазір не бар?</i>\n\n"
        "📋 <b>Командалар:</b>\n"
        "  /me         — жеке кабинет 👤\n"
        "  /miniapp    — қосымшадағы кесте 📅\n"
        "  /grades     — eCampus-тағы бағаларым\n"
        "  /stats      — статистика 📊\n"
        "  /classmates — топтастар 👥\n"
        "  /teacher    — оқытушыны табу\n"
        "  /help       — толық анықтама"
    ),
    "start.login_welcome": "👋 Сәлем, {name}!\n\n🔐 <b>Кіру тәсілі</b>\n\n1. <a href=\"{web_url}/profile\">{web_url}/profile</a> ашыңыз\n2. <b>«Telegram арқылы кіру»</b> түймесін басыңыз\n3. Көрсетілген <b>6 таңбалы кодты</b> маған жіберіңіз\n4. Растаңыз — бет өзі жаңарады ✨",

    # ── /help ────────────────────────────────────────────────────────────────
    "help.full": (
        "📖 <b>СКФУ кесте боты бойынша анықтама</b>\n\n"
        "Сұрағыңызды табиғи тілде жазыңыз:\n\n"
        "📅 <b>Кесте:</b>\n"
        "  <i>ИСС-б-о-22-3 кестесі</i>\n"
        "  <i>АИС25 тобында ертең не бар?</i>\n\n"
        "👤 <b>Оқытушы:</b>\n"
        "  <i>Подзолко қазір қайда?</i>  ·  <i>Иванов кестесі</i>\n\n"
        "🚪 <b>Аудиториялар:</b>\n"
        "  <i>Қазір бос аудиториялар</i>\n\n"
        "📋 <b>Командалар:</b>\n"
        "  /me          — жеке кабинет 👤\n"
        "  /miniapp     — қосымшадағы кесте 📅\n"
        "  /grades      — eCampus-тағы бағаларым\n"
        "  /stats       — үлгерім статистикасы 📊\n"
        "  /subjects    — пәндер тізімі\n"
        "  /classmates  — топтастарым 👥\n"
        "  /teacher     — оқытушыны табу\n"
        "  /ecampus     — eCampus күйі\n"
        "  /limit       — сұраулар шегі\n"
        "  /language    — интерфейс тілі 🌐\n"
        "  /support     — қолдау\n"
        "  /suggest     — идея ұсыну\n\n"
        "💡 <i>Топтарда мені атап шақырыңыз: @botname сұрақ</i>"
    ),
    "help.quick": (
        "📖 <b>Жылдам анықтама</b>\n\n"
        "/me       — осы экран\n"
        "/grades   — eCampus бағалары\n"
        "/stats    — статистика (семестрді таңдау)\n"
        "/subjects — пәндер тізімі\n"
        "/teacher  — оқытушыны іздеу\n"
        "/classmates — топтастар\n"
        "/limit    — сұраулар шегі\n"
        "/miniapp  — қосымшаны ашу\n"
        "/help     — толық анықтама"
    ),

    # ── Группа: приветствие при добавлении бота ─────────────────────────────────
    "group_welcome.text": (
        "👋 Сәлем! <b>{chat_title}</b> топқа қосылғаныма қуаныштымын!\n\n"
        "📌 <b>Мен не істей аламын:</b>\n"
        "  • Топтың, оқытушының, аудиторияның кестесі\n"
        "  • Қазір бос аудиториялар\n"
        "  • Оқытушылар мен топтар бойынша іздеу\n\n"
        "💬 <b>Қалай хабарласу керек:</b>\n"
        "  Мені атаңыз: <code>@{bot_username} ИСС-б-о-22-3 кестесі</code>\n"
        "  Немесе командаларды қолданыңыз:\n"
        "  /help — барлық мүмкіндіктер\n"
        "  /miniapp — қосымшадағы кесте 📅\n\n"
        "🔕 <i>Мен жалпы чатты бақыламаймын — тек атау мен командаларға жауап беремін.</i>"
    ),
    "group_welcome.default_title": "осы топ",
    "common.open_schedule_button": "📅 Кестені ашу",

    # ── /mykey (отключена) ───────────────────────────────────────────────────
    "mykey.disabled": "Команда /mykey өшірілген.",

    # ── /roles ───────────────────────────────────────────────────────────────
    "roles.role.admin": "Әкімші",
    "roles.role.moderator": "Модератор",
    "roles.role.vip": "VIP",
    "roles.role.beta": "Бета-тестер",
    "roles.role.user": "Пайдаланушы",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>Рөлдер:</b>",
    "roles.privileges_label": "\n🔓 <b>Артықшылықтар:</b>",
    "roles.priv_admin_panel": "⚙️ <b>Басқару тақтасы</b> → <a href=\"{url}\">ашу</a>",
    "roles.priv_beta": "🧪 <b>Бета-қолжетімділік</b> — кестенің кеңейтілген сүзгілері",
    "roles.priv_floorplan_edit": "🗺 Қабат жоспарларын <b>өңдеу</b>",
    "roles.priv_floorplan_view": "🗺 Қабат жоспарларын <b>көру</b>",
    "roles.priv_personal_limit": "📊 <b>Жеке шек</b>: {limit} сұрау / кезең",
    "roles.profile_link": "\n💼 <b>Жеке кабинет:</b> <a href=\"{url}\">ашу</a>",

    # ── /suggest ─────────────────────────────────────────────────────────────
    "suggest.prompt": (
        "💡 <b>Ұсыныстар мен идеялар</b>\n\n"
        "Боты немесе кестені жақсарту идеясы бар ма?\n"
        "Команда соңынан жазыңыз:\n\n"
        "<code>/suggest Сіздің идеяңыз осында</code>\n\n"
        "<i>Мысалы: /suggest Сабаққа 10 минут қалғанда хабарлама қосу</i>"
    ),
    "suggest.accepted": "✅ <b>Ұсыныс қабылданды!</b>\n\nРахмет, сіздің идеяңыз ботты жақсартуға көмектеседі.\nНөмір: <code>{ticket_id}</code>\n",

    # ── /about ───────────────────────────────────────────────────────────────
    "about.text": (
        "🎓 <b>СКФУ кесте боты</b>\n\n"
        "Солтүстік Кавказ федералды университетінің "
        "студенттері мен оқытушылары үшін ақылды көмекші.\n\n"
        "📌 <b>Мүмкіндіктер:</b>\n"
        "  • Топтардың, оқытушылардың, аудиториялардың кестесі\n"
        "  • Нақты уақыттағы бос аудиториялар\n"
        "  • Топтар мен оқытушылар бойынша іздеу\n"
        "  • Толық кестесі бар Mini App 📅\n\n"
        "🔗 <b>Сілтемелер:</b>\n"
        "  • <a href=\"{miniapp_url}\">Кесте Mini App</a>\n"
        "🛠 <b>Нұсқа:</b> 2.0\n"
        "💬 Сұрақтар мен ұсыныстар: /support · /suggest"
    ),

    # ── /miniapp ─────────────────────────────────────────────────────────────
    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — қосымшадағы толық кесте\n\n"
        "• Топ, оқытушы, аудитория бойынша икемді іздеу\n"
        "• Нақты уақыттағы бос аудиториялар\n"
        "• Корпустардың қабат жоспарлары\n"
        "• Таңдаулылар және жеке баптаулар\n\n"
        "Төмендегі түймені басыңыз 👇"
    ),

    # ── /support ─────────────────────────────────────────────────────────────
    "support.prompt": "📬 <b>Қолдау</b>\n\nСұрағыңызды команда соңынан жазыңыз:\n<code>/support Сұрағыңыз осында</code>",
    "support.accepted": "✅ <b>Өтініш қабылданды</b>\n\nСізге жақын уақытта жауап береміз.\nӨтініш нөмірі: <code>{ticket_id}</code>",

    # ── /limit ───────────────────────────────────────────────────────────────
    "limit.header": "📊 <b>{scope} шегі</b>",
    "limit.scope_private": "жеке сұраулар",
    "limit.scope_chat": "осы чаттағы сұраулар",
    "limit.used": "✅ Қолданылды: <b>{used}</b>",
    "limit.remaining": "💬 Қалды: <b>{remaining}</b>",
    "limit.max": "🏁 Максимум: <b>{cap}</b>",
    "limit.reset_in": "🔄 Жаңарту: <b>{reset_str}</b> кейін",
    "limit.reset_done": "🔄 Шек қазірдің өзінде жаңартылды — қайта қолдануға болады",
    "limit.exhausted_note": "<i>Шек таусылды. Жаңартуды күтіңіз немесе әкімшіге хабарласыңыз.</i>",
    "limit.normal_note": "<i>Шек ЖИ сұрауларын есептейді (кесте, іздеу). /start, /help және басқа командалар есептелмейді.</i>",

    # ── /login, /code, подтверждение входа ──────────────────────────────────
    "login.instructions": (
        "🔐 <b>Сайтқа кіру</b>\n\n"
        "1. <a href=\"{web_url}/profile\">{web_url}/profile</a> ашыңыз\n"
        "2. <b>«Telegram арқылы кіру»</b> түймесін басыңыз\n"
        "3. Сізге <b>6 әріптен тұратын код</b> көрсетіледі (бас латын әріптері)\n"
        "4. Бұл кодты <code>/code XXXXXX</code> командасымен жіберіңіз\n"
        "5. Кіруді растаңыз — бет автоматты түрде жаңарады\n\n"
        "💡 Немесе жай <code>/code</code> деп жазып, кодты бос орынмен жазыңыз."
    ),
    "login.code_missing": "❓ Команда соңынан кодты көрсетіңіз:\n<code>/code XXXXXX</code>\n\nКод сайтта «Telegram арқылы кіру» түймесін басқанда көрсетіледі.",
    "login.code_invalid_format": "❌ Код <b>6 бас әріп пен сандан</b> тұруы керек.\nМысалы: <code>/code ABCDEF</code>",
    "login.account_blocked": "❌ Сіздің тіркелгіңіз бұғатталған.",
    "login.server_error": "⚠️ Сервер қатесі. Кейінірек қайталап көріңіз.",
    "login.code_error": "❌ <b>{error}</b>\n\nКодты сайтта тексеріп, қайта көріңіз.\nКод <b>3 минут</b> жарамды.",
    "login.code_error_default": "Қате немесе мерзімі өткен код",
    "login.code_error_server": "Сервер қатесі",
    "login.confirm_prompt": "🔐 <b>Кіруді растау</b>\n\nСәлем, {name}! Біреу сіздің тіркелгіңізбен сайтқа кіруге тырысады.\n\nКіруді растайсыз ба?",
    "login.confirm_button": "✅ Кіруді растау",
    "login.cancel_button": "❌ Бас тарту",
    "login.cancelled": "❌ <b>Кіру бас тартылды.</b>\n\nЕгер бұл сіз болмасаңыз — қорықпаңыз, сілтеме енді жарамсыз.",
    "login.cancelled_toast": "Кіру бас тартылды",
    "login.confirm_error": "⚠️ <b>Растау қатесі.</b>\n\nМүмкін, сеанс мерзімі өткен. Қайта кіріп көріңіз.",
    "login.confirm_error_toast": "Қате, қайта көріңіз",
    "login.confirmed": "✅ <b>Кіру расталды!</b>\n\nСайттағы бет автоматты түрде жаңарады.",
    "login.confirmed_toast": "Кіру сәтті өтті ✅",
    "login.default_name": "пайдаланушы",

    # ── Дизамбигуация (выбор группы/аудитории) ──────────────────────────────
    "disambig.stale_data": "⏱ Деректер ескірген. Сұрауды қайталаңыз.",
    "disambig.stale_button": "⚠️ Ескірген түйме. Сұрауды қайталаңыз.",
    "disambig.expired": "⏱ Таңдау уақыты бітті. Сұрауды қайталаңыз.",
    "disambig.loading": "⏳ Кесте жүктелуде…",
    "disambig.unknown_intent": "❓ Белгісіз сұрау түрі.",
    "disambig.error": "❌ Кестені жүктеу қатесі.\n<code>{eid}</code>",
    "disambig.format_error": "❌ Кесте өңдеу қатесі.",
    "disambig.day_of": "{total}-нен {idx}-күн",
    "disambig.prev_page": "◀ Алд.",
    "disambig.next_page": "Келесі ▶",
    "disambig.group_label": "топ #{id}",
    "disambig.room_label": "ауд. #{id}",
    "disambig.schedule_title": "Кесте · {title}",

    # ── Фидбэк 👍👎 ───────────────────────────────────────────────────────────
    "feedback.error_toast": "⚠️ Қате",
    "feedback.already_rated_toast": "Бұрын бағаланған ✓",
    "feedback.save_failed_toast": "⚠️ Бағаны сақтау мүмкін болмады",
    "feedback.thanks_toast": "{icon} Баға сақталды, рахмет!",

    # ── /classmates ──────────────────────────────────────────────────────────
    "classmates.profile_not_found": "👤 Профиліңіз табылмады.",
    "classmates.no_group": "👥 <b>Топ көрсетілмеген</b>\n\nТоптастарыңызды көру үшін сайтта профиліңізді баптаңыз.",
    "classmates.query_error": "❌ Топтастар тізімін алу қатесі.",
    "classmates.header": "👥 <b>Топтастар · {group_label}</b>\n",
    "classmates.registered_count": "<i>Тіркелген: {count} адам.</i>\n",
    "classmates.none_registered": "👥 <b>Топтастар · {group_label}</b>\n\nӨз тобыңыздан әзірге ешкім ботта тіркелмеген.",
    "classmates.group_fallback_label": "топ #{id}",
    "classmates.more_suffix": "\n<i>…және басқалары</i>",

    # ── /teacher ──────────────────────────────────────────────────────────────
    "teacher.search_prompt": "👤 <b>Оқытушыны іздеу</b>\n\nТегін (немесе бөлігін) жазыңыз:\n<code>/teacher Иванов</code>",
    "teacher.search_error": "❌ Іздеу қатесі.",
    "teacher.not_found": "🔍 <b>{query}</b> бойынша ештеңе табылмады.\n\nБасқа тегін көріп көріңіз.",
    "teacher.found_count": "🔍 Табылған оқытушылар: <b>{count}</b>\n\nТаңдаңыз:",
    "teacher.not_found_short": "❌ Оқытушы табылмады.",
    "teacher.subjects_label": "\n📚 <b>Пәндер:</b>",
    "teacher.more_subjects": "  <i>…және тағы {count}</i>",
    "teacher.lesson_types_label": "\n🗂 <b>Сабақ түрлері:</b> {types}",
    "teacher.groups_label": "\n👥 <b>Топтар ({count}):</b> {names}",
    "teacher.more_groups": "  <i>…және тағы {count}</i>",
    "teacher.lessons_in_db": "\n📊 ДБ-дағы сабақтар: <b>{count}</b>",
    "teacher.schedule_loaded": "🕐 Кесте: <b>жүктелді</b>",
    "teacher.alltime_stats_label": "\n📈 <b>Барлық уақыт статистикасы:</b>",
    "teacher.total_lessons": "  Барлық сабақтар: <b>{count}</b>",
    "teacher.types_label": "  Түрлері: {types}",
    "teacher.buildings_label": "  Корпустар: {buildings}",
    "teacher.rooms_label": "  Аудиториялар: {rooms}",
    "teacher.schedule_button": "📅 Кесте",

    # ── /me ──────────────────────────────────────────────────────────────────
    "me.profile_not_found": "👤 Профиль табылмады.",
    "me.header": "👤 <b>Жеке кабинет</b>\n",
    "me.role_student": "Студент",
    "me.role_teacher": "Оқытушы",
    "me.role_unset": "Баптаулмаған",
    "me.group_line": "\n📌 Топ: <b>{group_name}</b>",
    "me.teacher_line": "\n📌 Оқытушы: <b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 Сұраулар шегі: <code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 Менің кестем",
    "me.miniapp_button": "📱 Кесте (қосымша)",
    "me.subjects_button": "📚 Пәндер",
    "me.stats_button": "📊 Статистика",
    "me.classmates_button": "👥 Топтастар",
    "me.my_lessons_button": "📈 Менің сабақтарым",
    "me.profile_button": "⚙️ Профиль",
    "me.map_button": "🗺 Карта",
    "me.limit_button": "💬 Сұраулар шегі",
    "me.help_button": "❓ Көмек",
    "me.no_ecampus_data": "📭 eCampus деректері жоқ.",
    "me.stats_choose_period": "📊 <b>Үлгерім статистикасы</b>\n\nКезеңді таңдаңыз:",

    # ── /grades ──────────────────────────────────────────────────────────────
    "grades.not_connected": "📚 <b>eCampus қосылмаған</b>\n\neCampus тіркелгісін сайттағы немесе мини-қосымшадағы <b>Профиль → eCampus</b> бөлімінде қосыңыз.",
    "grades.sync_running": "⏳ eCampus-пен синхрондау жүріп жатыр — деректер жаңартылып жатыр.\nБір минуттан кейін қайталап көріңіз.",
    "grades.empty": "📭 eCampus деректері әзірге бос.\nМини-қосымшада «Жаңарту» түймесін басыңыз немесе автосинхрондауды күтіңіз.",
    "grades.semester_label": "{n}-семестр",
    "grades.current_semester_label": "Ағымдағы семестр",
    "grades.no_grades": "📭 <b>Бағалар жоқ</b> ({sem_label})\n\nБағалар оқытушы оларды қойғаннан кейін пайда болады.",
    "grades.header": "📊 <b>Бағалар · {sem_label}</b>\n",
    "grades.total": "\n<i>Барлық бағалар: {count}</i>",
    "grades.page_suffix": "\n\n({page}/{total})",

    # ── /stats ───────────────────────────────────────────────────────────────
    "stats.not_connected_short": "📚 <b>eCampus қосылмаған</b>\n\nТіркелгіні сайттағы Профиль бөлімінде қосыңыз.",
    "stats.no_data": "📭 eCampus деректері жоқ. Синхрондауды жаңартыңыз.",
    "stats.no_term_data": "📭 Осы семестр бойынша деректер жоқ.",
    "stats.all_time_suffix": " · Барлық уақыт",
    "stats.term_fallback": " · сем.{id}",
    "stats.header": "📊 <b>Үлгерім статистикасы{suffix}</b>\n",
    "stats.subjects_count": "📚 Пәндер:   <b>{count}</b>",
    "stats.grades_count": "✏️  Бағалар:      <b>{count}</b>",
    "stats.exams_count": "🎓 Емтихандар:  <b>{count}</b>",
    "stats.credits_count": "📝 Сынақтар:    <b>{count}</b>",
    "stats.rating": "⭐ Рейтинг:    {icon} <b>{avg:.1f}</b> / {max:.1f} ({pct:.0f}%)",
    "stats.updated_at": "\n<i>Жаңартылды: {dt}</i>",
    "stats.choose_period": "📊 <b>Үлгерім статистикасы</b>\n\nКезеңді таңдаңыз:",
    "stats.all_time_button": "📊 Барлық уақыт үшін",

    # ── /subjects ────────────────────────────────────────────────────────────
    "subjects.not_connected": "📚 <b>eCampus қосылмаған</b>\n\nТіркелгіні сайттағы Профиль бөлімінде қосыңыз.",
    "subjects.no_data": "📭 Деректер жоқ. Синхрондауды жаңартыңыз.",
    "subjects.none_for_term": "📭 Пәндер табылмады ({sem_label}).",
    "subjects.header": "📚 <b>Пәндер · {sem_label}</b>  ({count} дана)\n",
    "subjects.no_type_data": "деректер жоқ",
    "subjects.rating_line": "\n    {icon} Рейтинг: <b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>Емтихан</i>",
    "subjects.credit_tag": " 📝<i>Сынақ</i>",

    # ── /ecampus ─────────────────────────────────────────────────────────────
    "ecampus.not_connected": (
        "📚 <b>СКФУ eCampus</b>\n\n"
        "Тіркелгі <b>қосылмаған</b>.\n\n"
        "Оны сайттағы немесе мини-қосымшадағы <b>Профиль → eCampus</b> "
        "бөлімінде қосып, мыналарды алыңыз:\n"
        "  • Пәндер мен бағалар тізімі\n"
        "  • Үлгерім статистикасы\n"
        "  • Әр курс бойынша рейтингтер\n\n"
        "Командалар (қосқаннан кейін):\n"
        "  /grades   — менің бағаларым\n"
        "  /stats    — үлгерім статистикасы\n"
        "  /subjects — пәндер тізімі"
    ),
    "ecampus.status_ok": "✅ Синхрондалды",
    "ecampus.status_running": "⏳ Синхрондау...",
    "ecampus.status_error": "❌ Синхрондау қатесі",
    "ecampus.status_pending": "🕐 Синхрондау күтілуде",
    "ecampus.header": "📚 <b>СКФУ eCampus</b>\n",
    "ecampus.status_line": "🔗 Күй: {status}",
    "ecampus.subjects_count": "📦 Пәндер: <b>{count}</b>",
    "ecampus.grades_count": "✏️  Бағалар: <b>{count}</b>",
    "ecampus.updated_at": "🕐 Жаңартылды: <b>{dt}</b>",
    "ecampus.current_term": "\n📅 Ағымдағы семестр: <b>{term}</b>",
    "ecampus.term_subjects": "   Пәндер: <b>{count}</b>",
    "ecampus.term_grades": "   Бағалар: <b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>Командалар:</b>\n"
        "  /grades   — ағымдағы семестрдегі бағаларым\n"
        "  /grades 2 — 2-семестр бағалары\n"
        "  /stats    — толық статистика\n"
        "  /subjects — пәндер тізімі"
    ),

    # ── ИИ-обработчик (ошибки/заглушки) ─────────────────────────────────────
    "ai.empty_message": "Бірдеңе жазыңыз 🙂",
    "ai.processing": "⏳ Өңделуде...",
    "ai.unknown_request": "❓ Белгісіз сұрау.",
    "ai.parse_failed": "❌ Сұрауды тану мүмкін болмады. Қайталап тұжырымдап көріңіз.",
    "ai.execution_error": "❌ Сұрауды орындау қатесі.\n<code>{eid}</code>",
    "ai.processing_error": "❌ Сұрауды өңдеу қатесі.",

    # ── /language (новая команда) ───────────────────────────────────────────
    "language.prompt": "🌐 <b>Интерфейс тілін таңдаңыз</b>\n\nБұл таңдау сайт пен мини-қосымшамен синхрондалады.",
    "language.saved": "✅ Тіл <b>{name}</b> болып өзгертілді.",
    "language.save_failed": "⚠️ Тілді сақтау мүмкін болмады. Қайта көріңіз.",

    # ── Меню команд бота (BotCommand description) ───────────────────────────
    "cmd.start": "Жұмысты бастау",
    "cmd.me": "Жеке кабинет 👤",
    "cmd.help": "Анықтама",
    "cmd.miniapp": "Кестені ашу (Mini App) 📅",
    "cmd.grades": "eCampus-тағы бағаларым",
    "cmd.stats": "Үлгерім статистикасы 📊",
    "cmd.subjects": "Пәндер тізімі",
    "cmd.classmates": "Топтастарым 👥",
    "cmd.teacher": "Оқытушыны табу 👤",
    "cmd.ecampus": "eCampus күйі",
    "cmd.limit": "Сұраулар шегі",
    "cmd.language": "Интерфейс тілі 🌐",
    "cmd.login": "Сайтқа кіру",
    "cmd.code": "Кодты енгізу (/code XXXXXX)",
    "cmd.support": "Қолдау",
    "cmd.suggest": "Идея ұсыну",
    "cmd.about": "Бот туралы",
}
