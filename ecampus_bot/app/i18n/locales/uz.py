"""O'zbek tili — ru.py asosida tayyorlangan tarjima."""

MESSAGES: dict[str, str] = {
    # ── /start ───────────────────────────────────────────────────────────────
    "start.greeting": (
        "👋 Salom! Men SKFU dars jadvali botiman.\n\n"
        "Savolingizni tabiiy tilda yozing:\n"
        "  • <i>ИСС-б-о-22-3 guruhining shu haftalik jadvali</i>\n"
        "  • <i>Podzolkoning darsi 5 daqiqadan keyin qayerda?</i>\n"
        "  • <i>11-bino bo'sh xonalari</i>\n"
        "  • <i>АИС-б-о-25-1 guruhida hozir nima bor?</i>\n\n"
        "📋 <b>Buyruqlar:</b>\n"
        "  /me         — shaxsiy kabinet 👤\n"
        "  /miniapp    — ilovada jadval 📅\n"
        "  /grades     — eCampus-dagi baholarim\n"
        "  /stats      — statistika 📊\n"
        "  /classmates — guruhdoshlar 👥\n"
        "  /teacher    — o'qituvchini topish\n"
        "  /help       — to'liq yordam"
    ),
    "start.login_welcome": "👋 Salom, {name}!\n\n🔐 <b>Yangi kirish usuli</b>\n\n1. <a href=\"{web_url}/profile\">{web_url}/profile</a> ni oching\n2. <b>«Telegram orqali kirish»</b> tugmasini bosing\n3. Ko'rsatilgan <b>6 xonali kodni</b> menga yuboring\n4. Tasdiqlang — sahifa o'zi yangilanadi ✨",

    # ── /help ────────────────────────────────────────────────────────────────
    "help.full": (
        "📖 <b>SKFU dars jadvali boti bo'yicha yordam</b>\n\n"
        "So'rovingizni tabiiy tilda yozing:\n\n"
        "📅 <b>Jadval:</b>\n"
        "  <i>ИСС-б-о-22-3 jadvali</i>\n"
        "  <i>АИС25 guruhida ertaga nima bor?</i>\n\n"
        "👤 <b>O'qituvchi:</b>\n"
        "  <i>Podzolko hozir qayerda?</i>  ·  <i>Ivanov jadvali</i>\n\n"
        "🚪 <b>Xonalar:</b>\n"
        "  <i>Hozir bo'sh xonalar</i>\n\n"
        "📋 <b>Buyruqlar:</b>\n"
        "  /me          — shaxsiy kabinet 👤\n"
        "  /miniapp     — ilovada jadval 📅\n"
        "  /grades      — eCampus-dagi baholarim\n"
        "  /stats       — o'zlashtirish statistikasi 📊\n"
        "  /subjects    — fanlar ro'yxati\n"
        "  /classmates  — guruhdoshlarim 👥\n"
        "  /teacher     — o'qituvchini topish\n"
        "  /ecampus     — eCampus holati\n"
        "  /limit       — so'rovlar chegarasi\n"
        "  /language    — interfeys tili 🌐\n"
        "  /support     — qo'llab-quvvatlash\n"
        "  /suggest     — g'oya taklif qilish\n\n"
        "💡 <i>Guruhlarda meni belgilab murojaat qiling: @botname so'rov</i>"
    ),
    "help.quick": (
        "📖 <b>Tezkor yordam</b>\n\n"
        "/me       — shu ekran\n"
        "/grades   — eCampus baholari\n"
        "/stats    — statistika (semestr tanlash bilan)\n"
        "/subjects — fanlar ro'yxati\n"
        "/teacher  — o'qituvchi qidirish\n"
        "/classmates — guruhdoshlar\n"
        "/limit    — so'rovlar chegarasi\n"
        "/miniapp  — ilovani ochish\n"
        "/help     — to'liq yordam"
    ),

    # ── Группа: приветствие при добавлении бота ─────────────────────────────────
    "group_welcome.text": (
        "👋 Salom! <b>{chat_title}</b> guruhiga qo'shilganimdan xursandman!\n\n"
        "📌 <b>Men nima qila olaman:</b>\n"
        "  • Guruh, o'qituvchi, xona jadvali\n"
        "  • Hozir bo'sh xonalar\n"
        "  • O'qituvchilar va guruhlar bo'yicha qidiruv\n\n"
        "💬 <b>Qanday murojaat qilish kerak:</b>\n"
        "  Meni belgilang: <code>@{bot_username} ИСС-б-о-22-3 jadvali</code>\n"
        "  Yoki buyruqlardan foydalaning:\n"
        "  /help — barcha imkoniyatlar\n"
        "  /miniapp — ilovada jadval 📅\n\n"
        "🔕 <i>Men umumiy chatni kuzatmayman — faqat belgilashlarga va buyruqlarga javob beraman.</i>"
    ),
    "group_welcome.default_title": "shu guruh",
    "common.open_schedule_button": "📅 Jadvalni ochish",

    # ── /mykey (отключена) ───────────────────────────────────────────────────
    "mykey.disabled": "/mykey buyrug'i o'chirilgan.",

    # ── /roles ───────────────────────────────────────────────────────────────
    "roles.role.admin": "Administrator",
    "roles.role.moderator": "Moderator",
    "roles.role.vip": "VIP",
    "roles.role.beta": "Beta-sinovchi",
    "roles.role.user": "Foydalanuvchi",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>Rollar:</b>",
    "roles.privileges_label": "\n🔓 <b>Imtiyozlar:</b>",
    "roles.priv_admin_panel": "⚙️ <b>Boshqaruv paneli</b> → <a href=\"{url}\">ochish</a>",
    "roles.priv_beta": "🧪 <b>Beta-kirish</b> — jadvalning kengaytirilgan filtrlari",
    "roles.priv_floorplan_edit": "🗺 Qavat rejalarini <b>tahrirlash</b>",
    "roles.priv_floorplan_view": "🗺 Qavat rejalarini <b>ko'rish</b>",
    "roles.priv_personal_limit": "📊 <b>Shaxsiy chegara</b>: {limit} so'rov / davr",
    "roles.profile_link": "\n💼 <b>Shaxsiy kabinet:</b> <a href=\"{url}\">ochish</a>",

    # ── /suggest ─────────────────────────────────────────────────────────────
    "suggest.prompt": (
        "💡 <b>Takliflar va g'oyalar</b>\n\n"
        "Botni yoki jadvalni yaxshilash uchun g'oyangiz bormi?\n"
        "Buyruqdan keyin yozing:\n\n"
        "<code>/suggest G'oyangiz shu yerda</code>\n\n"
        "<i>Masalan: /suggest Darsdan 10 daqiqa oldin bildirishnoma qo'shish</i>"
    ),
    "suggest.accepted": "✅ <b>Taklif qabul qilindi!</b>\n\nRahmat, g'oyangiz botni yaxshilashga yordam beradi.\nRaqam: <code>{ticket_id}</code>\n",

    # ── /about ───────────────────────────────────────────────────────────────
    "about.text": (
        "🎓 <b>SKFU dars jadvali boti</b>\n\n"
        "Shimoliy Kavkaz federal universiteti "
        "talaba va o'qituvchilari uchun aqlli yordamchi.\n\n"
        "📌 <b>Imkoniyatlar:</b>\n"
        "  • Guruhlar, o'qituvchilar, xonalar jadvali\n"
        "  • Real vaqtda bo'sh xonalar\n"
        "  • Guruh va o'qituvchilar bo'yicha qidiruv\n"
        "  • To'liq jadvalli Mini App 📅\n\n"
        "🔗 <b>Havolalar:</b>\n"
        "  • <a href=\"{miniapp_url}\">Jadval Mini App</a>\n"
        "🛠 <b>Versiya:</b> 2.0\n"
        "💬 Savol va takliflar: /support · /suggest"
    ),

    # ── /miniapp ─────────────────────────────────────────────────────────────
    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — ilovada to'liq jadval\n\n"
        "• Guruh, o'qituvchi, xona bo'yicha moslashuvchan qidiruv\n"
        "• Real vaqtda bo'sh xonalar\n"
        "• Binolarning qavat rejalari\n"
        "• Tanlanganlar va shaxsiy sozlamalar\n\n"
        "Quyidagi tugmani bosing 👇"
    ),

    # ── /support ─────────────────────────────────────────────────────────────
    "support.prompt": "📬 <b>Qo'llab-quvvatlash</b>\n\nSavolingizni buyruqdan keyin yozing:\n<code>/support Savolingiz shu yerda</code>",
    "support.accepted": "✅ <b>Murojaat qabul qilindi</b>\n\nSizga imkon qadar tezroq javob beramiz.\nMurojaat raqami: <code>{ticket_id}</code>",

    # ── /limit ───────────────────────────────────────────────────────────────
    "limit.header": "📊 <b>{scope} chegarasi</b>",
    "limit.scope_private": "shaxsiy so'rovlar",
    "limit.scope_chat": "shu chatdagi so'rovlar",
    "limit.used": "✅ Ishlatilgan: <b>{used}</b>",
    "limit.remaining": "💬 Qolgan: <b>{remaining}</b>",
    "limit.max": "🏁 Maksimum: <b>{cap}</b>",
    "limit.reset_in": "🔄 Yangilanish: <b>{reset_str}</b> dan keyin",
    "limit.reset_done": "🔄 Chegara allaqachon yangilangan — qayta foydalanish mumkin",
    "limit.exhausted_note": "<i>Chegara tugadi. Yangilanishini kuting yoki administratorga murojaat qiling.</i>",
    "limit.normal_note": "<i>Chegara AI so'rovlarini hisoblaydi (jadval, qidiruv). /start, /help va boshqa buyruqlar hisoblanmaydi.</i>",

    # ── /login, /code, подтверждение входа ──────────────────────────────────
    "login.instructions": (
        "🔐 <b>Saytga kirish</b>\n\n"
        "1. <a href=\"{web_url}/profile\">{web_url}/profile</a> ni oching\n"
        "2. <b>«Telegram orqali kirish»</b> tugmasini bosing\n"
        "3. Sizga <b>6 harfli kod</b> ko'rsatiladi (bosh lotin harflari)\n"
        "4. Bu kodni <code>/code XXXXXX</code> buyrug'i bilan yuboring\n"
        "5. Kirishni tasdiqlang — sahifa avtomatik yangilanadi\n\n"
        "💡 Yoki shunchaki <code>/code</code> deb yozib, kodni bo'sh joydan keyin yozing."
    ),
    "login.code_missing": "❓ Buyruqdan keyin kodni ko'rsating:\n<code>/code XXXXXX</code>\n\nKod saytda «Telegram orqali kirish» tugmasini bosganda ko'rsatiladi.",
    "login.code_invalid_format": "❌ Kod <b>6 bosh harf va raqamdan</b> iborat bo'lishi kerak.\nMisol: <code>/code ABCDEF</code>",
    "login.account_blocked": "❌ Sizning hisobingiz bloklangan.",
    "login.server_error": "⚠️ Server xatosi. Keyinroq qayta urinib ko'ring.",
    "login.code_error": "❌ <b>{error}</b>\n\nKodni saytda tekshirib, qayta urinib ko'ring.\nKod <b>3 daqiqa</b> amal qiladi.",
    "login.code_error_default": "Noto'g'ri yoki muddati o'tgan kod",
    "login.code_error_server": "Server xatosi",
    "login.confirm_prompt": "🔐 <b>Kirishni tasdiqlash</b>\n\nSalom, {name}! Kimdir sizning hisobingiz orqali saytga kirmoqchi.\n\nKirishni tasdiqlaysizmi?",
    "login.confirm_button": "✅ Kirishni tasdiqlash",
    "login.cancel_button": "❌ Bekor qilish",
    "login.cancelled": "❌ <b>Kirish bekor qilindi.</b>\n\nAgar bu siz bo'lmasangiz — xavotir olmang, havola endi yaroqsiz.",
    "login.cancelled_toast": "Kirish bekor qilindi",
    "login.confirm_error": "⚠️ <b>Tasdiqlash xatosi.</b>\n\nEhtimol, sessiya muddati tugagan. Qayta kirib ko'ring.",
    "login.confirm_error_toast": "Xato, qayta urinib ko'ring",
    "login.confirmed": "✅ <b>Kirish tasdiqlandi!</b>\n\nSaytdagi sahifa avtomatik yangilanadi.",
    "login.confirmed_toast": "Kirish muvaffaqiyatli amalga oshirildi ✅",
    "login.default_name": "foydalanuvchi",

    # ── Дизамбигуация (выбор группы/аудитории) ──────────────────────────────
    "disambig.stale_data": "⏱ Ma'lumotlar eskirgan. So'rovni qaytaring.",
    "disambig.stale_button": "⚠️ Eskirgan tugma. So'rovni qaytaring.",
    "disambig.expired": "⏱ Tanlash vaqti tugadi. So'rovni qaytaring.",
    "disambig.loading": "⏳ Jadval yuklanmoqda…",
    "disambig.unknown_intent": "❓ Noma'lum so'rov turi.",
    "disambig.error": "❌ Jadvalni yuklash xatosi.\n<code>{eid}</code>",
    "disambig.format_error": "❌ Jadvalni qayta ishlash xatosi.",
    "disambig.day_of": "{total} dan {idx}-kun",
    "disambig.prev_page": "◀ Oldingi",
    "disambig.next_page": "Keyingi ▶",
    "disambig.group_label": "guruh #{id}",
    "disambig.room_label": "xona #{id}",
    "disambig.schedule_title": "Jadval · {title}",

    # ── Фидбэк 👍👎 ───────────────────────────────────────────────────────────
    "feedback.error_toast": "⚠️ Xato",
    "feedback.already_rated_toast": "Allaqachon baholangan ✓",
    "feedback.save_failed_toast": "⚠️ Bahoni saqlash mumkin bo'lmadi",
    "feedback.thanks_toast": "{icon} Baho saqlandi, rahmat!",

    # ── /classmates ──────────────────────────────────────────────────────────
    "classmates.profile_not_found": "👤 Profilingiz topilmadi.",
    "classmates.no_group": "👥 <b>Guruh belgilanmagan</b>\n\nGuruhdoshlaringizni ko'rish uchun saytda profilingizni sozlang.",
    "classmates.query_error": "❌ Guruhdoshlar ro'yxatini olishda xato.",
    "classmates.header": "👥 <b>Guruhdoshlar · {group_label}</b>\n",
    "classmates.registered_count": "<i>Ro'yxatdan o'tgan: {count} kishi.</i>\n",
    "classmates.none_registered": "👥 <b>Guruhdoshlar · {group_label}</b>\n\nGuruhingizdan hali hech kim botda ro'yxatdan o'tmagan.",
    "classmates.group_fallback_label": "guruh #{id}",
    "classmates.more_suffix": "\n<i>…va boshqalar</i>",

    # ── /teacher ──────────────────────────────────────────────────────────────
    "teacher.search_prompt": "👤 <b>O'qituvchi qidiruvi</b>\n\nFamiliyani (yoki uning bir qismini) yozing:\n<code>/teacher Ivanov</code>",
    "teacher.search_error": "❌ Qidirishda xato.",
    "teacher.not_found": "🔍 <b>{query}</b> bo'yicha hech narsa topilmadi.\n\nBoshqa familiya urinib ko'ring.",
    "teacher.found_count": "🔍 Topilgan o'qituvchilar: <b>{count}</b>\n\nTanlang:",
    "teacher.not_found_short": "❌ O'qituvchi topilmadi.",
    "teacher.subjects_label": "\n📚 <b>Fanlar:</b>",
    "teacher.more_subjects": "  <i>…va yana {count}</i>",
    "teacher.lesson_types_label": "\n🗂 <b>Dars turlari:</b> {types}",
    "teacher.groups_label": "\n👥 <b>Guruhlar ({count}):</b> {names}",
    "teacher.more_groups": "  <i>…va yana {count}</i>",
    "teacher.lessons_in_db": "\n📊 Bazadagi darslar: <b>{count}</b>",
    "teacher.schedule_loaded": "🕐 Jadval: <b>yuklandi</b>",
    "teacher.alltime_stats_label": "\n📈 <b>Barcha vaqt statistikasi:</b>",
    "teacher.total_lessons": "  Jami darslar: <b>{count}</b>",
    "teacher.types_label": "  Turlari: {types}",
    "teacher.buildings_label": "  Binolar: {buildings}",
    "teacher.rooms_label": "  Xonalar: {rooms}",
    "teacher.schedule_button": "📅 Jadval",

    # ── /me ──────────────────────────────────────────────────────────────────
    "me.profile_not_found": "👤 Profil topilmadi.",
    "me.header": "👤 <b>Shaxsiy kabinet</b>\n",
    "me.role_student": "Talaba",
    "me.role_teacher": "O'qituvchi",
    "me.role_unset": "Sozlanmagan",
    "me.group_line": "\n📌 Guruh: <b>{group_name}</b>",
    "me.teacher_line": "\n📌 O'qituvchi: <b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 So'rovlar chegarasi: <code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 Mening jadvalim",
    "me.miniapp_button": "📱 Jadval (ilova)",
    "me.subjects_button": "📚 Fanlar",
    "me.stats_button": "📊 Statistika",
    "me.classmates_button": "👥 Guruhdoshlar",
    "me.my_lessons_button": "📈 Mening darslarim",
    "me.profile_button": "⚙️ Profil",
    "me.map_button": "🗺 Xarita",
    "me.limit_button": "💬 So'rovlar chegarasi",
    "me.help_button": "❓ Yordam",
    "me.no_ecampus_data": "📭 eCampus ma'lumotlari yo'q.",
    "me.stats_choose_period": "📊 <b>O'zlashtirish statistikasi</b>\n\nDavrni tanlang:",

    # ── /grades ──────────────────────────────────────────────────────────────
    "grades.not_connected": "📚 <b>eCampus ulanmagan</b>\n\neCampus hisobini saytda yoki mini-ilovada <b>Profil → eCampus</b> bo'limida ulang.",
    "grades.sync_running": "⏳ eCampus bilan sinxronlash hali davom etmoqda — ma'lumotlar yangilanmoqda.\nBir daqiqadan keyin qayta urinib ko'ring.",
    "grades.empty": "📭 eCampus ma'lumotlari hali bo'sh.\nMini-ilovada «Yangilash» tugmasini bosing yoki avtosinxronlanishini kuting.",
    "grades.semester_label": "{n}-semestr",
    "grades.current_semester_label": "Joriy semestr",
    "grades.no_grades": "📭 <b>Baholar yo'q</b> ({sem_label})\n\nBaholar o'qituvchi ularni qo'ygandan keyin paydo bo'ladi.",
    "grades.header": "📊 <b>Baholar · {sem_label}</b>\n",
    "grades.total": "\n<i>Jami baholar: {count}</i>",
    "grades.page_suffix": "\n\n({page}/{total})",

    # ── /stats ───────────────────────────────────────────────────────────────
    "stats.not_connected_short": "📚 <b>eCampus ulanmagan</b>\n\nHisobni saytda Profil bo'limida ulang.",
    "stats.no_data": "📭 eCampus ma'lumotlari yo'q. Sinxronlanishni yangilang.",
    "stats.no_term_data": "📭 Shu semestr bo'yicha ma'lumot yo'q.",
    "stats.all_time_suffix": " · Barcha vaqt",
    "stats.term_fallback": " · sem.{id}",
    "stats.header": "📊 <b>O'zlashtirish statistikasi{suffix}</b>\n",
    "stats.subjects_count": "📚 Fanlar:   <b>{count}</b>",
    "stats.grades_count": "✏️  Baholar:      <b>{count}</b>",
    "stats.exams_count": "🎓 Imtihonlar:  <b>{count}</b>",
    "stats.credits_count": "📝 Zachyotlar:    <b>{count}</b>",
    "stats.rating": "⭐ Reyting:    {icon} <b>{avg:.1f}</b> / {max:.1f} ({pct:.0f}%)",
    "stats.updated_at": "\n<i>Yangilangan: {dt}</i>",
    "stats.choose_period": "📊 <b>O'zlashtirish statistikasi</b>\n\nDavrni tanlang:",
    "stats.all_time_button": "📊 Barcha vaqt uchun",

    # ── /subjects ────────────────────────────────────────────────────────────
    "subjects.not_connected": "📚 <b>eCampus ulanmagan</b>\n\nHisobni saytda Profil bo'limida ulang.",
    "subjects.no_data": "📭 Ma'lumot yo'q. Sinxronlanishni yangilang.",
    "subjects.none_for_term": "📭 Fanlar topilmadi ({sem_label}).",
    "subjects.header": "📚 <b>Fanlar · {sem_label}</b>  ({count} ta)\n",
    "subjects.no_type_data": "ma'lumot yo'q",
    "subjects.rating_line": "\n    {icon} Reyting: <b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>Imtihon</i>",
    "subjects.credit_tag": " 📝<i>Zachyot</i>",

    # ── /ecampus ─────────────────────────────────────────────────────────────
    "ecampus.not_connected": (
        "📚 <b>SKFU eCampus</b>\n\n"
        "Hisob <b>ulanmagan</b>.\n\n"
        "Uni saytda yoki mini-ilovada <b>Profil → eCampus</b> "
        "bo'limida ulang va quyidagilarga ega bo'ling:\n"
        "  • Fanlar va baholar ro'yxati\n"
        "  • O'zlashtirish statistikasi\n"
        "  • Har bir kurs bo'yicha reytinglar\n\n"
        "Buyruqlar (ulangandan keyin):\n"
        "  /grades   — baholarim\n"
        "  /stats    — o'zlashtirish statistikasi\n"
        "  /subjects — fanlar ro'yxati"
    ),
    "ecampus.status_ok": "✅ Sinxronlangan",
    "ecampus.status_running": "⏳ Sinxronlanmoqda...",
    "ecampus.status_error": "❌ Sinxronlash xatosi",
    "ecampus.status_pending": "🕐 Sinxronlanish kutilmoqda",
    "ecampus.header": "📚 <b>SKFU eCampus</b>\n",
    "ecampus.status_line": "🔗 Holat: {status}",
    "ecampus.subjects_count": "📦 Fanlar: <b>{count}</b>",
    "ecampus.grades_count": "✏️  Baholar: <b>{count}</b>",
    "ecampus.updated_at": "🕐 Yangilangan: <b>{dt}</b>",
    "ecampus.current_term": "\n📅 Joriy semestr: <b>{term}</b>",
    "ecampus.term_subjects": "   Fanlar: <b>{count}</b>",
    "ecampus.term_grades": "   Baholar: <b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>Buyruqlar:</b>\n"
        "  /grades   — joriy semestr baholarim\n"
        "  /grades 2 — 2-semestr baholari\n"
        "  /stats    — to'liq statistika\n"
        "  /subjects — fanlar ro'yxati"
    ),

    # ── ИИ-обработчик (ошибки/заглушки) ─────────────────────────────────────
    "ai.empty_message": "Biror narsa yozing 🙂",
    "ai.processing": "⏳ Qayta ishlanmoqda...",
    "ai.unknown_request": "❓ Noma'lum so'rov.",
    "ai.parse_failed": "❌ So'rovni aniqlab bo'lmadi. Qayta ifodalab ko'ring.",
    "ai.execution_error": "❌ So'rovni bajarishda xato.\n<code>{eid}</code>",
    "ai.processing_error": "❌ So'rovni qayta ishlashda xato.",

    # ── /language (новая команда) ───────────────────────────────────────────
    "language.prompt": "🌐 <b>Interfeys tilini tanlang</b>\n\nBu tanlov sayt va mini-ilova bilan sinxronlanadi.",
    "language.saved": "✅ Til <b>{name}</b> ga o'zgartirildi.",
    "language.save_failed": "⚠️ Tilni saqlash mumkin bo'lmadi. Qayta urinib ko'ring.",

    # ── Меню команд бота (BotCommand description) ───────────────────────────
    "cmd.start": "Ishni boshlash",
    "cmd.me": "Shaxsiy kabinet 👤",
    "cmd.help": "Yordam",
    "cmd.miniapp": "Jadvalni ochish (Mini App) 📅",
    "cmd.grades": "eCampus-dagi baholarim",
    "cmd.stats": "O'zlashtirish statistikasi 📊",
    "cmd.subjects": "Fanlar ro'yxati",
    "cmd.classmates": "Guruhdoshlarim 👥",
    "cmd.teacher": "O'qituvchini topish 👤",
    "cmd.ecampus": "eCampus holati",
    "cmd.limit": "So'rovlar chegarasi",
    "cmd.language": "Interfeys tili 🌐",
    "cmd.login": "Saytga kirish",
    "cmd.code": "Kodni kiritish (/code XXXXXX)",
    "cmd.support": "Qo'llab-quvvatlash",
    "cmd.suggest": "G'oya taklif qilish",
    "cmd.about": "Bot haqida",
}
