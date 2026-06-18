"""Русский — источник истины для всех остальных переводов."""

MESSAGES: dict[str, str] = {
    # ── /start ───────────────────────────────────────────────────────────────
    "start.greeting": (
        "👋 Привет! Я бот расписания СКФУ.\n\n"
        "Спрашивай на естественном русском языке:\n"
        "  • <i>Расписание ИСС-б-о-22-3 на эту неделю</i>\n"
        "  • <i>Где пара через 5 минут у Подзолко?</i>\n"
        "  • <i>Свободные аудитории в корпусе 11</i>\n"
        "  • <i>Что сейчас у группы АИС-б-о-25-1?</i>\n\n"
        "📋 <b>Команды:</b>\n"
        "  /me         — личный кабинет 👤\n"
        "  /miniapp    — расписание в приложении 📅\n"
        "  /grades     — мои оценки из eCampus\n"
        "  /stats      — статистика 📊\n"
        "  /classmates — одногруппники 👥\n"
        "  /teacher    — найти преподавателя\n"
        "  /help       — полная справка"
    ),
    "start.login_welcome": "👋 Привет, {name}!\n\n🔐 <b>Новый способ входа</b>\n\n1. Откройте <a href=\"{web_url}/profile\">{web_url}/profile</a>\n2. Нажмите <b>«Войти через Telegram»</b>\n3. Отправьте мне показанный <b>6-значный код</b>\n4. Подтвердите — страница обновится сама ✨",

    # ── /help ────────────────────────────────────────────────────────────────
    "help.full": (
        "📖 <b>Справка по боту расписания СКФУ</b>\n\n"
        "Просто напиши запрос на естественном языке:\n\n"
        "📅 <b>Расписание:</b>\n"
        "  <i>Расписание ИСС-б-о-22-3</i>\n"
        "  <i>Что у группы АИС25 завтра?</i>\n\n"
        "👤 <b>Преподаватель:</b>\n"
        "  <i>Где Подзолко сейчас?</i>  ·  <i>Расписание Иванова</i>\n\n"
        "🚪 <b>Аудитории:</b>\n"
        "  <i>Свободные аудитории прямо сейчас</i>\n\n"
        "📋 <b>Команды:</b>\n"
        "  /me          — личный кабинет 👤\n"
        "  /miniapp     — расписание в приложении 📅\n"
        "  /grades      — мои оценки из eCampus\n"
        "  /stats       — статистика успеваемости 📊\n"
        "  /subjects    — список предметов\n"
        "  /classmates  — мои одногруппники 👥\n"
        "  /teacher     — найти преподавателя\n"
        "  /ecampus     — статус eCampus\n"
        "  /limit       — лимит запросов\n"
        "  /language    — язык интерфейса 🌐\n"
        "  /support     — поддержка\n"
        "  /suggest     — предложить идею\n\n"
        "💡 <i>В группах обращайтесь через упоминание: @botname запрос</i>"
    ),
    "help.quick": (
        "📖 <b>Быстрая справка</b>\n\n"
        "/me       — этот экран\n"
        "/grades   — оценки из eCampus\n"
        "/stats    — статистика (с выбором семестра)\n"
        "/subjects — список предметов\n"
        "/teacher  — поиск преподавателя\n"
        "/classmates — одногруппники\n"
        "/limit    — лимит запросов\n"
        "/miniapp  — открыть приложение\n"
        "/help     — полная справка"
    ),

    # ── Группа: приветствие при добавлении бота ─────────────────────────────────
    "group_welcome.text": (
        "👋 Привет! Рад присоединиться к <b>{chat_title}</b>!\n\n"
        "📌 <b>Что я умею:</b>\n"
        "  • Расписание группы, преподавателя, аудитории\n"
        "  • Свободные аудитории прямо сейчас\n"
        "  • Поиск по преподавателям и группам\n\n"
        "💬 <b>Как обращаться:</b>\n"
        "  Упомяните меня: <code>@{bot_username} расписание ИСС-б-о-22-3</code>\n"
        "  Или используйте команды:\n"
        "  /help — все возможности\n"
        "  /miniapp — расписание в приложении 📅\n\n"
        "🔕 <i>Я не слежу за общим чатом — отвечаю только на упоминания и команды.</i>"
    ),
    "group_welcome.default_title": "эту группу",
    "common.open_schedule_button": "📅 Открыть расписание",

    # ── /mykey (отключена) ───────────────────────────────────────────────────
    "mykey.disabled": "Команда /mykey отключена.",

    # ── /roles ───────────────────────────────────────────────────────────────
    "roles.role.admin": "Администратор",
    "roles.role.moderator": "Модератор",
    "roles.role.vip": "VIP",
    "roles.role.beta": "Бета-тестер",
    "roles.role.user": "Пользователь",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>Роли:</b>",
    "roles.privileges_label": "\n🔓 <b>Привилегии:</b>",
    "roles.priv_admin_panel": "⚙️ <b>Панель управления</b> → <a href=\"{url}\">открыть</a>",
    "roles.priv_beta": "🧪 <b>Бета-доступ</b> — расширенные фильтры расписания",
    "roles.priv_floorplan_edit": "🗺 <b>Редактирование</b> планов этажей",
    "roles.priv_floorplan_view": "🗺 <b>Просмотр</b> планов этажей",
    "roles.priv_personal_limit": "📊 <b>Персональный лимит</b>: {limit} запросов / период",
    "roles.profile_link": "\n💼 <b>Личный кабинет:</b> <a href=\"{url}\">открыть</a>",

    # ── /suggest ─────────────────────────────────────────────────────────────
    "suggest.prompt": (
        "💡 <b>Предложения и идеи</b>\n\n"
        "Есть идея, как улучшить бот или расписание?\n"
        "Напишите её после команды:\n\n"
        "<code>/suggest Ваша идея здесь</code>\n\n"
        "<i>Например: /suggest Добавить уведомление за 10 минут до пары</i>"
    ),
    "suggest.accepted": "✅ <b>Предложение принято!</b>\n\nСпасибо, ваша идея поможет сделать бот лучше.\nНомер: <code>{ticket_id}</code>\n",

    # ── /about ───────────────────────────────────────────────────────────────
    "about.text": (
        "🎓 <b>Бот расписания СКФУ</b>\n\n"
        "Умный помощник для студентов и преподавателей "
        "Северо-Кавказского федерального университета.\n\n"
        "📌 <b>Возможности:</b>\n"
        "  • Расписание групп, преподавателей, аудиторий\n"
        "  • Свободные аудитории в реальном времени\n"
        "  • Поиск по группам и преподавателям\n"
        "  • Mini App с полным расписанием 📅\n\n"
        "🔗 <b>Ссылки:</b>\n"
        "  • <a href=\"{miniapp_url}\">Mini App расписания</a>\n"
        "🛠 <b>Версия:</b> 2.0\n"
        "💬 Вопросы и предложения: /support · /suggest"
    ),

    # ── /miniapp ─────────────────────────────────────────────────────────────
    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — полное расписание в приложении\n\n"
        "• Гибкий поиск по группе, преподавателю, аудитории\n"
        "• Свободные аудитории в реальном времени\n"
        "• Планы этажей корпусов\n"
        "• Избранное и персональные настройки\n\n"
        "Нажмите кнопку ниже 👇"
    ),

    # ── /support ─────────────────────────────────────────────────────────────
    "support.prompt": "📬 <b>Поддержка</b>\n\nНапишите ваш вопрос после команды:\n<code>/support Ваш вопрос здесь</code>",
    "support.accepted": "✅ <b>Обращение принято</b>\n\nМы ответим вам как можно скорее.\nНомер обращения: <code>{ticket_id}</code>",

    # ── /limit ───────────────────────────────────────────────────────────────
    "limit.header": "📊 <b>Лимит {scope}</b>",
    "limit.scope_private": "личных запросов",
    "limit.scope_chat": "запросов в этом чате",
    "limit.used": "✅ Использовано: <b>{used}</b>",
    "limit.remaining": "💬 Осталось: <b>{remaining}</b>",
    "limit.max": "🏁 Максимум: <b>{cap}</b>",
    "limit.reset_in": "🔄 Сброс через: <b>{reset_str}</b>",
    "limit.reset_done": "🔄 Лимит уже сброшен — можно использовать снова",
    "limit.exhausted_note": "<i>Лимит исчерпан. Подождите сброса или обратитесь к администратору.</i>",
    "limit.normal_note": "<i>Лимит считает запросы к ИИ (расписание, поиск). Команды /start, /help и другие не учитываются.</i>",

    # ── /login, /code, подтверждение входа ──────────────────────────────────
    "login.instructions": (
        "🔐 <b>Вход на сайт</b>\n\n"
        "1. Откройте <a href=\"{web_url}/profile\">{web_url}/profile</a>\n"
        "2. Нажмите <b>«Войти через Telegram»</b>\n"
        "3. Вам покажут <b>6-буквенный код</b> (заглавные латинские)\n"
        "4. Отправьте этот код командой <code>/code XXXXXX</code>\n"
        "5. Подтвердите вход — страница обновится автоматически\n\n"
        "💡 Или просто напишите <code>/code</code> и код через пробел."
    ),
    "login.code_missing": "❓ Укажи код после команды:\n<code>/code XXXXXX</code>\n\nКод отображается на сайте при нажатии «Войти через Telegram».",
    "login.code_invalid_format": "❌ Код должен состоять из <b>6 заглавных букв и цифр</b>.\nПример: <code>/code ABCDEF</code>",
    "login.account_blocked": "❌ Ваш аккаунт заблокирован.",
    "login.server_error": "⚠️ Ошибка сервера. Попробуйте позже.",
    "login.code_error": "❌ <b>{error}</b>\n\nПроверьте код на сайте и попробуйте снова.\nКод действителен <b>3 минуты</b>.",
    "login.code_error_default": "Неверный или истёкший код",
    "login.code_error_server": "Ошибка сервера",
    "login.confirm_prompt": "🔐 <b>Подтверждение входа</b>\n\nПривет, {name}! Кто-то входит на сайт с твоим аккаунтом.\n\nПодтвердить вход?",
    "login.confirm_button": "✅ Подтвердить вход",
    "login.cancel_button": "❌ Отмена",
    "login.cancelled": "❌ <b>Вход отменён.</b>\n\nЕсли это были не вы — ничего страшного, ссылка уже недействительна.",
    "login.cancelled_toast": "Вход отменён",
    "login.confirm_error": "⚠️ <b>Ошибка подтверждения.</b>\n\nВозможно, сессия истекла. Попробуйте войти снова.",
    "login.confirm_error_toast": "Ошибка, попробуйте снова",
    "login.confirmed": "✅ <b>Вход подтверждён!</b>\n\nСтраница на сайте обновится автоматически.",
    "login.confirmed_toast": "Вход выполнен ✅",
    "login.default_name": "пользователь",

    # ── Дизамбигуация (выбор группы/аудитории) ──────────────────────────────
    "disambig.stale_data": "⏱ Данные устарели. Повторите запрос.",
    "disambig.stale_button": "⚠️ Устаревшая кнопка. Повторите запрос.",
    "disambig.expired": "⏱ Время выбора истекло. Повторите запрос.",
    "disambig.loading": "⏳ Загружаю расписание…",
    "disambig.unknown_intent": "❓ Неизвестный тип запроса.",
    "disambig.error": "❌ Ошибка при загрузке расписания.\n<code>{eid}</code>",
    "disambig.format_error": "❌ Ошибка обработки расписания.",
    "disambig.day_of": "День {idx} из {total}",
    "disambig.prev_page": "◀ Пред.",
    "disambig.next_page": "След. ▶",
    "disambig.group_label": "группа #{id}",
    "disambig.room_label": "ауд. #{id}",
    "disambig.schedule_title": "Расписание · {title}",

    # ── Фидбэк 👍👎 ───────────────────────────────────────────────────────────
    "feedback.error_toast": "⚠️ Ошибка",
    "feedback.already_rated_toast": "Уже оценено ✓",
    "feedback.save_failed_toast": "⚠️ Не удалось сохранить оценку",
    "feedback.thanks_toast": "{icon} Оценка сохранена, спасибо!",

    # ── /classmates ──────────────────────────────────────────────────────────
    "classmates.profile_not_found": "👤 Не удалось найти ваш профиль.",
    "classmates.no_group": "👥 <b>Группа не настроена</b>\n\nНастройте профиль на сайте, чтобы видеть одногруппников.",
    "classmates.query_error": "❌ Ошибка при получении списка одногруппников.",
    "classmates.header": "👥 <b>Одногруппники · {group_label}</b>\n",
    "classmates.registered_count": "<i>Зарегистрировано: {count} чел.</i>\n",
    "classmates.none_registered": "👥 <b>Одногруппники · {group_label}</b>\n\nПока никто из вашей группы не зарегистрировался в боте.",
    "classmates.group_fallback_label": "группа #{id}",
    "classmates.more_suffix": "\n<i>…и ещё</i>",

    # ── /teacher ──────────────────────────────────────────────────────────────
    "teacher.search_prompt": "👤 <b>Поиск преподавателя</b>\n\nНапишите фамилию (или часть):\n<code>/teacher Иванов</code>",
    "teacher.search_error": "❌ Ошибка поиска.",
    "teacher.not_found": "🔍 По запросу <b>{query}</b> ничего не найдено.\n\nПопробуйте другую фамилию.",
    "teacher.found_count": "🔍 Найдено преподавателей: <b>{count}</b>\n\nВыберите:",
    "teacher.not_found_short": "❌ Преподаватель не найден.",
    "teacher.subjects_label": "\n📚 <b>Предметы:</b>",
    "teacher.more_subjects": "  <i>…и ещё {count}</i>",
    "teacher.lesson_types_label": "\n🗂 <b>Типы занятий:</b> {types}",
    "teacher.groups_label": "\n👥 <b>Группы ({count}):</b> {names}",
    "teacher.more_groups": "  <i>…и ещё {count}</i>",
    "teacher.lessons_in_db": "\n📊 Занятий в БД: <b>{count}</b>",
    "teacher.schedule_loaded": "🕐 Расписание: <b>загружено</b>",
    "teacher.alltime_stats_label": "\n📈 <b>Статистика за всё время:</b>",
    "teacher.total_lessons": "  Всего пар: <b>{count}</b>",
    "teacher.types_label": "  Типы: {types}",
    "teacher.buildings_label": "  Корпуса: {buildings}",
    "teacher.rooms_label": "  Аудитории: {rooms}",
    "teacher.schedule_button": "📅 Расписание",

    # ── /me ──────────────────────────────────────────────────────────────────
    "me.profile_not_found": "👤 Профиль не найден.",
    "me.header": "👤 <b>Личный кабинет</b>\n",
    "me.role_student": "Студент",
    "me.role_teacher": "Преподаватель",
    "me.role_unset": "Не настроен",
    "me.group_line": "\n📌 Группа: <b>{group_name}</b>",
    "me.teacher_line": "\n📌 Преподаватель: <b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 Лимит запросов: <code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 Моё расписание",
    "me.miniapp_button": "📱 Расписание (приложение)",
    "me.subjects_button": "📚 Предметы",
    "me.stats_button": "📊 Статистика",
    "me.classmates_button": "👥 Одногруппники",
    "me.my_lessons_button": "📈 Мои занятия",
    "me.profile_button": "⚙️ Профиль",
    "me.map_button": "🗺 Карта",
    "me.limit_button": "💬 Лимит запросов",
    "me.help_button": "❓ Помощь",
    "me.no_ecampus_data": "📭 Нет данных eCampus.",
    "me.stats_choose_period": "📊 <b>Статистика успеваемости</b>\n\nВыберите период:",

    # ── /grades ──────────────────────────────────────────────────────────────
    "grades.not_connected": "📚 <b>eCampus не подключён</b>\n\nПодключите аккаунт eCampus в разделе <b>Профиль → eCampus</b> на сайте или в мини-приложении.",
    "grades.sync_running": "⏳ Синхронизация с eCampus ещё идёт — данные обновляются.\nПопробуйте через минуту.",
    "grades.empty": "📭 Данные eCampus пока пусты.\nНажмите «Обновить» в мини-приложении или подождите автосинхронизации.",
    "grades.semester_label": "Семестр {n}",
    "grades.current_semester_label": "Текущий семестр",
    "grades.no_grades": "📭 <b>Оценок нет</b> ({sem_label})\n\nОценки появятся после того, как преподаватель их выставит.",
    "grades.header": "📊 <b>Оценки · {sem_label}</b>\n",
    "grades.total": "\n<i>Всего оценок: {count}</i>",
    "grades.page_suffix": "\n\n({page}/{total})",

    # ── /stats ───────────────────────────────────────────────────────────────
    "stats.not_connected_short": "📚 <b>eCampus не подключён</b>\n\nПодключите аккаунт в разделе Профиль на сайте.",
    "stats.no_data": "📭 Нет данных eCampus. Обновите синхронизацию.",
    "stats.no_term_data": "📭 Нет данных за этот семестр.",
    "stats.all_time_suffix": " · Всё время",
    "stats.term_fallback": " · сем.{id}",
    "stats.header": "📊 <b>Статистика успеваемости{suffix}</b>\n",
    "stats.subjects_count": "📚 Предметов:   <b>{count}</b>",
    "stats.grades_count": "✏️  Оценок:      <b>{count}</b>",
    "stats.exams_count": "🎓 Экзаменов:  <b>{count}</b>",
    "stats.credits_count": "📝 Зачётов:    <b>{count}</b>",
    "stats.rating": "⭐ Рейтинг:    {icon} <b>{avg:.1f}</b> / {max:.1f} ({pct:.0f}%)",
    "stats.updated_at": "\n<i>Обновлено: {dt}</i>",
    "stats.choose_period": "📊 <b>Статистика успеваемости</b>\n\nВыберите период:",
    "stats.all_time_button": "📊 За всё время",

    # ── /subjects ────────────────────────────────────────────────────────────
    "subjects.not_connected": "📚 <b>eCampus не подключён</b>\n\nПодключите аккаунт в разделе Профиль на сайте.",
    "subjects.no_data": "📭 Нет данных. Обновите синхронизацию.",
    "subjects.none_for_term": "📭 Предметы не найдены ({sem_label}).",
    "subjects.header": "📚 <b>Предметы · {sem_label}</b>  ({count} шт.)\n",
    "subjects.no_type_data": "нет данных",
    "subjects.rating_line": "\n    {icon} Рейтинг: <b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>Экзамен</i>",
    "subjects.credit_tag": " 📝<i>Зачёт</i>",

    # ── /ecampus ─────────────────────────────────────────────────────────────
    "ecampus.not_connected": (
        "📚 <b>eCampus СКФУ</b>\n\n"
        "Аккаунт <b>не подключён</b>.\n\n"
        "Подключите его в разделе <b>Профиль → eCampus</b> на сайте "
        "или в мини-приложении — и получите:\n"
        "  • Список предметов и оценок\n"
        "  • Статистику успеваемости\n"
        "  • Рейтинги по каждому курсу\n\n"
        "Команды (после подключения):\n"
        "  /grades   — мои оценки\n"
        "  /stats    — статистика успеваемости\n"
        "  /subjects — список предметов"
    ),
    "ecampus.status_ok": "✅ Синхронизировано",
    "ecampus.status_running": "⏳ Синхронизация...",
    "ecampus.status_error": "❌ Ошибка синхронизации",
    "ecampus.status_pending": "🕐 Ожидание синхронизации",
    "ecampus.header": "📚 <b>eCampus СКФУ</b>\n",
    "ecampus.status_line": "🔗 Статус: {status}",
    "ecampus.subjects_count": "📦 Предметов: <b>{count}</b>",
    "ecampus.grades_count": "✏️  Оценок: <b>{count}</b>",
    "ecampus.updated_at": "🕐 Обновлено: <b>{dt}</b>",
    "ecampus.current_term": "\n📅 Текущий семестр: <b>{term}</b>",
    "ecampus.term_subjects": "   Предметов: <b>{count}</b>",
    "ecampus.term_grades": "   Оценок: <b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>Команды:</b>\n"
        "  /grades   — мои оценки текущего семестра\n"
        "  /grades 2 — оценки за 2-й семестр\n"
        "  /stats    — полная статистика\n"
        "  /subjects — список предметов"
    ),

    # ── ИИ-обработчик (ошибки/заглушки) ─────────────────────────────────────
    "ai.empty_message": "Напишите что-нибудь 🙂",
    "ai.processing": "⏳ Обрабатываю...",
    "ai.unknown_request": "❓ Неизвестный запрос.",
    "ai.parse_failed": "❌ Не удалось распознать запрос. Попробуйте переформулировать.",
    "ai.execution_error": "❌ Ошибка при выполнении запроса.\n<code>{eid}</code>",
    "ai.processing_error": "❌ Ошибка обработки запроса.",

    # ── /language (новая команда) ───────────────────────────────────────────
    "language.prompt": "🌐 <b>Выберите язык интерфейса</b>\n\nЭтот выбор синхронизируется с сайтом и мини-приложением.",
    "language.saved": "✅ Язык изменён на <b>{name}</b>.",
    "language.save_failed": "⚠️ Не удалось сохранить язык. Попробуйте снова.",

    # ── Меню команд бота (BotCommand description) ───────────────────────────
    "cmd.start": "Начало работы",
    "cmd.me": "Личный кабинет 👤",
    "cmd.help": "Справка",
    "cmd.miniapp": "Открыть расписание (Mini App) 📅",
    "cmd.grades": "Мои оценки из eCampus",
    "cmd.stats": "Статистика успеваемости 📊",
    "cmd.subjects": "Список предметов",
    "cmd.classmates": "Мои одногруппники 👥",
    "cmd.teacher": "Найти преподавателя 👤",
    "cmd.ecampus": "Статус eCampus",
    "cmd.limit": "Лимит запросов",
    "cmd.language": "Язык интерфейса 🌐",
    "cmd.login": "Войти на сайт",
    "cmd.code": "Ввести код (/code XXXXXX)",
    "cmd.support": "Поддержка",
    "cmd.suggest": "Предложить идею",
    "cmd.about": "О боте",
}
