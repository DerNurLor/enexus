"""हिन्दी — ru.py पर आधारित अनुवाद।"""

MESSAGES: dict[str, str] = {
    # ── /start ───────────────────────────────────────────────────────────────
    "start.greeting": (
        "👋 नमस्ते! मैं SKFU शेड्यूल बॉट हूँ।\n\n"
        "अपना सवाल सामान्य भाषा में लिखें:\n"
        "  • <i>ИСС-б-о-22-3 ग्रुप का इस हफ्ते का शेड्यूल</i>\n"
        "  • <i>5 मिनट में Подзолко की क्लास कहाँ है?</i>\n"
        "  • <i>बिल्डिंग 11 में खाली कमरे</i>\n"
        "  • <i>АИС-б-о-25-1 ग्रुप में अभी क्या है?</i>\n\n"
        "📋 <b>कमांड्स:</b>\n"
        "  /me         — पर्सनल कैबिनेट 👤\n"
        "  /miniapp    — ऐप में शेड्यूल 📅\n"
        "  /grades     — eCampus से मेरे ग्रेड\n"
        "  /stats      — स्टैटिस्टिक्स 📊\n"
        "  /classmates — क्लासमेट्स 👥\n"
        "  /teacher    — टीचर ढूँढें\n"
        "  /help       — पूरी मदद"
    ),
    "start.login_welcome": "👋 नमस्ते, {name}!\n\n🔐 <b>लॉगिन का नया तरीका</b>\n\n1. <a href=\"{web_url}/profile\">{web_url}/profile</a> खोलें\n2. <b>«Telegram से लॉगिन करें»</b> बटन दबाएँ\n3. दिखाया गया <b>6-अंकों का कोड</b> मुझे भेजें\n4. कन्फर्म करें — पेज खुद अपडेट हो जाएगा ✨",

    # ── /help ────────────────────────────────────────────────────────────────
    "help.full": (
        "📖 <b>SKFU शेड्यूल बॉट की मदद</b>\n\n"
        "अपना सवाल सामान्य भाषा में लिखें:\n\n"
        "📅 <b>शेड्यूल:</b>\n"
        "  <i>ИСС-б-о-22-3 का शेड्यूल</i>\n"
        "  <i>АИС25 ग्रुप में कल क्या है?</i>\n\n"
        "👤 <b>टीचर:</b>\n"
        "  <i>Подзолко अभी कहाँ है?</i>  ·  <i>Иванов का शेड्यूल</i>\n\n"
        "🚪 <b>कमरे:</b>\n"
        "  <i>अभी खाली कमरे</i>\n\n"
        "📋 <b>कमांड्स:</b>\n"
        "  /me          — पर्सनल कैबिनेट 👤\n"
        "  /miniapp     — ऐप में शेड्यूल 📅\n"
        "  /grades      — eCampus से मेरे ग्रेड\n"
        "  /stats       — परफॉर्मेंस स्टैटिस्टिक्स 📊\n"
        "  /subjects    — विषयों की सूची\n"
        "  /classmates  — मेरे क्लासमेट्स 👥\n"
        "  /teacher     — टीचर ढूँढें\n"
        "  /ecampus     — eCampus स्टेटस\n"
        "  /limit       — रिक्वेस्ट लिमिट\n"
        "  /language    — इंटरफ़ेस की भाषा 🌐\n"
        "  /support     — सपोर्ट\n"
        "  /suggest     — आइडिया सुझाएँ\n\n"
        "💡 <i>ग्रुप्स में मुझे मेंशन करके पूछें: @botname सवाल</i>"
    ),
    "help.quick": (
        "📖 <b>क्विक हेल्प</b>\n\n"
        "/me       — यह स्क्रीन\n"
        "/grades   — eCampus ग्रेड\n"
        "/stats    — स्टैटिस्टिक्स (सेमेस्टर चुनने के साथ)\n"
        "/subjects — विषयों की सूची\n"
        "/teacher  — टीचर सर्च\n"
        "/classmates — क्लासमेट्स\n"
        "/limit    — रिक्वेस्ट लिमिट\n"
        "/miniapp  — ऐप खोलें\n"
        "/help     — पूरी मदद"
    ),

    # ── Группа: приветствие при добавлении бота ─────────────────────────────────
    "group_welcome.text": (
        "👋 नमस्ते! <b>{chat_title}</b> में जुड़कर खुशी हुई!\n\n"
        "📌 <b>मैं क्या कर सकता हूँ:</b>\n"
        "  • ग्रुप, टीचर, कमरे का शेड्यूल\n"
        "  • अभी खाली कमरे\n"
        "  • टीचर्स और ग्रुप्स में सर्च\n\n"
        "💬 <b>कैसे पूछें:</b>\n"
        "  मुझे मेंशन करें: <code>@{bot_username} ИСС-б-о-22-3 का शेड्यूल</code>\n"
        "  या कमांड्स इस्तेमाल करें:\n"
        "  /help — सभी फ़ीचर्स\n"
        "  /miniapp — ऐप में शेड्यूल 📅\n\n"
        "🔕 <i>मैं सामान्य चैट को मॉनिटर नहीं करता — सिर्फ मेंशन और कमांड्स का जवाब देता हूँ।</i>"
    ),
    "group_welcome.default_title": "यह ग्रुप",
    "common.open_schedule_button": "📅 शेड्यूल खोलें",

    # ── /mykey (отключена) ───────────────────────────────────────────────────
    "mykey.disabled": "/mykey कमांड बंद है।",

    # ── /roles ───────────────────────────────────────────────────────────────
    "roles.role.admin": "एडमिन",
    "roles.role.moderator": "मॉडरेटर",
    "roles.role.vip": "VIP",
    "roles.role.beta": "बीटा-टेस्टर",
    "roles.role.user": "यूज़र",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>रोल्स:</b>",
    "roles.privileges_label": "\n🔓 <b>विशेषाधिकार:</b>",
    "roles.priv_admin_panel": "⚙️ <b>एडमिन पैनल</b> → <a href=\"{url}\">खोलें</a>",
    "roles.priv_beta": "🧪 <b>बीटा एक्सेस</b> — शेड्यूल के एक्सटेंडेड फ़िल्टर",
    "roles.priv_floorplan_edit": "🗺 फ़्लोर प्लान <b>एडिट</b> करना",
    "roles.priv_floorplan_view": "🗺 फ़्लोर प्लान <b>देखना</b>",
    "roles.priv_personal_limit": "📊 <b>पर्सनल लिमिट</b>: {limit} रिक्वेस्ट / पीरियड",
    "roles.profile_link": "\n💼 <b>पर्सनल कैबिनेट:</b> <a href=\"{url}\">खोलें</a>",

    # ── /suggest ─────────────────────────────────────────────────────────────
    "suggest.prompt": (
        "💡 <b>सुझाव और आइडियाज़</b>\n\n"
        "बॉट या शेड्यूल को बेहतर बनाने का कोई आइडिया है?\n"
        "कमांड के बाद लिखें:\n\n"
        "<code>/suggest आपका आइडिया यहाँ</code>\n\n"
        "<i>उदाहरण: /suggest क्लास से 10 मिनट पहले नोटिफिकेशन जोड़ें</i>"
    ),
    "suggest.accepted": "✅ <b>सुझाव स्वीकार किया गया!</b>\n\nधन्यवाद, आपका आइडिया बॉट को बेहतर बनाने में मदद करेगा।\nनंबर: <code>{ticket_id}</code>\n",

    # ── /about ───────────────────────────────────────────────────────────────
    "about.text": (
        "🎓 <b>SKFU शेड्यूल बॉट</b>\n\n"
        "नॉर्थ कॉकेशस फ़ेडरल यूनिवर्सिटी के "
        "स्टूडेंट्स और टीचर्स के लिए स्मार्ट असिस्टेंट।\n\n"
        "📌 <b>फ़ीचर्स:</b>\n"
        "  • ग्रुप्स, टीचर्स, कमरों का शेड्यूल\n"
        "  • रियल-टाइम में खाली कमरे\n"
        "  • ग्रुप्स और टीचर्स में सर्च\n"
        "  • पूरे शेड्यूल वाला Mini App 📅\n\n"
        "🔗 <b>लिंक्स:</b>\n"
        "  • <a href=\"{miniapp_url}\">शेड्यूल Mini App</a>\n"
        "🛠 <b>वर्शन:</b> 2.0\n"
        "💬 सवाल और सुझाव: /support · /suggest"
    ),

    # ── /miniapp ─────────────────────────────────────────────────────────────
    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — ऐप में पूरा शेड्यूल\n\n"
        "• ग्रुप, टीचर, कमरे से फ़्लेक्सिबल सर्च\n"
        "• रियल-टाइम में खाली कमरे\n"
        "• बिल्डिंगों के फ़्लोर प्लान\n"
        "• फ़ेवरेट्स और पर्सनल सेटिंग्स\n\n"
        "नीचे दिया बटन दबाएँ 👇"
    ),

    # ── /support ─────────────────────────────────────────────────────────────
    "support.prompt": "📬 <b>सपोर्ट</b>\n\nअपना सवाल कमांड के बाद लिखें:\n<code>/support आपका सवाल यहाँ</code>",
    "support.accepted": "✅ <b>रिक्वेस्ट स्वीकार की गई</b>\n\nहम जल्द से जल्द जवाब देंगे।\nरिक्वेस्ट नंबर: <code>{ticket_id}</code>",

    # ── /limit ───────────────────────────────────────────────────────────────
    "limit.header": "📊 <b>{scope} की लिमिट</b>",
    "limit.scope_private": "पर्सनल रिक्वेस्ट्स",
    "limit.scope_chat": "इस चैट में रिक्वेस्ट्स",
    "limit.used": "✅ इस्तेमाल हुआ: <b>{used}</b>",
    "limit.remaining": "💬 बाकी: <b>{remaining}</b>",
    "limit.max": "🏁 अधिकतम: <b>{cap}</b>",
    "limit.reset_in": "🔄 रीसेट: <b>{reset_str}</b> में",
    "limit.reset_done": "🔄 लिमिट रीसेट हो चुकी है — फिर से इस्तेमाल कर सकते हैं",
    "limit.exhausted_note": "<i>लिमिट खत्म हो गई है। रीसेट का इंतज़ार करें या एडमिन से संपर्क करें।</i>",
    "limit.normal_note": "<i>लिमिट AI रिक्वेस्ट्स को काउंट करती है (शेड्यूल, सर्च)। /start, /help और दूसरे कमांड्स काउंट नहीं होते।</i>",

    # ── /login, /code, подтверждение входа ──────────────────────────────────
    "login.instructions": (
        "🔐 <b>साइट में लॉगिन</b>\n\n"
        "1. <a href=\"{web_url}/profile\">{web_url}/profile</a> खोलें\n"
        "2. <b>«Telegram से लॉगिन करें»</b> बटन दबाएँ\n"
        "3. आपको <b>6 अक्षरों का कोड</b> दिखेगा (बड़े लैटिन अक्षर)\n"
        "4. यह कोड <code>/code XXXXXX</code> कमांड से भेजें\n"
        "5. लॉगिन कन्फर्म करें — पेज खुद अपडेट हो जाएगा\n\n"
        "💡 या सिर्फ <code>/code</code> लिखकर कोड स्पेस के बाद लिखें।"
    ),
    "login.code_missing": "❓ कमांड के बाद कोड बताएँ:\n<code>/code XXXXXX</code>\n\nकोड साइट पर «Telegram से लॉगिन करें» दबाने पर दिखता है।",
    "login.code_invalid_format": "❌ कोड <b>6 बड़े अक्षरों और नंबरों</b> का होना चाहिए।\nउदाहरण: <code>/code ABCDEF</code>",
    "login.account_blocked": "❌ आपका अकाउंट ब्लॉक है।",
    "login.server_error": "⚠️ सर्वर एरर। बाद में कोशिश करें।",
    "login.code_error": "❌ <b>{error}</b>\n\nसाइट पर कोड चेक करें और फिर कोशिश करें।\nकोड <b>3 मिनट</b> तक वैध है।",
    "login.code_error_default": "गलत या एक्सपायर्ड कोड",
    "login.code_error_server": "सर्वर एरर",
    "login.confirm_prompt": "🔐 <b>लॉगिन कन्फर्मेशन</b>\n\nनमस्ते, {name}! कोई आपके अकाउंट से साइट में लॉगिन करने की कोशिश कर रहा है।\n\nलॉगिन कन्फर्म करें?",
    "login.confirm_button": "✅ लॉगिन कन्फर्म करें",
    "login.cancel_button": "❌ कैंसिल करें",
    "login.cancelled": "❌ <b>लॉगिन कैंसिल हुआ।</b>\n\nअगर यह आप नहीं थे — कोई बात नहीं, लिंक अब काम नहीं करेगा।",
    "login.cancelled_toast": "लॉगिन कैंसिल हुआ",
    "login.confirm_error": "⚠️ <b>कन्फर्मेशन एरर।</b>\n\nशायद सेशन एक्सपायर हो गया है। फिर से लॉगिन करने की कोशिश करें।",
    "login.confirm_error_toast": "एरर, फिर से कोशिश करें",
    "login.confirmed": "✅ <b>लॉगिन कन्फर्म हुआ!</b>\n\nसाइट का पेज खुद अपडेट हो जाएगा।",
    "login.confirmed_toast": "लॉगिन सफल हुआ ✅",
    "login.default_name": "यूज़र",

    # ── Дизамбигуация (выбор группы/аудитории) ──────────────────────────────
    "disambig.stale_data": "⏱ डेटा पुराना हो गया है। रिक्वेस्ट दोबारा भेजें।",
    "disambig.stale_button": "⚠️ पुराना बटन। रिक्वेस्ट दोबारा भेजें।",
    "disambig.expired": "⏱ चुनने का समय खत्म हुआ। रिक्वेस्ट दोबारा भेजें।",
    "disambig.loading": "⏳ शेड्यूल लोड हो रहा है…",
    "disambig.unknown_intent": "❓ अनजान रिक्वेस्ट टाइप।",
    "disambig.error": "❌ शेड्यूल लोड करने में एरर।\n<code>{eid}</code>",
    "disambig.format_error": "❌ शेड्यूल प्रोसेस करने में एरर।",
    "disambig.day_of": "दिन {idx} / {total}",
    "disambig.prev_page": "◀ पिछला",
    "disambig.next_page": "अगला ▶",
    "disambig.group_label": "ग्रुप #{id}",
    "disambig.room_label": "कमरा #{id}",
    "disambig.schedule_title": "शेड्यूल · {title}",

    # ── Фидбэк 👍👎 ───────────────────────────────────────────────────────────
    "feedback.error_toast": "⚠️ एरर",
    "feedback.already_rated_toast": "पहले से रेट किया गया ✓",
    "feedback.save_failed_toast": "⚠️ रेटिंग सेव नहीं हो पाई",
    "feedback.thanks_toast": "{icon} रेटिंग सेव हो गई, धन्यवाद!",

    # ── /classmates ──────────────────────────────────────────────────────────
    "classmates.profile_not_found": "👤 आपकी प्रोफ़ाइल नहीं मिली।",
    "classmates.no_group": "👥 <b>ग्रुप सेट नहीं है</b>\n\nक्लासमेट्स देखने के लिए साइट पर अपनी प्रोफ़ाइल सेट करें।",
    "classmates.query_error": "❌ क्लासमेट्स की लिस्ट लाने में एरर।",
    "classmates.header": "👥 <b>क्लासमेट्स · {group_label}</b>\n",
    "classmates.registered_count": "<i>रजिस्टर्ड: {count} लोग।</i>\n",
    "classmates.none_registered": "👥 <b>क्लासमेट्स · {group_label}</b>\n\nआपके ग्रुप से अभी तक कोई बॉट में रजिस्टर नहीं हुआ है।",
    "classmates.group_fallback_label": "ग्रुप #{id}",
    "classmates.more_suffix": "\n<i>…और भी</i>",

    # ── /teacher ──────────────────────────────────────────────────────────────
    "teacher.search_prompt": "👤 <b>टीचर सर्च</b>\n\nसरनेम (या उसका हिस्सा) लिखें:\n<code>/teacher Иванов</code>",
    "teacher.search_error": "❌ सर्च में एरर।",
    "teacher.not_found": "🔍 <b>{query}</b> के लिए कुछ नहीं मिला।\n\nदूसरा सरनेम कोशिश करें।",
    "teacher.found_count": "🔍 मिले टीचर्स: <b>{count}</b>\n\nचुनें:",
    "teacher.not_found_short": "❌ टीचर नहीं मिला।",
    "teacher.subjects_label": "\n📚 <b>विषय:</b>",
    "teacher.more_subjects": "  <i>…और {count} और</i>",
    "teacher.lesson_types_label": "\n🗂 <b>क्लास के टाइप:</b> {types}",
    "teacher.groups_label": "\n👥 <b>ग्रुप्स ({count}):</b> {names}",
    "teacher.more_groups": "  <i>…और {count} और</i>",
    "teacher.lessons_in_db": "\n📊 डेटाबेस में क्लासेज़: <b>{count}</b>",
    "teacher.schedule_loaded": "🕐 शेड्यूल: <b>लोड हो गया</b>",
    "teacher.alltime_stats_label": "\n📈 <b>सारे समय का स्टैटिस्टिक्स:</b>",
    "teacher.total_lessons": "  कुल क्लासेज़: <b>{count}</b>",
    "teacher.types_label": "  टाइप्स: {types}",
    "teacher.buildings_label": "  बिल्डिंग्स: {buildings}",
    "teacher.rooms_label": "  कमरे: {rooms}",
    "teacher.schedule_button": "📅 शेड्यूल",

    # ── /me ──────────────────────────────────────────────────────────────────
    "me.profile_not_found": "👤 प्रोफ़ाइल नहीं मिली।",
    "me.header": "👤 <b>पर्सनल कैबिनेट</b>\n",
    "me.role_student": "स्टूडेंट",
    "me.role_teacher": "टीचर",
    "me.role_unset": "सेट नहीं है",
    "me.group_line": "\n📌 ग्रुप: <b>{group_name}</b>",
    "me.teacher_line": "\n📌 टीचर: <b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 रिक्वेस्ट लिमिट: <code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 मेरा शेड्यूल",
    "me.miniapp_button": "📱 शेड्यूल (ऐप)",
    "me.subjects_button": "📚 विषय",
    "me.stats_button": "📊 स्टैटिस्टिक्स",
    "me.classmates_button": "👥 क्लासमेट्स",
    "me.my_lessons_button": "📈 मेरी क्लासेज़",
    "me.profile_button": "⚙️ प्रोफ़ाइल",
    "me.map_button": "🗺 मैप",
    "me.limit_button": "💬 रिक्वेस्ट लिमिट",
    "me.help_button": "❓ मदद",
    "me.no_ecampus_data": "📭 eCampus का डेटा नहीं है।",
    "me.stats_choose_period": "📊 <b>परफॉर्मेंस स्टैटिस्टिक्स</b>\n\nपीरियड चुनें:",

    # ── /grades ──────────────────────────────────────────────────────────────
    "grades.not_connected": "📚 <b>eCampus कनेक्ट नहीं है</b>\n\neCampus अकाउंट को साइट या मिनी-ऐप के <b>प्रोफ़ाइल → eCampus</b> सेक्शन में कनेक्ट करें।",
    "grades.sync_running": "⏳ eCampus के साथ सिंक अभी भी चल रहा है — डेटा अपडेट हो रहा है।\nएक मिनट बाद कोशिश करें।",
    "grades.empty": "📭 eCampus का डेटा अभी खाली है।\nमिनी-ऐप में «अपडेट करें» दबाएँ या ऑटो-सिंक का इंतज़ार करें।",
    "grades.semester_label": "सेमेस्टर {n}",
    "grades.current_semester_label": "मौजूदा सेमेस्टर",
    "grades.no_grades": "📭 <b>ग्रेड नहीं हैं</b> ({sem_label})\n\nटीचर के डालने के बाद ग्रेड दिखेंगे।",
    "grades.header": "📊 <b>ग्रेड · {sem_label}</b>\n",
    "grades.total": "\n<i>कुल ग्रेड: {count}</i>",
    "grades.page_suffix": "\n\n({page}/{total})",

    # ── /stats ───────────────────────────────────────────────────────────────
    "stats.not_connected_short": "📚 <b>eCampus कनेक्ट नहीं है</b>\n\nसाइट के प्रोफ़ाइल सेक्शन में अकाउंट कनेक्ट करें।",
    "stats.no_data": "📭 eCampus का डेटा नहीं है। सिंक अपडेट करें।",
    "stats.no_term_data": "📭 इस सेमेस्टर का डेटा नहीं है।",
    "stats.all_time_suffix": " · सारा समय",
    "stats.term_fallback": " · सेम.{id}",
    "stats.header": "📊 <b>परफॉर्मेंस स्टैटिस्टिक्स{suffix}</b>\n",
    "stats.subjects_count": "📚 विषय:   <b>{count}</b>",
    "stats.grades_count": "✏️  ग्रेड:      <b>{count}</b>",
    "stats.exams_count": "🎓 एग्ज़ाम:  <b>{count}</b>",
    "stats.credits_count": "📝 क्रेडिट:    <b>{count}</b>",
    "stats.rating": "⭐ रेटिंग:    {icon} <b>{avg:.1f}</b> / {max:.1f} ({pct:.0f}%)",
    "stats.updated_at": "\n<i>अपडेटेड: {dt}</i>",
    "stats.choose_period": "📊 <b>परफॉर्मेंस स्टैटिस्टिक्स</b>\n\nपीरियड चुनें:",
    "stats.all_time_button": "📊 सारे समय के लिए",

    # ── /subjects ────────────────────────────────────────────────────────────
    "subjects.not_connected": "📚 <b>eCampus कनेक्ट नहीं है</b>\n\nसाइट के प्रोफ़ाइल सेक्शन में अकाउंट कनेक्ट करें।",
    "subjects.no_data": "📭 डेटा नहीं है। सिंक अपडेट करें।",
    "subjects.none_for_term": "📭 विषय नहीं मिले ({sem_label})।",
    "subjects.header": "📚 <b>विषय · {sem_label}</b>  ({count} कुल)\n",
    "subjects.no_type_data": "डेटा नहीं है",
    "subjects.rating_line": "\n    {icon} रेटिंग: <b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>एग्ज़ाम</i>",
    "subjects.credit_tag": " 📝<i>क्रेडिट</i>",

    # ── /ecampus ─────────────────────────────────────────────────────────────
    "ecampus.not_connected": (
        "📚 <b>eCampus SKFU</b>\n\n"
        "अकाउंट <b>कनेक्ट नहीं है</b>।\n\n"
        "इसे साइट या मिनी-ऐप के <b>प्रोफ़ाइल → eCampus</b> सेक्शन में "
        "कनेक्ट करें और पाएँ:\n"
        "  • विषयों और ग्रेड्स की लिस्ट\n"
        "  • परफॉर्मेंस स्टैटिस्टिक्स\n"
        "  • हर कोर्स की रेटिंग\n\n"
        "कमांड्स (कनेक्ट करने के बाद):\n"
        "  /grades   — मेरे ग्रेड\n"
        "  /stats    — परफॉर्मेंस स्टैटिस्टिक्स\n"
        "  /subjects — विषयों की लिस्ट"
    ),
    "ecampus.status_ok": "✅ सिंक हो गया",
    "ecampus.status_running": "⏳ सिंक हो रहा है...",
    "ecampus.status_error": "❌ सिंक में एरर",
    "ecampus.status_pending": "🕐 सिंक का इंतज़ार",
    "ecampus.header": "📚 <b>eCampus SKFU</b>\n",
    "ecampus.status_line": "🔗 स्टेटस: {status}",
    "ecampus.subjects_count": "📦 विषय: <b>{count}</b>",
    "ecampus.grades_count": "✏️  ग्रेड: <b>{count}</b>",
    "ecampus.updated_at": "🕐 अपडेटेड: <b>{dt}</b>",
    "ecampus.current_term": "\n📅 मौजूदा सेमेस्टर: <b>{term}</b>",
    "ecampus.term_subjects": "   विषय: <b>{count}</b>",
    "ecampus.term_grades": "   ग्रेड: <b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>कमांड्स:</b>\n"
        "  /grades   — मौजूदा सेमेस्टर के ग्रेड\n"
        "  /grades 2 — सेमेस्टर 2 के ग्रेड\n"
        "  /stats    — पूरा स्टैटिस्टिक्स\n"
        "  /subjects — विषयों की लिस्ट"
    ),

    # ── ИИ-обработчик (ошибки/заглушки) ─────────────────────────────────────
    "ai.empty_message": "कुछ लिखें 🙂",
    "ai.processing": "⏳ प्रोसेस हो रहा है...",
    "ai.unknown_request": "❓ अनजान रिक्वेस्ट।",
    "ai.parse_failed": "❌ रिक्वेस्ट समझ नहीं पाया। दूसरे तरीके से लिखें।",
    "ai.execution_error": "❌ रिक्वेस्ट चलाने में एरर।\n<code>{eid}</code>",
    "ai.processing_error": "❌ रिक्वेस्ट प्रोसेस करने में एरर।",

    # ── /language (новая команда) ───────────────────────────────────────────
    "language.prompt": "🌐 <b>इंटरफ़ेस की भाषा चुनें</b>\n\nयह चुनाव साइट और मिनी-ऐप के साथ सिंक होता है।",
    "language.saved": "✅ भाषा बदलकर <b>{name}</b> हो गई।",
    "language.save_failed": "⚠️ भाषा सेव नहीं हो पाई। फिर से कोशिश करें।",

    # ── Меню команд бота (BotCommand description) ───────────────────────────
    "cmd.start": "शुरू करें",
    "cmd.me": "पर्सनल कैबिनेट 👤",
    "cmd.help": "मदद",
    "cmd.miniapp": "शेड्यूल खोलें (Mini App) 📅",
    "cmd.grades": "eCampus से मेरे ग्रेड",
    "cmd.stats": "परफॉर्मेंस स्टैटिस्टिक्स 📊",
    "cmd.subjects": "विषयों की लिस्ट",
    "cmd.classmates": "मेरे क्लासमेट्स 👥",
    "cmd.teacher": "टीचर ढूँढें 👤",
    "cmd.ecampus": "eCampus स्टेटस",
    "cmd.limit": "रिक्वेस्ट लिमिट",
    "cmd.language": "इंटरफ़ेस की भाषा 🌐",
    "cmd.login": "साइट में लॉगिन",
    "cmd.code": "कोड डालें (/code XXXXXX)",
    "cmd.support": "सपोर्ट",
    "cmd.suggest": "आइडिया सुझाएँ",
    "cmd.about": "बॉट के बारे में",
}
