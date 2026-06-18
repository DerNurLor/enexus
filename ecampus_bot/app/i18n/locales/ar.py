"""العربية."""

MESSAGES: dict[str, str] = {
    "start.greeting": (
        "👋 مرحبًا! أنا روبوت الجدول الدراسي لجامعة شمال القوقاز الفيدرالية.\n\n"
        "اسألني بلغة طبيعية:\n"
        "  • <i>جدول ISS-b-o-22-3 لهذا الأسبوع</i>\n"
        "  • <i>أين حصة بودزولكو بعد 5 دقائق؟</i>\n"
        "  • <i>القاعات الفاضية في المبنى 11</i>\n"
        "  • <i>ماذا تفعل فرقة AIS-b-o-25-1 الآن؟</i>\n\n"
        "📋 <b>الأوامر:</b>\n"
        "  /me         — لوحة التحكم الشخصية 👤\n"
        "  /miniapp    — الجدول في التطبيق 📅\n"
        "  /grades     — درجاتي من eCampus\n"
        "  /stats      — الإحصائيات 📊\n"
        "  /classmates — زملاء الدراسة 👥\n"
        "  /teacher    — البحث عن أستاذ\n"
        "  /help       — المساعدة الكاملة"
    ),
    "start.login_welcome": "👋 مرحبًا {name}!\n\n🔐 <b>طريقة تسجيل دخول جديدة</b>\n\n1. افتح <a href=\"{web_url}/profile\">{web_url}/profile</a>\n2. اضغط على <b>«تسجيل الدخول عبر Telegram»</b>\n3. أرسل لي <b>الرمز المكوّن من 6 أرقام</b> الظاهر\n4. أكّد — ستتحدث الصفحة تلقائيًا ✨",

    "help.full": (
        "📖 <b>مساعدة روبوت الجدول الدراسي</b>\n\n"
        "اسأل ببساطة بلغة طبيعية:\n\n"
        "📅 <b>الجدول:</b>\n"
        "  <i>جدول ISS-b-o-22-3</i>\n"
        "  <i>ماذا لدى فرقة AIS25 غدًا؟</i>\n\n"
        "👤 <b>الأستاذ:</b>\n"
        "  <i>أين بودزولكو الآن؟</i>  ·  <i>جدول إيفانوف</i>\n\n"
        "🚪 <b>القاعات:</b>\n"
        "  <i>القاعات الفاضية الآن</i>\n\n"
        "📋 <b>الأوامر:</b>\n"
        "  /me          — لوحة التحكم الشخصية 👤\n"
        "  /miniapp     — الجدول في التطبيق 📅\n"
        "  /grades      — درجاتي من eCampus\n"
        "  /stats       — الإحصائيات الدراسية 📊\n"
        "  /subjects    — قائمة المواد\n"
        "  /classmates  — زملاء الدراسة 👥\n"
        "  /teacher     — البحث عن أستاذ\n"
        "  /ecampus     — حالة eCampus\n"
        "  /limit       — حد الطلبات\n"
        "  /language    — لغة الواجهة 🌐\n"
        "  /support     — الدعم\n"
        "  /suggest     — اقترح فكرة\n\n"
        "💡 <i>في المجموعات، اذكرني: @botname طلبك</i>"
    ),
    "help.quick": (
        "📖 <b>مساعدة سريعة</b>\n\n"
        "/me       — هذه الشاشة\n"
        "/grades   — درجات eCampus\n"
        "/stats    — الإحصائيات (اختيار الفصل)\n"
        "/subjects — قائمة المواد\n"
        "/teacher  — البحث عن أستاذ\n"
        "/classmates — زملاء الدراسة\n"
        "/limit    — حد الطلبات\n"
        "/miniapp  — فتح التطبيق\n"
        "/help     — المساعدة الكاملة"
    ),

    "group_welcome.text": (
        "👋 مرحبًا! سعيد بالانضمام إلى <b>{chat_title}</b>!\n\n"
        "📌 <b>ما يمكنني فعله:</b>\n"
        "  • جدول الفرقة أو الأستاذ أو القاعة\n"
        "  • القاعات الفاضية الآن\n"
        "  • البحث عن الأساتذة والفرق\n\n"
        "💬 <b>كيف تتحدث معي:</b>\n"
        "  اذكرني: <code>@{bot_username} جدول ISS-b-o-22-3</code>\n"
        "  أو استخدم الأوامر:\n"
        "  /help — كل ما يمكنني فعله\n"
        "  /miniapp — الجدول في التطبيق 📅\n\n"
        "🔕 <i>لا أتابع الدردشة كاملة — أرد فقط على الإشارات والأوامر.</i>"
    ),
    "group_welcome.default_title": "هذه المجموعة",
    "common.open_schedule_button": "📅 فتح الجدول",

    "mykey.disabled": "الأمر /mykey معطّل.",

    "roles.role.admin": "مسؤول",
    "roles.role.moderator": "مشرف",
    "roles.role.vip": "VIP",
    "roles.role.beta": "مختبر تجريبي",
    "roles.role.user": "مستخدم",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>الأدوار:</b>",
    "roles.privileges_label": "\n🔓 <b>الصلاحيات:</b>",
    "roles.priv_admin_panel": "⚙️ <b>لوحة الإدارة</b> ← <a href=\"{url}\">فتح</a>",
    "roles.priv_beta": "🧪 <b>وصول تجريبي</b> — مرشحات جدول موسعة",
    "roles.priv_floorplan_edit": "🗺 <b>تعديل</b> مخططات الطوابق",
    "roles.priv_floorplan_view": "🗺 <b>عرض</b> مخططات الطوابق",
    "roles.priv_personal_limit": "📊 <b>حد شخصي</b>: {limit} طلب / فترة",
    "roles.profile_link": "\n💼 <b>لوحة التحكم الشخصية:</b> <a href=\"{url}\">فتح</a>",

    "suggest.prompt": (
        "💡 <b>الاقتراحات والأفكار</b>\n\n"
        "هل لديك فكرة لتحسين الروبوت أو الجدول؟\n"
        "اكتبها بعد الأمر:\n\n"
        "<code>/suggest فكرتك هنا</code>\n\n"
        "<i>مثال: /suggest إضافة تنبيه قبل 10 دقائق من الحصة</i>"
    ),
    "suggest.accepted": "✅ <b>تم استلام الاقتراح!</b>\n\nشكرًا، فكرتك ستساعد في تحسين الروبوت.\nرقم: <code>{ticket_id}</code>\n",

    "about.text": (
        "🎓 <b>روبوت الجدول الدراسي لجامعة شمال القوقاز الفيدرالية</b>\n\n"
        "مساعد ذكي لطلاب وأساتذة الجامعة.\n\n"
        "📌 <b>الميزات:</b>\n"
        "  • جدول الفرق والأساتذة والقاعات\n"
        "  • القاعات الفاضية في الوقت الحقيقي\n"
        "  • البحث عن الفرق والأساتذة\n"
        "  • تطبيق مصغر بالجدول الكامل 📅\n\n"
        "🔗 <b>روابط:</b>\n"
        "  • <a href=\"{miniapp_url}\">التطبيق المصغر للجدول</a>\n"
        "🛠 <b>الإصدار:</b> 2.0\n"
        "💬 الأسئلة والاقتراحات: /support · /suggest"
    ),

    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — الجدول الكامل في تطبيق\n\n"
        "• بحث مرن بالفرقة أو الأستاذ أو القاعة\n"
        "• القاعات الفاضية في الوقت الحقيقي\n"
        "• مخططات طوابق المباني\n"
        "• المفضلة والإعدادات الشخصية\n\n"
        "اضغط الزر أدناه 👇"
    ),

    "support.prompt": "📬 <b>الدعم</b>\n\nاكتب سؤالك بعد الأمر:\n<code>/support سؤالك هنا</code>",
    "support.accepted": "✅ <b>تم استلام الطلب</b>\n\nسنرد عليك في أقرب وقت ممكن.\nرقم التذكرة: <code>{ticket_id}</code>",

    "limit.header": "📊 <b>حد {scope}</b>",
    "limit.scope_private": "الطلبات الشخصية",
    "limit.scope_chat": "الطلبات في هذه المحادثة",
    "limit.used": "✅ المستخدم: <b>{used}</b>",
    "limit.remaining": "💬 المتبقي: <b>{remaining}</b>",
    "limit.max": "🏁 الحد الأقصى: <b>{cap}</b>",
    "limit.reset_in": "🔄 إعادة الضبط بعد: <b>{reset_str}</b>",
    "limit.reset_done": "🔄 تمت إعادة ضبط الحد — يمكنك الاستخدام مجددًا",
    "limit.exhausted_note": "<i>تم استهلاك الحد. انتظر إعادة الضبط أو تواصل مع المسؤول.</i>",
    "limit.normal_note": "<i>هذا الحد يحسب طلبات الذكاء الاصطناعي (الجدول، البحث) فقط. أوامر /start و /help لا تُحسب.</i>",

    "login.instructions": (
        "🔐 <b>تسجيل الدخول إلى الموقع</b>\n\n"
        "1. افتح <a href=\"{web_url}/profile\">{web_url}/profile</a>\n"
        "2. اضغط على <b>«تسجيل الدخول عبر Telegram»</b>\n"
        "3. سيظهر لك <b>رمز من 6 أحرف</b> (لاتينية كبيرة)\n"
        "4. أرسله بالأمر <code>/code XXXXXX</code>\n"
        "5. أكّد — ستتحدث الصفحة تلقائيًا\n\n"
        "💡 أو فقط اكتب <code>/code</code> ثم الرمز، مفصولين بمسافة."
    ),
    "login.code_missing": "❓ أدخل الرمز بعد الأمر:\n<code>/code XXXXXX</code>\n\nيظهر الرمز في الموقع عند الضغط على «تسجيل الدخول عبر Telegram».",
    "login.code_invalid_format": "❌ يجب أن يكون الرمز <b>6 أحرف كبيرة وأرقام</b>.\nمثال: <code>/code ABCDEF</code>",
    "login.account_blocked": "❌ حسابك محظور.",
    "login.server_error": "⚠️ خطأ في الخادم. حاول مرة أخرى لاحقًا.",
    "login.code_error": "❌ <b>{error}</b>\n\nتحقق من الرمز في الموقع وحاول مرة أخرى.\nالرمز صالح لمدة <b>3 دقائق</b>.",
    "login.code_error_default": "رمز غير صحيح أو منتهي الصلاحية",
    "login.code_error_server": "خطأ في الخادم",
    "login.confirm_prompt": "🔐 <b>تأكيد تسجيل الدخول</b>\n\nمرحبًا {name}! شخص ما يسجل الدخول إلى الموقع بحسابك.\n\nهل تؤكد تسجيل الدخول؟",
    "login.confirm_button": "✅ تأكيد تسجيل الدخول",
    "login.cancel_button": "❌ إلغاء",
    "login.cancelled": "❌ <b>تم إلغاء تسجيل الدخول.</b>\n\nإذا لم تكن أنت — لا بأس، الرابط أصبح غير صالح.",
    "login.cancelled_toast": "تم إلغاء تسجيل الدخول",
    "login.confirm_error": "⚠️ <b>خطأ في التأكيد.</b>\n\nقد تكون الجلسة منتهية. حاول تسجيل الدخول مرة أخرى.",
    "login.confirm_error_toast": "خطأ، حاول مرة أخرى",
    "login.confirmed": "✅ <b>تم تأكيد تسجيل الدخول!</b>\n\nستتحدث صفحة الموقع تلقائيًا.",
    "login.confirmed_toast": "تم تسجيل الدخول ✅",
    "login.default_name": "مستخدم",

    "disambig.stale_data": "⏱ البيانات قديمة. أعد الطلب من فضلك.",
    "disambig.stale_button": "⚠️ زر قديم. أعد الطلب من فضلك.",
    "disambig.expired": "⏱ انتهى وقت الاختيار. أعد الطلب من فضلك.",
    "disambig.loading": "⏳ جاري تحميل الجدول…",
    "disambig.unknown_intent": "❓ نوع طلب غير معروف.",
    "disambig.error": "❌ خطأ في تحميل الجدول.\n<code>{eid}</code>",
    "disambig.format_error": "❌ خطأ في معالجة الجدول.",
    "disambig.day_of": "اليوم {idx} من {total}",
    "disambig.prev_page": "◀ السابق",
    "disambig.next_page": "التالي ▶",
    "disambig.group_label": "فرقة #{id}",
    "disambig.room_label": "قاعة #{id}",
    "disambig.schedule_title": "الجدول · {title}",

    "feedback.error_toast": "⚠️ خطأ",
    "feedback.already_rated_toast": "تم التقييم مسبقًا ✓",
    "feedback.save_failed_toast": "⚠️ تعذر حفظ التقييم",
    "feedback.thanks_toast": "{icon} تم حفظ التقييم، شكرًا!",

    "classmates.profile_not_found": "👤 لم يتم العثور على ملفك الشخصي.",
    "classmates.no_group": "👥 <b>الفرقة غير مُعدّة</b>\n\nقم بإعداد ملفك الشخصي في الموقع لرؤية زملاء الدراسة.",
    "classmates.query_error": "❌ خطأ في الحصول على قائمة زملاء الدراسة.",
    "classmates.header": "👥 <b>زملاء الدراسة · {group_label}</b>\n",
    "classmates.registered_count": "<i>المسجلون: {count}</i>\n",
    "classmates.none_registered": "👥 <b>زملاء الدراسة · {group_label}</b>\n\nلم يسجّل أحد من فرقتك في الروبوت بعد.",
    "classmates.group_fallback_label": "فرقة #{id}",
    "classmates.more_suffix": "\n<i>…والمزيد</i>",

    "teacher.search_prompt": "👤 <b>البحث عن أستاذ</b>\n\nاكتب اللقب (أو جزءًا منه):\n<code>/teacher Ivanov</code>",
    "teacher.search_error": "❌ خطأ في البحث.",
    "teacher.not_found": "🔍 لم يتم العثور على نتائج لـ <b>{query}</b>.\n\nجرّب لقبًا آخر.",
    "teacher.found_count": "🔍 تم العثور على <b>{count}</b> أستاذًا\n\nاختر:",
    "teacher.not_found_short": "❌ لم يتم العثور على الأستاذ.",
    "teacher.subjects_label": "\n📚 <b>المواد:</b>",
    "teacher.more_subjects": "  <i>…و{count} أخرى</i>",
    "teacher.lesson_types_label": "\n🗂 <b>أنواع الحصص:</b> {types}",
    "teacher.groups_label": "\n👥 <b>الفرق ({count}):</b> {names}",
    "teacher.more_groups": "  <i>…و{count} أخرى</i>",
    "teacher.lessons_in_db": "\n📊 الحصص في قاعدة البيانات: <b>{count}</b>",
    "teacher.schedule_loaded": "🕐 الجدول: <b>محمّل</b>",
    "teacher.alltime_stats_label": "\n📈 <b>إحصائيات كل الوقت:</b>",
    "teacher.total_lessons": "  إجمالي الحصص: <b>{count}</b>",
    "teacher.types_label": "  الأنواع: {types}",
    "teacher.buildings_label": "  المباني: {buildings}",
    "teacher.rooms_label": "  القاعات: {rooms}",
    "teacher.schedule_button": "📅 الجدول",

    "me.profile_not_found": "👤 لم يتم العثور على الملف الشخصي.",
    "me.header": "👤 <b>لوحة التحكم الشخصية</b>\n",
    "me.role_student": "طالب",
    "me.role_teacher": "أستاذ",
    "me.role_unset": "غير مُعدّ",
    "me.group_line": "\n📌 الفرقة: <b>{group_name}</b>",
    "me.teacher_line": "\n📌 الأستاذ: <b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 حد الطلبات: <code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 جدولي",
    "me.miniapp_button": "📱 الجدول (تطبيق)",
    "me.subjects_button": "📚 المواد",
    "me.stats_button": "📊 الإحصائيات",
    "me.classmates_button": "👥 زملاء الدراسة",
    "me.my_lessons_button": "📈 حصصي",
    "me.profile_button": "⚙️ الملف الشخصي",
    "me.map_button": "🗺 الخريطة",
    "me.limit_button": "💬 حد الطلبات",
    "me.help_button": "❓ المساعدة",
    "me.no_ecampus_data": "📭 لا توجد بيانات eCampus.",
    "me.stats_choose_period": "📊 <b>الإحصائيات الدراسية</b>\n\nاختر الفترة:",

    "grades.not_connected": "📚 <b>eCampus غير متصل</b>\n\nقم بربط حساب eCampus في <b>الملف الشخصي ← eCampus</b> على الموقع أو في التطبيق المصغر.",
    "grades.sync_running": "⏳ المزامنة مع eCampus لا تزال جارية — البيانات يتم تحديثها.\nحاول مرة أخرى بعد دقيقة.",
    "grades.empty": "📭 بيانات eCampus لا تزال فاضية.\nاضغط «تحديث» في التطبيق المصغر أو انتظر المزامنة التلقائية.",
    "grades.semester_label": "الفصل {n}",
    "grades.current_semester_label": "الفصل الحالي",
    "grades.no_grades": "📭 <b>لا توجد درجات</b> ({sem_label})\n\nستظهر الدرجات بعد أن يضعها الأستاذ.",
    "grades.header": "📊 <b>الدرجات · {sem_label}</b>\n",
    "grades.total": "\n<i>إجمالي الدرجات: {count}</i>",
    "grades.page_suffix": "\n\n({page}/{total})",

    "stats.not_connected_short": "📚 <b>eCampus غير متصل</b>\n\nقم بربط حسابك في الملف الشخصي على الموقع.",
    "stats.no_data": "📭 لا توجد بيانات eCampus. حدّث المزامنة.",
    "stats.no_term_data": "📭 لا توجد بيانات لهذا الفصل.",
    "stats.all_time_suffix": " · كل الوقت",
    "stats.term_fallback": " · فصل {id}",
    "stats.header": "📊 <b>الإحصائيات الدراسية{suffix}</b>\n",
    "stats.subjects_count": "📚 المواد:   <b>{count}</b>",
    "stats.grades_count": "✏️  الدرجات:    <b>{count}</b>",
    "stats.exams_count": "🎓 الامتحانات:  <b>{count}</b>",
    "stats.credits_count": "📝 الاختبارات:  <b>{count}</b>",
    "stats.rating": "⭐ التقييم:    {icon} <b>{avg:.1f}</b> / {max:.1f} ({pct:.0f}%)",
    "stats.updated_at": "\n<i>آخر تحديث: {dt}</i>",
    "stats.choose_period": "📊 <b>الإحصائيات الدراسية</b>\n\nاختر الفترة:",
    "stats.all_time_button": "📊 كل الوقت",

    "subjects.not_connected": "📚 <b>eCampus غير متصل</b>\n\nقم بربط حسابك في الملف الشخصي على الموقع.",
    "subjects.no_data": "📭 لا توجد بيانات. حدّث المزامنة.",
    "subjects.none_for_term": "📭 لم يتم العثور على مواد ({sem_label}).",
    "subjects.header": "📚 <b>المواد · {sem_label}</b> ({count})\n",
    "subjects.no_type_data": "لا توجد بيانات",
    "subjects.rating_line": "\n    {icon} التقييم: <b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>امتحان</i>",
    "subjects.credit_tag": " 📝<i>اختبار</i>",

    "ecampus.not_connected": (
        "📚 <b>NCFU eCampus</b>\n\n"
        "الحساب <b>غير متصل</b>.\n\n"
        "قم بربطه في <b>الملف الشخصي ← eCampus</b> على الموقع "
        "أو في التطبيق المصغر للحصول على:\n"
        "  • قائمة المواد والدرجات\n"
        "  • الإحصائيات الدراسية\n"
        "  • تقييمات كل مادة\n\n"
        "الأوامر (بعد الربط):\n"
        "  /grades   — درجاتي\n"
        "  /stats    — الإحصائيات الدراسية\n"
        "  /subjects — قائمة المواد"
    ),
    "ecampus.status_ok": "✅ تمت المزامنة",
    "ecampus.status_running": "⏳ جاري المزامنة...",
    "ecampus.status_error": "❌ خطأ في المزامنة",
    "ecampus.status_pending": "🕐 في انتظار المزامنة",
    "ecampus.header": "📚 <b>NCFU eCampus</b>\n",
    "ecampus.status_line": "🔗 الحالة: {status}",
    "ecampus.subjects_count": "📦 المواد: <b>{count}</b>",
    "ecampus.grades_count": "✏️  الدرجات: <b>{count}</b>",
    "ecampus.updated_at": "🕐 آخر تحديث: <b>{dt}</b>",
    "ecampus.current_term": "\n📅 الفصل الحالي: <b>{term}</b>",
    "ecampus.term_subjects": "   المواد: <b>{count}</b>",
    "ecampus.term_grades": "   الدرجات: <b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>الأوامر:</b>\n"
        "  /grades   — درجاتي للفصل الحالي\n"
        "  /grades 2 — درجات الفصل 2\n"
        "  /stats    — الإحصائيات الكاملة\n"
        "  /subjects — قائمة المواد"
    ),

    "ai.empty_message": "اكتب شيئًا 🙂",
    "ai.processing": "⏳ جاري المعالجة...",
    "ai.unknown_request": "❓ طلب غير معروف.",
    "ai.parse_failed": "❌ تعذّر فهم الطلب. حاول إعادة صياغته.",
    "ai.execution_error": "❌ خطأ في تنفيذ الطلب.\n<code>{eid}</code>",
    "ai.processing_error": "❌ خطأ في معالجة الطلب.",

    "language.prompt": "🌐 <b>اختر لغة الواجهة</b>\n\nهذا الاختيار يُزامَن مع الموقع والتطبيق المصغر.",
    "language.saved": "✅ تم تغيير اللغة إلى <b>{name}</b>.",
    "language.save_failed": "⚠️ تعذّر حفظ اللغة. حاول مرة أخرى.",

    "cmd.start": "بدء الاستخدام",
    "cmd.me": "لوحة التحكم الشخصية 👤",
    "cmd.help": "المساعدة",
    "cmd.miniapp": "فتح الجدول (تطبيق مصغر) 📅",
    "cmd.grades": "درجاتي من eCampus",
    "cmd.stats": "الإحصائيات الدراسية 📊",
    "cmd.subjects": "قائمة المواد",
    "cmd.classmates": "زملاء الدراسة 👥",
    "cmd.teacher": "البحث عن أستاذ 👤",
    "cmd.ecampus": "حالة eCampus",
    "cmd.limit": "حد الطلبات",
    "cmd.language": "لغة الواجهة 🌐",
    "cmd.login": "تسجيل الدخول إلى الموقع",
    "cmd.code": "إدخال الرمز (/code XXXXXX)",
    "cmd.support": "الدعم",
    "cmd.suggest": "اقترح فكرة",
    "cmd.about": "عن الروبوت",
}
