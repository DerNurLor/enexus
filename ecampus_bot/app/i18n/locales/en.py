"""English."""

MESSAGES: dict[str, str] = {
    "start.greeting": (
        "👋 Hi! I'm the NCFU schedule bot.\n\n"
        "Ask me in plain language:\n"
        "  • <i>Schedule for ISS-b-o-22-3 this week</i>\n"
        "  • <i>Where is Podzolko's class in 5 minutes?</i>\n"
        "  • <i>Free rooms in building 11</i>\n"
        "  • <i>What's group AIS-b-o-25-1 doing right now?</i>\n\n"
        "📋 <b>Commands:</b>\n"
        "  /me         — personal dashboard 👤\n"
        "  /miniapp    — schedule in the app 📅\n"
        "  /grades     — my eCampus grades\n"
        "  /stats      — statistics 📊\n"
        "  /classmates — classmates 👥\n"
        "  /teacher    — find a teacher\n"
        "  /help       — full help"
    ),
    "start.login_welcome": "👋 Hi, {name}!\n\n🔐 <b>New login method</b>\n\n1. Open <a href=\"{web_url}/profile\">{web_url}/profile</a>\n2. Tap <b>«Sign in with Telegram»</b>\n3. Send me the <b>6-digit code</b> shown\n4. Confirm — the page will refresh automatically ✨",

    "help.full": (
        "📖 <b>NCFU schedule bot help</b>\n\n"
        "Just ask in plain language:\n\n"
        "📅 <b>Schedule:</b>\n"
        "  <i>Schedule for ISS-b-o-22-3</i>\n"
        "  <i>What does group AIS25 have tomorrow?</i>\n\n"
        "👤 <b>Teacher:</b>\n"
        "  <i>Where is Podzolko right now?</i>  ·  <i>Ivanov's schedule</i>\n\n"
        "🚪 <b>Rooms:</b>\n"
        "  <i>Free rooms right now</i>\n\n"
        "📋 <b>Commands:</b>\n"
        "  /me          — personal dashboard 👤\n"
        "  /miniapp     — schedule in the app 📅\n"
        "  /grades      — my eCampus grades\n"
        "  /stats       — academic statistics 📊\n"
        "  /subjects    — list of subjects\n"
        "  /classmates  — my classmates 👥\n"
        "  /teacher     — find a teacher\n"
        "  /ecampus     — eCampus status\n"
        "  /limit       — request limit\n"
        "  /language    — interface language 🌐\n"
        "  /support     — support\n"
        "  /suggest     — suggest an idea\n\n"
        "💡 <i>In groups, mention me: @botname your request</i>"
    ),
    "help.quick": (
        "📖 <b>Quick help</b>\n\n"
        "/me       — this screen\n"
        "/grades   — eCampus grades\n"
        "/stats    — statistics (choose semester)\n"
        "/subjects — list of subjects\n"
        "/teacher  — find a teacher\n"
        "/classmates — classmates\n"
        "/limit    — request limit\n"
        "/miniapp  — open the app\n"
        "/help     — full help"
    ),

    "group_welcome.text": (
        "👋 Hi! Glad to join <b>{chat_title}</b>!\n\n"
        "📌 <b>What I can do:</b>\n"
        "  • Schedule for a group, teacher, or room\n"
        "  • Free rooms right now\n"
        "  • Search teachers and groups\n\n"
        "💬 <b>How to talk to me:</b>\n"
        "  Mention me: <code>@{bot_username} schedule ISS-b-o-22-3</code>\n"
        "  Or use commands:\n"
        "  /help — everything I can do\n"
        "  /miniapp — schedule in the app 📅\n\n"
        "🔕 <i>I don't watch the whole chat — I only reply to mentions and commands.</i>"
    ),
    "group_welcome.default_title": "this group",
    "common.open_schedule_button": "📅 Open schedule",

    "mykey.disabled": "/mykey is disabled.",

    "roles.role.admin": "Admin",
    "roles.role.moderator": "Moderator",
    "roles.role.vip": "VIP",
    "roles.role.beta": "Beta tester",
    "roles.role.user": "User",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>Roles:</b>",
    "roles.privileges_label": "\n🔓 <b>Privileges:</b>",
    "roles.priv_admin_panel": "⚙️ <b>Admin panel</b> → <a href=\"{url}\">open</a>",
    "roles.priv_beta": "🧪 <b>Beta access</b> — extended schedule filters",
    "roles.priv_floorplan_edit": "🗺 <b>Editing</b> floor plans",
    "roles.priv_floorplan_view": "🗺 <b>Viewing</b> floor plans",
    "roles.priv_personal_limit": "📊 <b>Personal limit</b>: {limit} requests / period",
    "roles.profile_link": "\n💼 <b>Personal dashboard:</b> <a href=\"{url}\">open</a>",

    "suggest.prompt": (
        "💡 <b>Suggestions and ideas</b>\n\n"
        "Got an idea to improve the bot or schedule?\n"
        "Write it after the command:\n\n"
        "<code>/suggest Your idea here</code>\n\n"
        "<i>Example: /suggest Add a reminder 10 minutes before class</i>"
    ),
    "suggest.accepted": "✅ <b>Suggestion received!</b>\n\nThanks, your idea will help make the bot better.\nNumber: <code>{ticket_id}</code>\n",

    "about.text": (
        "🎓 <b>NCFU schedule bot</b>\n\n"
        "A smart assistant for students and faculty "
        "of North Caucasus Federal University.\n\n"
        "📌 <b>Features:</b>\n"
        "  • Schedule for groups, teachers, rooms\n"
        "  • Free rooms in real time\n"
        "  • Search groups and teachers\n"
        "  • Mini App with the full schedule 📅\n\n"
        "🔗 <b>Links:</b>\n"
        "  • <a href=\"{miniapp_url}\">Schedule Mini App</a>\n"
        "🛠 <b>Version:</b> 2.0\n"
        "💬 Questions and suggestions: /support · /suggest"
    ),

    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — the full schedule in an app\n\n"
        "• Flexible search by group, teacher, room\n"
        "• Free rooms in real time\n"
        "• Building floor plans\n"
        "• Favorites and personal settings\n\n"
        "Tap the button below 👇"
    ),

    "support.prompt": "📬 <b>Support</b>\n\nWrite your question after the command:\n<code>/support Your question here</code>",
    "support.accepted": "✅ <b>Request received</b>\n\nWe'll get back to you as soon as possible.\nTicket number: <code>{ticket_id}</code>",

    "limit.header": "📊 <b>{scope} limit</b>",
    "limit.scope_private": "personal request",
    "limit.scope_chat": "request in this chat",
    "limit.used": "✅ Used: <b>{used}</b>",
    "limit.remaining": "💬 Remaining: <b>{remaining}</b>",
    "limit.max": "🏁 Maximum: <b>{cap}</b>",
    "limit.reset_in": "🔄 Resets in: <b>{reset_str}</b>",
    "limit.reset_done": "🔄 Limit already reset — you can use it again",
    "limit.exhausted_note": "<i>Limit reached. Wait for reset or contact an admin.</i>",
    "limit.normal_note": "<i>This limit counts AI requests (schedule, search). /start, /help and other commands don't count.</i>",

    "login.instructions": (
        "🔐 <b>Sign in to the website</b>\n\n"
        "1. Open <a href=\"{web_url}/profile\">{web_url}/profile</a>\n"
        "2. Tap <b>«Sign in with Telegram»</b>\n"
        "3. You'll see a <b>6-letter code</b> (uppercase Latin)\n"
        "4. Send it with <code>/code XXXXXX</code>\n"
        "5. Confirm — the page will refresh automatically\n\n"
        "💡 Or just type <code>/code</code> and the code, separated by a space."
    ),
    "login.code_missing": "❓ Provide the code after the command:\n<code>/code XXXXXX</code>\n\nThe code is shown on the site when you tap «Sign in with Telegram».",
    "login.code_invalid_format": "❌ The code must be <b>6 uppercase letters and digits</b>.\nExample: <code>/code ABCDEF</code>",
    "login.account_blocked": "❌ Your account is blocked.",
    "login.server_error": "⚠️ Server error. Try again later.",
    "login.code_error": "❌ <b>{error}</b>\n\nCheck the code on the site and try again.\nThe code is valid for <b>3 minutes</b>.",
    "login.code_error_default": "Invalid or expired code",
    "login.code_error_server": "Server error",
    "login.confirm_prompt": "🔐 <b>Confirm sign-in</b>\n\nHi, {name}! Someone is signing in to the site with your account.\n\nConfirm sign-in?",
    "login.confirm_button": "✅ Confirm sign-in",
    "login.cancel_button": "❌ Cancel",
    "login.cancelled": "❌ <b>Sign-in cancelled.</b>\n\nIf this wasn't you, no worries — the link is already invalid.",
    "login.cancelled_toast": "Sign-in cancelled",
    "login.confirm_error": "⚠️ <b>Confirmation error.</b>\n\nThe session may have expired. Try signing in again.",
    "login.confirm_error_toast": "Error, try again",
    "login.confirmed": "✅ <b>Sign-in confirmed!</b>\n\nThe site will refresh automatically.",
    "login.confirmed_toast": "Signed in ✅",
    "login.default_name": "user",

    "disambig.stale_data": "⏱ Data is outdated. Please try again.",
    "disambig.stale_button": "⚠️ Outdated button. Please try again.",
    "disambig.expired": "⏱ Selection time expired. Please try again.",
    "disambig.loading": "⏳ Loading schedule…",
    "disambig.unknown_intent": "❓ Unknown request type.",
    "disambig.error": "❌ Error loading schedule.\n<code>{eid}</code>",
    "disambig.format_error": "❌ Error processing schedule.",
    "disambig.day_of": "Day {idx} of {total}",
    "disambig.prev_page": "◀ Prev",
    "disambig.next_page": "Next ▶",
    "disambig.group_label": "group #{id}",
    "disambig.room_label": "room #{id}",
    "disambig.schedule_title": "Schedule · {title}",

    "feedback.error_toast": "⚠️ Error",
    "feedback.already_rated_toast": "Already rated ✓",
    "feedback.save_failed_toast": "⚠️ Failed to save rating",
    "feedback.thanks_toast": "{icon} Rating saved, thanks!",

    "classmates.profile_not_found": "👤 Couldn't find your profile.",
    "classmates.no_group": "👥 <b>Group not set</b>\n\nSet up your profile on the site to see classmates.",
    "classmates.query_error": "❌ Error fetching the classmates list.",
    "classmates.header": "👥 <b>Classmates · {group_label}</b>\n",
    "classmates.registered_count": "<i>Registered: {count}</i>\n",
    "classmates.none_registered": "👥 <b>Classmates · {group_label}</b>\n\nNo one from your group has registered with the bot yet.",
    "classmates.group_fallback_label": "group #{id}",
    "classmates.more_suffix": "\n<i>…and more</i>",

    "teacher.search_prompt": "👤 <b>Find a teacher</b>\n\nType a last name (or part of it):\n<code>/teacher Ivanov</code>",
    "teacher.search_error": "❌ Search error.",
    "teacher.not_found": "🔍 Nothing found for <b>{query}</b>.\n\nTry a different last name.",
    "teacher.found_count": "🔍 Found teachers: <b>{count}</b>\n\nChoose one:",
    "teacher.not_found_short": "❌ Teacher not found.",
    "teacher.subjects_label": "\n📚 <b>Subjects:</b>",
    "teacher.more_subjects": "  <i>…and {count} more</i>",
    "teacher.lesson_types_label": "\n🗂 <b>Lesson types:</b> {types}",
    "teacher.groups_label": "\n👥 <b>Groups ({count}):</b> {names}",
    "teacher.more_groups": "  <i>…and {count} more</i>",
    "teacher.lessons_in_db": "\n📊 Lessons in database: <b>{count}</b>",
    "teacher.schedule_loaded": "🕐 Schedule: <b>loaded</b>",
    "teacher.alltime_stats_label": "\n📈 <b>All-time statistics:</b>",
    "teacher.total_lessons": "  Total classes: <b>{count}</b>",
    "teacher.types_label": "  Types: {types}",
    "teacher.buildings_label": "  Buildings: {buildings}",
    "teacher.rooms_label": "  Rooms: {rooms}",
    "teacher.schedule_button": "📅 Schedule",

    "me.profile_not_found": "👤 Profile not found.",
    "me.header": "👤 <b>Personal dashboard</b>\n",
    "me.role_student": "Student",
    "me.role_teacher": "Teacher",
    "me.role_unset": "Not set up",
    "me.group_line": "\n📌 Group: <b>{group_name}</b>",
    "me.teacher_line": "\n📌 Teacher: <b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 Request limit: <code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 My schedule",
    "me.miniapp_button": "📱 Schedule (app)",
    "me.subjects_button": "📚 Subjects",
    "me.stats_button": "📊 Statistics",
    "me.classmates_button": "👥 Classmates",
    "me.my_lessons_button": "📈 My classes",
    "me.profile_button": "⚙️ Profile",
    "me.map_button": "🗺 Map",
    "me.limit_button": "💬 Request limit",
    "me.help_button": "❓ Help",
    "me.no_ecampus_data": "📭 No eCampus data.",
    "me.stats_choose_period": "📊 <b>Academic statistics</b>\n\nChoose a period:",

    "grades.not_connected": "📚 <b>eCampus not connected</b>\n\nConnect your eCampus account in <b>Profile → eCampus</b> on the site or in the mini app.",
    "grades.sync_running": "⏳ Sync with eCampus is still running — data is updating.\nTry again in a minute.",
    "grades.empty": "📭 eCampus data is still empty.\nTap «Refresh» in the mini app or wait for auto-sync.",
    "grades.semester_label": "Semester {n}",
    "grades.current_semester_label": "Current semester",
    "grades.no_grades": "📭 <b>No grades</b> ({sem_label})\n\nGrades will appear once the teacher enters them.",
    "grades.header": "📊 <b>Grades · {sem_label}</b>\n",
    "grades.total": "\n<i>Total grades: {count}</i>",
    "grades.page_suffix": "\n\n({page}/{total})",

    "stats.not_connected_short": "📚 <b>eCampus not connected</b>\n\nConnect your account in Profile on the site.",
    "stats.no_data": "📭 No eCampus data. Refresh sync.",
    "stats.no_term_data": "📭 No data for this semester.",
    "stats.all_time_suffix": " · All time",
    "stats.term_fallback": " · sem.{id}",
    "stats.header": "📊 <b>Academic statistics{suffix}</b>\n",
    "stats.subjects_count": "📚 Subjects:   <b>{count}</b>",
    "stats.grades_count": "✏️  Grades:     <b>{count}</b>",
    "stats.exams_count": "🎓 Exams:     <b>{count}</b>",
    "stats.credits_count": "📝 Pass/fail:  <b>{count}</b>",
    "stats.rating": "⭐ Rating:     {icon} <b>{avg:.1f}</b> / {max:.1f} ({pct:.0f}%)",
    "stats.updated_at": "\n<i>Updated: {dt}</i>",
    "stats.choose_period": "📊 <b>Academic statistics</b>\n\nChoose a period:",
    "stats.all_time_button": "📊 All time",

    "subjects.not_connected": "📚 <b>eCampus not connected</b>\n\nConnect your account in Profile on the site.",
    "subjects.no_data": "📭 No data. Refresh sync.",
    "subjects.none_for_term": "📭 No subjects found ({sem_label}).",
    "subjects.header": "📚 <b>Subjects · {sem_label}</b>  ({count})\n",
    "subjects.no_type_data": "no data",
    "subjects.rating_line": "\n    {icon} Rating: <b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>Exam</i>",
    "subjects.credit_tag": " 📝<i>Pass/fail</i>",

    "ecampus.not_connected": (
        "📚 <b>NCFU eCampus</b>\n\n"
        "Account <b>not connected</b>.\n\n"
        "Connect it in <b>Profile → eCampus</b> on the site "
        "or in the mini app to get:\n"
        "  • A list of subjects and grades\n"
        "  • Academic statistics\n"
        "  • Ratings for each course\n\n"
        "Commands (after connecting):\n"
        "  /grades   — my grades\n"
        "  /stats    — academic statistics\n"
        "  /subjects — list of subjects"
    ),
    "ecampus.status_ok": "✅ Synced",
    "ecampus.status_running": "⏳ Syncing...",
    "ecampus.status_error": "❌ Sync error",
    "ecampus.status_pending": "🕐 Waiting for sync",
    "ecampus.header": "📚 <b>NCFU eCampus</b>\n",
    "ecampus.status_line": "🔗 Status: {status}",
    "ecampus.subjects_count": "📦 Subjects: <b>{count}</b>",
    "ecampus.grades_count": "✏️  Grades: <b>{count}</b>",
    "ecampus.updated_at": "🕐 Updated: <b>{dt}</b>",
    "ecampus.current_term": "\n📅 Current semester: <b>{term}</b>",
    "ecampus.term_subjects": "   Subjects: <b>{count}</b>",
    "ecampus.term_grades": "   Grades: <b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>Commands:</b>\n"
        "  /grades   — my grades for the current semester\n"
        "  /grades 2 — grades for semester 2\n"
        "  /stats    — full statistics\n"
        "  /subjects — list of subjects"
    ),

    "ai.empty_message": "Write something 🙂",
    "ai.processing": "⏳ Processing...",
    "ai.unknown_request": "❓ Unknown request.",
    "ai.parse_failed": "❌ Couldn't understand the request. Try rephrasing it.",
    "ai.execution_error": "❌ Error while running the request.\n<code>{eid}</code>",
    "ai.processing_error": "❌ Error processing the request.",

    "language.prompt": "🌐 <b>Choose interface language</b>\n\nThis choice syncs with the website and mini app.",
    "language.saved": "✅ Language changed to <b>{name}</b>.",
    "language.save_failed": "⚠️ Failed to save language. Try again.",

    "cmd.start": "Get started",
    "cmd.me": "Personal dashboard 👤",
    "cmd.help": "Help",
    "cmd.miniapp": "Open schedule (Mini App) 📅",
    "cmd.grades": "My eCampus grades",
    "cmd.stats": "Academic statistics 📊",
    "cmd.subjects": "List of subjects",
    "cmd.classmates": "My classmates 👥",
    "cmd.teacher": "Find a teacher 👤",
    "cmd.ecampus": "eCampus status",
    "cmd.limit": "Request limit",
    "cmd.language": "Interface language 🌐",
    "cmd.login": "Sign in to the website",
    "cmd.code": "Enter code (/code XXXXXX)",
    "cmd.support": "Support",
    "cmd.suggest": "Suggest an idea",
    "cmd.about": "About the bot",
}
