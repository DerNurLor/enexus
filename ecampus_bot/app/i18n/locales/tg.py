"""Тоҷикӣ — тарҷума дар асоси ru.py."""

MESSAGES: dict[str, str] = {
    # ── /start ───────────────────────────────────────────────────────────────
    "start.greeting": (
        "👋 Салом! Ман боти ҷадвали дарсии СКФУ ҳастам.\n\n"
        "Саволи худро бо забони муқаррарӣ нависед:\n"
        "  • <i>Ҷадвали гурӯҳи ИСС-б-о-22-3 барои ин ҳафта</i>\n"
        "  • <i>Дарси Подзолко баъди 5 дақиқа дар куҷост?</i>\n"
        "  • <i>Синфхонаҳои холӣ дар бинои 11</i>\n"
        "  • <i>Дар гурӯҳи АИС-б-о-25-1 ҳозир чӣ ҳаст?</i>\n\n"
        "📋 <b>Фармонҳо:</b>\n"
        "  /me         — кабинети шахсӣ 👤\n"
        "  /miniapp    — ҷадвал дар барнома 📅\n"
        "  /grades     — бахоҳои ман аз eCampus\n"
        "  /stats      — статистика 📊\n"
        "  /classmates — ҳамгурӯҳон 👥\n"
        "  /teacher    — ёфтани муаллим\n"
        "  /help       — кӯмаки пурра"
    ),
    "start.login_welcome": "👋 Салом, {name}!\n\n🔐 <b>Усули нави воридшавӣ</b>\n\n1. <a href=\"{web_url}/profile\">{web_url}/profile</a>-ро кушоед\n2. Тугмаи <b>«Воридшавӣ тавассути Telegram»</b>-ро пахш кунед\n3. Рамзи <b>6-рақамаи</b> нишон додашударо ба ман фиристед\n4. Тасдиқ кунед — саҳифа худаш нав мешавад ✨",

    # ── /help ────────────────────────────────────────────────────────────────
    "help.full": (
        "📖 <b>Кӯмак дар бораи боти ҷадвали дарсии СКФУ</b>\n\n"
        "Дархости худро бо забони муқаррарӣ нависед:\n\n"
        "📅 <b>Ҷадвал:</b>\n"
        "  <i>Ҷадвали ИСС-б-о-22-3</i>\n"
        "  <i>Фардо дар гурӯҳи АИС25 чӣ ҳаст?</i>\n\n"
        "👤 <b>Муаллим:</b>\n"
        "  <i>Подзолко ҳозир дар куҷост?</i>  ·  <i>Ҷадвали Иванов</i>\n\n"
        "🚪 <b>Синфхонаҳо:</b>\n"
        "  <i>Синфхонаҳои холӣ ҳозир</i>\n\n"
        "📋 <b>Фармонҳо:</b>\n"
        "  /me          — кабинети шахсӣ 👤\n"
        "  /miniapp     — ҷадвал дар барнома 📅\n"
        "  /grades      — бахоҳои ман аз eCampus\n"
        "  /stats       — статистикаи пешравӣ 📊\n"
        "  /subjects    — рӯйхати фанҳо\n"
        "  /classmates  — ҳамгурӯҳонам 👥\n"
        "  /teacher     — ёфтани муаллим\n"
        "  /ecampus     — ҳолати eCampus\n"
        "  /limit       — маҳдудияти дархостҳо\n"
        "  /language    — забони интерфейс 🌐\n"
        "  /support     — дастгирӣ\n"
        "  /suggest     — пешниҳод кардани ғоя\n\n"
        "💡 <i>Дар гурӯҳҳо бо қайд кардан муроҷиат кунед: @botname дархост</i>"
    ),
    "help.quick": (
        "📖 <b>Кӯмаки зуд</b>\n\n"
        "/me       — ин экран\n"
        "/grades   — бахоҳои eCampus\n"
        "/stats    — статистика (бо интихоби семестр)\n"
        "/subjects — рӯйхати фанҳо\n"
        "/teacher  — ҷустуҳои муаллим\n"
        "/classmates — ҳамгурӯҳон\n"
        "/limit    — маҳдудияти дархостҳо\n"
        "/miniapp  — кушодани барнома\n"
        "/help     — кӯмаки пурра"
    ),

    # ── Группа: приветствие при добавлении бота ─────────────────────────────────
    "group_welcome.text": (
        "👋 Салом! Хушҳолам, ки ба <b>{chat_title}</b> ҳамроҳ шудам!\n\n"
        "📌 <b>Чӣ кор карда метавонам:</b>\n"
        "  • Ҷадвали гурӯҳ, муаллим, синфхона\n"
        "  • Синфхонаҳои холӣ ҳозир\n"
        "  • Ҷустуҷӯ аз рӯи муаллимон ва гурӯҳҳо\n\n"
        "💬 <b>Чӣ тавр муроҷиат кардан:</b>\n"
        "  Маро қайд кунед: <code>@{bot_username} ҷадвали ИСС-б-о-22-3</code>\n"
        "  Ё аз фармонҳо истифода баред:\n"
        "  /help — ҳамаи имкониятҳо\n"
        "  /miniapp — ҷадвал дар барнома 📅\n\n"
        "🔕 <i>Ман чати умумиро пайгирӣ намекунам — фақат ба қайдҳо ва фармонҳо ҷавоб медиҳам.</i>"
    ),
    "group_welcome.default_title": "ин гурӯҳ",
    "common.open_schedule_button": "📅 Кушодани ҷадвал",

    # ── /mykey (отключена) ───────────────────────────────────────────────────
    "mykey.disabled": "Фармони /mykey хомӯш карда шудааст.",

    # ── /roles ───────────────────────────────────────────────────────────────
    "roles.role.admin": "Маъмур",
    "roles.role.moderator": "Модератор",
    "roles.role.vip": "VIP",
    "roles.role.beta": "Озмоишгари бета",
    "roles.role.user": "Корбар",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>Нақшҳо:</b>",
    "roles.privileges_label": "\n🔓 <b>Имтиёзҳо:</b>",
    "roles.priv_admin_panel": "⚙️ <b>Лавҳаи идоракунӣ</b> → <a href=\"{url}\">кушодан</a>",
    "roles.priv_beta": "🧪 <b>Дастрасии бета</b> — филтрҳои васеи ҷадвал",
    "roles.priv_floorplan_edit": "🗺 <b>Таҳрир</b> кардани нақшаҳои қабат",
    "roles.priv_floorplan_view": "🗺 <b>Дидани</b> нақшаҳои қабат",
    "roles.priv_personal_limit": "📊 <b>Маҳдудияти шахсӣ</b>: {limit} дархост / давра",
    "roles.profile_link": "\n💼 <b>Кабинети шахсӣ:</b> <a href=\"{url}\">кушодан</a>",

    # ── /suggest ─────────────────────────────────────────────────────────────
    "suggest.prompt": (
        "💡 <b>Пешниҳодҳо ва ғояҳо</b>\n\n"
        "Ғояе доред, ки боту ё ҷадвалро беҳтар кунад?\n"
        "Баъди фармон бинвисед:\n\n"
        "<code>/suggest Ғояи шумо дар ин ҷо</code>\n\n"
        "<i>Масалан: /suggest Илова кардани огоҳӣ 10 дақиқа пеш аз дарс</i>"
    ),
    "suggest.accepted": "✅ <b>Пешниҳод қабул шуд!</b>\n\nСупос, ғояи шумо ба беҳтар шудани бот мадад мекунад.\nРақам: <code>{ticket_id}</code>\n",

    # ── /about ───────────────────────────────────────────────────────────────
    "about.text": (
        "🎓 <b>Боти ҷадвали дарсии СКФУ</b>\n\n"
        "Ёрдамчии оқил барои донишҷӯён ва омӯзгорони "
        "Донишгоҳи федералии Кавкази Шимолӣ.\n\n"
        "📌 <b>Имкониятҳо:</b>\n"
        "  • Ҷадвали гурӯҳҳо, муаллимон, синфхонаҳо\n"
        "  • Синфхонаҳои холӣ дар вақти воқеӣ\n"
        "  • Ҷустуҷӯ аз рӯи гурӯҳҳо ва муаллимон\n"
        "  • Mini App бо ҷадвали пурра 📅\n\n"
        "🔗 <b>Истинодҳо:</b>\n"
        "  • <a href=\"{miniapp_url}\">Mini App ҷадвал</a>\n"
        "🛠 <b>Версия:</b> 2.0\n"
        "💬 Саволҳо ва пешниҳодҳо: /support · /suggest"
    ),

    # ── /miniapp ─────────────────────────────────────────────────────────────
    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — ҷадвали пурра дар барнома\n\n"
        "• Ҷустуҷӯи мутаҳаррик аз рӯи гурӯҳ, муаллим, синфхона\n"
        "• Синфхонаҳои холӣ дар вақти воқеӣ\n"
        "• Нақшаҳои қабати бинохо\n"
        "• Интихобшудаҳо ва танзимоти шахсӣ\n\n"
        "Тугмаи поёнро пахш кунед 👇"
    ),

    # ── /support ─────────────────────────────────────────────────────────────
    "support.prompt": "📬 <b>Дастгирӣ</b>\n\nСаволи худро баъди фармон бинвисед:\n<code>/support Саволи шумо дар ин ҷо</code>",
    "support.accepted": "✅ <b>Муроҷиат қабул шуд</b>\n\nМо дар муддати кӯтоҳтарин ҷавоб медиҳем.\nРақами муроҷиат: <code>{ticket_id}</code>",

    # ── /limit ───────────────────────────────────────────────────────────────
    "limit.header": "📊 <b>Маҳдудияти {scope}</b>",
    "limit.scope_private": "дархостҳои шахсӣ",
    "limit.scope_chat": "дархостҳо дар ин чат",
    "limit.used": "✅ Истифода шуд: <b>{used}</b>",
    "limit.remaining": "💬 Боқимонда: <b>{remaining}</b>",
    "limit.max": "🏁 Ҳадди аксар: <b>{cap}</b>",
    "limit.reset_in": "🔄 Бозсозӣ баъди: <b>{reset_str}</b>",
    "limit.reset_done": "🔄 Маҳдудият аллакай бозсозӣ шуд — мумкин аст дубора истифода баред",
    "limit.exhausted_note": "<i>Маҳдудият тамом шуд. Бозсозиро интизор шавед ё ба маъмур муроҷиат кунед.</i>",
    "limit.normal_note": "<i>Маҳдудият дархостҳои AI-ро ҳисоб мекунад (ҷадвал, ҷустуҷӯ). Фармонҳои /start, /help ва дигарон ҳисоб намешаванд.</i>",

    # ── /login, /code, подтверждение входа ──────────────────────────────────
    "login.instructions": (
        "🔐 <b>Воридшавӣ ба сайт</b>\n\n"
        "1. <a href=\"{web_url}/profile\">{web_url}/profile</a>-ро кушоед\n"
        "2. Тугмаи <b>«Воридшавӣ тавассути Telegram»</b>-ро пахш кунед\n"
        "3. Ба шумо <b>рамзи 6-ҳарфа</b> нишон дода мешавад (ҳарфҳои калони лотинӣ)\n"
        "4. Ин рамзро бо фармони <code>/code XXXXXX</code> фиристед\n"
        "5. Воридшавиро тасдиқ кунед — саҳифа худкор нав мешавад\n\n"
        "💡 Ё танҳо <code>/code</code> ва рамзро бо фосила бинвисед."
    ),
    "login.code_missing": "❓ Баъди фармон рамзро нишон диҳед:\n<code>/code XXXXXX</code>\n\nРамз дар сайт ҳангоми пахши «Воридшавӣ тавассути Telegram» намоиш дода мешавад.",
    "login.code_invalid_format": "❌ Рамз бояд аз <b>6 ҳарфи калон ва рақам</b> иборат бошад.\nМисол: <code>/code ABCDEF</code>",
    "login.account_blocked": "❌ Ҳисоби шумо бастааст.",
    "login.server_error": "⚠️ Хатои сервер. Дертар кӯшиш кунед.",
    "login.code_error": "❌ <b>{error}</b>\n\nРамзро дар сайт санҷед ва дубора кӯшиш кунед.\nРамз <b>3 дақиқа</b> амал мекунад.",
    "login.code_error_default": "Рамзи нодуруст ё мӯҳлаташ гузашта",
    "login.code_error_server": "Хатои сервер",
    "login.confirm_prompt": "🔐 <b>Тасдиқи воридшавӣ</b>\n\nСалом, {name}! Касе мехоҳад бо ҳисоби шумо ба сайт ворид шавад.\n\nВоридшавиро тасдиқ мекунед?",
    "login.confirm_button": "✅ Тасдиқи воридшавӣ",
    "login.cancel_button": "❌ Бекор кардан",
    "login.cancelled": "❌ <b>Воридшавӣ бекор шуд.</b>\n\nАгар ин шумо набудед — хавотир нашавед, истинод дигар амал намекунад.",
    "login.cancelled_toast": "Воридшавӣ бекор шуд",
    "login.confirm_error": "⚠️ <b>Хатои тасдиқ.</b>\n\nЭҳтимол, мӯҳлати ҳолат гузашта аст. Дубора ворид шуданро кӯшиш кунед.",
    "login.confirm_error_toast": "Хато, дубора кӯшиш кунед",
    "login.confirmed": "✅ <b>Воридшавӣ тасдиқ шуд!</b>\n\nСаҳифа дар сайт худкор нав мешавад.",
    "login.confirmed_toast": "Воридшавӣ бомуваффақият анҷом ёфт ✅",
    "login.default_name": "корбар",

    # ── Дизамбигуация (выбор группы/аудитории) ──────────────────────────────
    "disambig.stale_data": "⏱ Маълумот кӯҳна шуд. Дархостро такрор кунед.",
    "disambig.stale_button": "⚠️ Тугмаи кӯҳна. Дархостро такрор кунед.",
    "disambig.expired": "⏱ Вақти интихоб гузашт. Дархостро такрор кунед.",
    "disambig.loading": "⏳ Ҷадвал бор мешавад…",
    "disambig.unknown_intent": "❓ Намуди дархости номаълум.",
    "disambig.error": "❌ Хатои боргирии ҷадвал.\n<code>{eid}</code>",
    "disambig.format_error": "❌ Хатои коркарди ҷадвал.",
    "disambig.day_of": "Рӯзи {idx} аз {total}",
    "disambig.prev_page": "◀ Қаблӣ",
    "disambig.next_page": "Баъдӣ ▶",
    "disambig.group_label": "гурӯҳи #{id}",
    "disambig.room_label": "синфхонаи #{id}",
    "disambig.schedule_title": "Ҷадвал · {title}",

    # ── Фидбэк 👍👎 ───────────────────────────────────────────────────────────
    "feedback.error_toast": "⚠️ Хато",
    "feedback.already_rated_toast": "Аллакай баҳо дода шуд ✓",
    "feedback.save_failed_toast": "⚠️ Захираи баҳо муваффақ нашуд",
    "feedback.thanks_toast": "{icon} Баҳо захира шуд, ташаккур!",

    # ── /classmates ──────────────────────────────────────────────────────────
    "classmates.profile_not_found": "👤 Профили шумо ёфт нашуд.",
    "classmates.no_group": "👥 <b>Гурӯҳ танзим нашудааст</b>\n\nБарои дидани ҳамгурӯҳон профили худро дар сайт танзим кунед.",
    "classmates.query_error": "❌ Хатои гирифтани рӯйхати ҳамгурӯҳон.",
    "classmates.header": "👥 <b>Ҳамгурӯҳон · {group_label}</b>\n",
    "classmates.registered_count": "<i>Қайд шудаанд: {count} нафар.</i>\n",
    "classmates.none_registered": "👥 <b>Ҳамгурӯҳон · {group_label}</b>\n\nАз гурӯҳи шумо то ҳол ҳеҷ кас дар бот қайд нашудааст.",
    "classmates.group_fallback_label": "гурӯҳи #{id}",
    "classmates.more_suffix": "\n<i>…ва дигарон</i>",

    # ── /teacher ──────────────────────────────────────────────────────────────
    "teacher.search_prompt": "👤 <b>Ҷустуҳои муаллим</b>\n\nНасабро (ё қисми онро) нависед:\n<code>/teacher Иванов</code>",
    "teacher.search_error": "❌ Хатои ҷустуҷӯ.",
    "teacher.not_found": "🔍 Аз рӯи <b>{query}</b> чизе ёфт нашуд.\n\nНасаби дигарро кӯшиш кунед.",
    "teacher.found_count": "🔍 Муаллимони ёфтшуда: <b>{count}</b>\n\nИнтихоб кунед:",
    "teacher.not_found_short": "❌ Муаллим ёфт нашуд.",
    "teacher.subjects_label": "\n📚 <b>Фанҳо:</b>",
    "teacher.more_subjects": "  <i>…ва боз {count}</i>",
    "teacher.lesson_types_label": "\n🗂 <b>Намудҳои дарс:</b> {types}",
    "teacher.groups_label": "\n👥 <b>Гурӯҳҳо ({count}):</b> {names}",
    "teacher.more_groups": "  <i>…ва боз {count}</i>",
    "teacher.lessons_in_db": "\n📊 Дарсҳо дар пойгоҳи дода: <b>{count}</b>",
    "teacher.schedule_loaded": "🕐 Ҷадвал: <b>бор шуд</b>",
    "teacher.alltime_stats_label": "\n📈 <b>Статистика барои тамоми вақт:</b>",
    "teacher.total_lessons": "  Ҳамагӣ дарсҳо: <b>{count}</b>",
    "teacher.types_label": "  Намудҳо: {types}",
    "teacher.buildings_label": "  Бинохо: {buildings}",
    "teacher.rooms_label": "  Синфхонаҳо: {rooms}",
    "teacher.schedule_button": "📅 Ҷадвал",

    # ── /me ──────────────────────────────────────────────────────────────────
    "me.profile_not_found": "👤 Профил ёфт нашуд.",
    "me.header": "👤 <b>Кабинети шахсӣ</b>\n",
    "me.role_student": "Донишҷӯ",
    "me.role_teacher": "Муаллим",
    "me.role_unset": "Танзим нашудааст",
    "me.group_line": "\n📌 Гурӯҳ: <b>{group_name}</b>",
    "me.teacher_line": "\n📌 Муаллим: <b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 Маҳдудияти дархостҳо: <code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 Ҷадвали ман",
    "me.miniapp_button": "📱 Ҷадвал (барнома)",
    "me.subjects_button": "📚 Фанҳо",
    "me.stats_button": "📊 Статистика",
    "me.classmates_button": "👥 Ҳамгурӯҳон",
    "me.my_lessons_button": "📈 Дарсҳои ман",
    "me.profile_button": "⚙️ Профил",
    "me.map_button": "🗺 Харита",
    "me.limit_button": "💬 Маҳдудияти дархостҳо",
    "me.help_button": "❓ Кӯмак",
    "me.no_ecampus_data": "📭 Маълумоти eCampus нест.",
    "me.stats_choose_period": "📊 <b>Статистикаи пешравӣ</b>\n\nДавраро интихоб кунед:",

    # ── /grades ──────────────────────────────────────────────────────────────
    "grades.not_connected": "📚 <b>eCampus пайваст нашудааст</b>\n\nҲисоби eCampus-ро дар бахши <b>Профил → eCampus</b> дар сайт ё мини-барнома пайваст кунед.",
    "grades.sync_running": "⏳ Синхронизация бо eCampus ҳанӯз идома дорад — маълумот нав мешавад.\nБаъди як дақиқа кӯшиш кунед.",
    "grades.empty": "📭 Маълумоти eCampus то ҳол холӣ аст.\nДар мини-барнома тугмаи «Нав кардан»-ро пахш кунед ё синхронизацияи худкорро интизор шавед.",
    "grades.semester_label": "Семестри {n}",
    "grades.current_semester_label": "Семестри ҷорӣ",
    "grades.no_grades": "📭 <b>Баҳо нест</b> ({sem_label})\n\nБаҳоҳо баъди гузоштани муаллим пайдо мешаванд.",
    "grades.header": "📊 <b>Баҳоҳо · {sem_label}</b>\n",
    "grades.total": "\n<i>Ҳамагӣ баҳоҳо: {count}</i>",
    "grades.page_suffix": "\n\n({page}/{total})",

    # ── /stats ───────────────────────────────────────────────────────────────
    "stats.not_connected_short": "📚 <b>eCampus пайваст нашудааст</b>\n\nҲисобро дар бахши Профил дар сайт пайваст кунед.",
    "stats.no_data": "📭 Маълумоти eCampus нест. Синхронизацияро нав кунед.",
    "stats.no_term_data": "📭 Барои ин семестр маълумот нест.",
    "stats.all_time_suffix": " · Тамоми вақт",
    "stats.term_fallback": " · сем.{id}",
    "stats.header": "📊 <b>Статистикаи пешравӣ{suffix}</b>\n",
    "stats.subjects_count": "📚 Фанҳо:   <b>{count}</b>",
    "stats.grades_count": "✏️  Баҳоҳо:      <b>{count}</b>",
    "stats.exams_count": "🎓 Имтиҳонҳо:  <b>{count}</b>",
    "stats.credits_count": "📝 Зачётҳо:    <b>{count}</b>",
    "stats.rating": "⭐ Рейтинг:    {icon} <b>{avg:.1f}</b> / {max:.1f} ({pct:.0f}%)",
    "stats.updated_at": "\n<i>Нав шуд: {dt}</i>",
    "stats.choose_period": "📊 <b>Статистикаи пешравӣ</b>\n\nДавраро интихоб кунед:",
    "stats.all_time_button": "📊 Барои тамоми вақт",

    # ── /subjects ────────────────────────────────────────────────────────────
    "subjects.not_connected": "📚 <b>eCampus пайваст нашудааст</b>\n\nҲисобро дар бахши Профил дар сайт пайваст кунед.",
    "subjects.no_data": "📭 Маълумот нест. Синхронизацияро нав кунед.",
    "subjects.none_for_term": "📭 Фанҳо ёфт нашуданд ({sem_label}).",
    "subjects.header": "📚 <b>Фанҳо · {sem_label}</b>  ({count} дона)\n",
    "subjects.no_type_data": "маълумот нест",
    "subjects.rating_line": "\n    {icon} Рейтинг: <b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>Имтиҳон</i>",
    "subjects.credit_tag": " 📝<i>Зачёт</i>",

    # ── /ecampus ─────────────────────────────────────────────────────────────
    "ecampus.not_connected": (
        "📚 <b>eCampus СКФУ</b>\n\n"
        "Ҳисоб <b>пайваст нашудааст</b>.\n\n"
        "Онро дар бахши <b>Профил → eCampus</b> дар сайт ё "
        "мини-барнома пайваст кунед ва гиред:\n"
        "  • Рӯйхати фанҳо ва баҳоҳо\n"
        "  • Статистикаи пешравӣ\n"
        "  • Рейтингҳо барои ҳар курс\n\n"
        "Фармонҳо (баъди пайваст шудан):\n"
        "  /grades   — баҳоҳои ман\n"
        "  /stats    — статистикаи пешравӣ\n"
        "  /subjects — рӯйхати фанҳо"
    ),
    "ecampus.status_ok": "✅ Синхронизация шуд",
    "ecampus.status_running": "⏳ Синхронизация...",
    "ecampus.status_error": "❌ Хатои синхронизация",
    "ecampus.status_pending": "🕐 Интизори синхронизация",
    "ecampus.header": "📚 <b>eCampus СКФУ</b>\n",
    "ecampus.status_line": "🔗 Ҳолат: {status}",
    "ecampus.subjects_count": "📦 Фанҳо: <b>{count}</b>",
    "ecampus.grades_count": "✏️  Баҳоҳо: <b>{count}</b>",
    "ecampus.updated_at": "🕐 Нав шуд: <b>{dt}</b>",
    "ecampus.current_term": "\n📅 Семестри ҷорӣ: <b>{term}</b>",
    "ecampus.term_subjects": "   Фанҳо: <b>{count}</b>",
    "ecampus.term_grades": "   Баҳоҳо: <b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>Фармонҳо:</b>\n"
        "  /grades   — баҳоҳои семестри ҷорӣ\n"
        "  /grades 2 — баҳоҳои семестри 2\n"
        "  /stats    — статистикаи пурра\n"
        "  /subjects — рӯйхати фанҳо"
    ),

    # ── ИИ-обработчик (ошибки/заглушки) ─────────────────────────────────────
    "ai.empty_message": "Чизе нависед 🙂",
    "ai.processing": "⏳ Коркард мешавад...",
    "ai.unknown_request": "❓ Дархости номаълум.",
    "ai.parse_failed": "❌ Дархостро шинохта натавонист. Бо тарзи дигар нависед.",
    "ai.execution_error": "❌ Хатои иҷрои дархост.\n<code>{eid}</code>",
    "ai.processing_error": "❌ Хатои коркарди дархост.",

    # ── /language (новая команда) ───────────────────────────────────────────
    "language.prompt": "🌐 <b>Забони интерфейсро интихоб кунед</b>\n\nИн интихоб бо сайт ва мини-барнома синхронизация мешавад.",
    "language.saved": "✅ Забон ба <b>{name}</b> тағйир ёфт.",
    "language.save_failed": "⚠️ Захираи забон муваффақ нашуд. Дубора кӯшиш кунед.",

    # ── Меню команд бота (BotCommand description) ───────────────────────────
    "cmd.start": "Сар кардани кор",
    "cmd.me": "Кабинети шахсӣ 👤",
    "cmd.help": "Кӯмак",
    "cmd.miniapp": "Кушодани ҷадвал (Mini App) 📅",
    "cmd.grades": "Баҳоҳои ман аз eCampus",
    "cmd.stats": "Статистикаи пешравӣ 📊",
    "cmd.subjects": "Рӯйхати фанҳо",
    "cmd.classmates": "Ҳамгурӯҳонам 👥",
    "cmd.teacher": "Ёфтани муаллим 👤",
    "cmd.ecampus": "Ҳолати eCampus",
    "cmd.limit": "Маҳдудияти дархостҳо",
    "cmd.language": "Забони интерфейс 🌐",
    "cmd.login": "Воридшавӣ ба сайт",
    "cmd.code": "Ворид кардани рамз (/code XXXXXX)",
    "cmd.support": "Дастгирӣ",
    "cmd.suggest": "Пешниҳод кардани ғоя",
    "cmd.about": "Дар бораи бот",
}
