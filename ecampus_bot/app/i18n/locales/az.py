"""Azərbaycan dili — ru.py əsasında hazırlanmış tərcümə."""

MESSAGES: dict[str, str] = {
    # ── /start ───────────────────────────────────────────────────────────────
    "start.greeting": (
        "👋 Salam! Mən SKFU dərs cədvəli botuyam.\n\n"
        "Sualınızı təbii dildə yazın:\n"
        "  • <i>ИСС-б-о-22-3 qrupunun bu həftəlik cədvəli</i>\n"
        "  • <i>Podzolkonun dərsi 5 dəqiqədən sonra harada?</i>\n"
        "  • <i>11-ci korpusda boş otaqlar</i>\n"
        "  • <i>АИС-б-о-25-1 qrupunda indi nə var?</i>\n\n"
        "📋 <b>Əmrlər:</b>\n"
        "  /me         — şəxsi kabinet 👤\n"
        "  /miniapp    — tətbiqdə cədvəl 📅\n"
        "  /grades     — eCampus-dakı qiymətlərim\n"
        "  /stats      — statistika 📊\n"
        "  /classmates — qrupdaşlar 👥\n"
        "  /teacher    — müəllim tapmaq\n"
        "  /help       — tam kömək"
    ),
    "start.login_welcome": "👋 Salam, {name}!\n\n🔐 <b>Yeni giriş üsulu</b>\n\n1. <a href=\"{web_url}/profile\">{web_url}/profile</a> açın\n2. <b>«Telegram ilə giriş»</b> düyməsini basın\n3. Göstərilən <b>6 rəqəmli kodu</b> mənə göndərin\n4. Təsdiqləyin — səhifə özü yenilənəcək ✨",

    # ── /help ────────────────────────────────────────────────────────────────
    "help.full": (
        "📖 <b>SKFU dərs cədvəli botu üzrə kömək</b>\n\n"
        "Sorğunuzu təbii dildə yazın:\n\n"
        "📅 <b>Cədvəl:</b>\n"
        "  <i>ИСС-б-о-22-3 cədvəli</i>\n"
        "  <i>АИС25 qrupunda sabah nə var?</i>\n\n"
        "👤 <b>Müəllim:</b>\n"
        "  <i>Podzolko indi haradadır?</i>  ·  <i>İvanovun cədvəli</i>\n\n"
        "🚪 <b>Otaqlar:</b>\n"
        "  <i>İndi boş otaqlar</i>\n\n"
        "📋 <b>Əmrlər:</b>\n"
        "  /me          — şəxsi kabinet 👤\n"
        "  /miniapp     — tətbiqdə cədvəl 📅\n"
        "  /grades      — eCampus-dakı qiymətlərim\n"
        "  /stats       — akademik göstəricilər statistikası 📊\n"
        "  /subjects    — fənlərin siyahısı\n"
        "  /classmates  — qrupdaşlarım 👥\n"
        "  /teacher     — müəllim tapmaq\n"
        "  /ecampus     — eCampus statusu\n"
        "  /limit       — sorğu limiti\n"
        "  /language    — interfeys dili 🌐\n"
        "  /support     — dəstək\n"
        "  /suggest     — ideya təklif et\n\n"
        "💡 <i>Qruplarda məni qeyd edərək müraciət edin: @botname sorğu</i>"
    ),
    "help.quick": (
        "📖 <b>Tez kömək</b>\n\n"
        "/me       — bu ekran\n"
        "/grades   — eCampus qiymətləri\n"
        "/stats    — statistika (semestr seçimi ilə)\n"
        "/subjects — fənlərin siyahısı\n"
        "/teacher  — müəllim axtarışı\n"
        "/classmates — qrupdaşlar\n"
        "/limit    — sorğu limiti\n"
        "/miniapp  — tətbiqi aç\n"
        "/help     — tam kömək"
    ),

    # ── Группа: приветствие при добавлении бота ─────────────────────────────────
    "group_welcome.text": (
        "👋 Salam! <b>{chat_title}</b> qrupuna qoşulmağıma şadam!\n\n"
        "📌 <b>Bacarıqlarım:</b>\n"
        "  • Qrupun, müəllimin, otağın cədvəli\n"
        "  • İndi boş olan otaqlar\n"
        "  • Müəllim və qruplar üzrə axtarış\n\n"
        "💬 <b>Necə müraciət etmək olar:</b>\n"
        "  Məni qeyd edin: <code>@{bot_username} ИСС-б-о-22-3 cədvəli</code>\n"
        "  Və ya əmrlərdən istifadə edin:\n"
        "  /help — bütün imkanlar\n"
        "  /miniapp — tətbiqdə cədvəl 📅\n\n"
        "🔕 <i>Mən ümumi söhbəti izləmirəm — yalnız qeydlərə və əmrlərə cavab verirəm.</i>"
    ),
    "group_welcome.default_title": "bu qrup",
    "common.open_schedule_button": "📅 Cədvəli aç",

    # ── /mykey (отключена) ───────────────────────────────────────────────────
    "mykey.disabled": "/mykey əmri deaktivdir.",

    # ── /roles ───────────────────────────────────────────────────────────────
    "roles.role.admin": "Administrator",
    "roles.role.moderator": "Moderator",
    "roles.role.vip": "VIP",
    "roles.role.beta": "Beta-sınaqçı",
    "roles.role.user": "İstifadəçi",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>Rollar:</b>",
    "roles.privileges_label": "\n🔓 <b>İmtiyazlar:</b>",
    "roles.priv_admin_panel": "⚙️ <b>İdarəetmə paneli</b> → <a href=\"{url}\">aç</a>",
    "roles.priv_beta": "🧪 <b>Beta-giriş</b> — cədvəlin genişləndirilmiş filtrləri",
    "roles.priv_floorplan_edit": "🗺 Mərtəbə planlarını <b>redaktə etmə</b>",
    "roles.priv_floorplan_view": "🗺 Mərtəbə planlarına <b>baxış</b>",
    "roles.priv_personal_limit": "📊 <b>Şəxsi limit</b>: {limit} sorğu / dövr",
    "roles.profile_link": "\n💼 <b>Şəxsi kabinet:</b> <a href=\"{url}\">aç</a>",

    # ── /suggest ─────────────────────────────────────────────────────────────
    "suggest.prompt": (
        "💡 <b>Təkliflər və ideyalar</b>\n\n"
        "Botu və ya cədvəli yaxşılaşdırmaq üçün ideyanız var?\n"
        "Əmrdən sonra yazın:\n\n"
        "<code>/suggest İdeyanız bura</code>\n\n"
        "<i>Məsələn: /suggest Dərsdən 10 dəqiqə əvvəl bildiriş əlavə et</i>"
    ),
    "suggest.accepted": "✅ <b>Təklif qəbul edildi!</b>\n\nTəşəkkürlər, ideyanız botu daha yaxşı etməyə kömək edəcək.\nNömrə: <code>{ticket_id}</code>\n",

    # ── /about ───────────────────────────────────────────────────────────────
    "about.text": (
        "🎓 <b>SKFU dərs cədvəli botu</b>\n\n"
        "Şimali Qafqaz federal universitetinin "
        "tələbə və müəllimləri üçün ağıllı köməkçi.\n\n"
        "📌 <b>İmkanlar:</b>\n"
        "  • Qrupların, müəllimlərin, otaqların cədvəli\n"
        "  • Real vaxtda boş otaqlar\n"
        "  • Qrup və müəllim axtarışı\n"
        "  • Tam cədvəlli Mini App 📅\n\n"
        "🔗 <b>Keçidlər:</b>\n"
        "  • <a href=\"{miniapp_url}\">Cədvəl Mini App</a>\n"
        "🛠 <b>Versiya:</b> 2.0\n"
        "💬 Suallar və təkliflər: /support · /suggest"
    ),

    # ── /miniapp ─────────────────────────────────────────────────────────────
    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — tətbiqdə tam cədvəl\n\n"
        "• Qrup, müəllim, otaq üzrə çevik axtarış\n"
        "• Real vaxtda boş otaqlar\n"
        "• Korpusların mərtəbə planları\n"
        "• Seçilmişlər və şəxsi tənzimləmələr\n\n"
        "Aşağıdaki düyməni basın 👇"
    ),

    # ── /support ─────────────────────────────────────────────────────────────
    "support.prompt": "📬 <b>Dəstək</b>\n\nSualınızı əmrdən sonra yazın:\n<code>/support Sualınız bura</code>",
    "support.accepted": "✅ <b>Müraciət qəbul edildi</b>\n\nSizə ən qısa zamanda cavab verəcəyik.\nMüraciət nömrəsi: <code>{ticket_id}</code>",

    # ── /limit ───────────────────────────────────────────────────────────────
    "limit.header": "📊 <b>{scope} limiti</b>",
    "limit.scope_private": "şəxsi sorğular",
    "limit.scope_chat": "bu söhbətdəki sorğular",
    "limit.used": "✅ İstifadə olunub: <b>{used}</b>",
    "limit.remaining": "💬 Qalıb: <b>{remaining}</b>",
    "limit.max": "🏁 Maksimum: <b>{cap}</b>",
    "limit.reset_in": "🔄 Sıfırlanma: <b>{reset_str}</b> sonra",
    "limit.reset_done": "🔄 Limit artıq sıfırlanıb — yenidən istifadə edə bilərsiniz",
    "limit.exhausted_note": "<i>Limit bitib. Sıfırlanmasını gözləyin və ya administratorla əlaqə saxlayın.</i>",
    "limit.normal_note": "<i>Limit AI sorğularını sayır (cədvəl, axtarış). /start, /help və digər əmrlər sayılmır.</i>",

    # ── /login, /code, подтверждение входа ──────────────────────────────────
    "login.instructions": (
        "🔐 <b>Saytda giriş</b>\n\n"
        "1. <a href=\"{web_url}/profile\">{web_url}/profile</a> açın\n"
        "2. <b>«Telegram ilə giriş»</b> düyməsini basın\n"
        "3. Sizə <b>6 hərfli kod</b> göstəriləcək (böyük latın hərfləri)\n"
        "4. Bu kodu <code>/code XXXXXX</code> əmri ilə göndərin\n"
        "5. Girişi təsdiqləyin — səhifə avtomatik yenilənəcək\n\n"
        "💡 Və ya sadəcə <code>/code</code> yazıb kodu boşluqdan sonra qeyd edin."
    ),
    "login.code_missing": "❓ Əmrdən sonra kodu qeyd edin:\n<code>/code XXXXXX</code>\n\nKod saytda «Telegram ilə giriş» düyməsinə basanda göstərilir.",
    "login.code_invalid_format": "❌ Kod <b>6 böyük hərf və rəqəmdən</b> ibarət olmalıdır.\nMisal: <code>/code ABCDEF</code>",
    "login.account_blocked": "❌ Hesabınız bloklanıb.",
    "login.server_error": "⚠️ Server xətası. Sonra yenidən cəhd edin.",
    "login.code_error": "❌ <b>{error}</b>\n\nKodu saytda yoxlayıb yenidən cəhd edin.\nKod <b>3 dəqiqə</b> etibarlıdır.",
    "login.code_error_default": "Səhv və ya vaxtı keçmiş kod",
    "login.code_error_server": "Server xətası",
    "login.confirm_prompt": "🔐 <b>Girişin təsdiqi</b>\n\nSalam, {name}! Kim isə sizin hesabınızla sayta daxil olmağa çalışır.\n\nGirişi təsdiqləyirsiniz?",
    "login.confirm_button": "✅ Girişi təsdiqlə",
    "login.cancel_button": "❌ Ləğv et",
    "login.cancelled": "❌ <b>Giriş ləğv edildi.</b>\n\nƏgər bu siz deyildinizsə — narahat olmayın, keçid artıq etibarsızdır.",
    "login.cancelled_toast": "Giriş ləğv edildi",
    "login.confirm_error": "⚠️ <b>Təsdiq xətası.</b>\n\nBəlkə sessiyanın vaxtı bitib. Yenidən giriş etməyə çalışın.",
    "login.confirm_error_toast": "Xəta, yenidən cəhd edin",
    "login.confirmed": "✅ <b>Giriş təsdiqləndi!</b>\n\nSaytdaki səhifə avtomatik yenilənəcək.",
    "login.confirmed_toast": "Giriş uğurla tamamlandı ✅",
    "login.default_name": "istifadəçi",

    # ── Дизамбигуация (выбор группы/аудитории) ──────────────────────────────
    "disambig.stale_data": "⏱ Məlumatlar köhnəlib. Sorğunu təkrarlayın.",
    "disambig.stale_button": "⚠️ Köhnəlmiş düymə. Sorğunu təkrarlayın.",
    "disambig.expired": "⏱ Seçim vaxtı bitdi. Sorğunu təkrarlayın.",
    "disambig.loading": "⏳ Cədvəl yüklənir…",
    "disambig.unknown_intent": "❓ Naməlum sorğu növü.",
    "disambig.error": "❌ Cədvəli yükləmə xətası.\n<code>{eid}</code>",
    "disambig.format_error": "❌ Cədvəl emalı xətası.",
    "disambig.day_of": "{total}-dən {idx}-gün",
    "disambig.prev_page": "◀ Əvvəlki",
    "disambig.next_page": "Növbəti ▶",
    "disambig.group_label": "qrup #{id}",
    "disambig.room_label": "otaq #{id}",
    "disambig.schedule_title": "Cədvəl · {title}",

    # ── Фидбэк 👍👎 ───────────────────────────────────────────────────────────
    "feedback.error_toast": "⚠️ Xəta",
    "feedback.already_rated_toast": "Artıq qiymətləndirilib ✓",
    "feedback.save_failed_toast": "⚠️ Qiymətləndirməni saxlamaq mümkün olmadı",
    "feedback.thanks_toast": "{icon} Qiymətləndirmə saxlanıldı, təşəkkürlər!",

    # ── /classmates ──────────────────────────────────────────────────────────
    "classmates.profile_not_found": "👤 Profiliniz tapılmadı.",
    "classmates.no_group": "👥 <b>Qrup təyin edilməyib</b>\n\nQrupdaşlarınızı görmək üçün saytda profilinizi tənzimləyin.",
    "classmates.query_error": "❌ Qrupdaşlar siyahısını əldə etmə xətası.",
    "classmates.header": "👥 <b>Qrupdaşlar · {group_label}</b>\n",
    "classmates.registered_count": "<i>Qeydiyyatdan keçib: {count} nəfər.</i>\n",
    "classmates.none_registered": "👥 <b>Qrupdaşlar · {group_label}</b>\n\nQrupunuzdan hələ heç kim botda qeydiyyatdan keçməyib.",
    "classmates.group_fallback_label": "qrup #{id}",
    "classmates.more_suffix": "\n<i>…və daha çox</i>",

    # ── /teacher ──────────────────────────────────────────────────────────────
    "teacher.search_prompt": "👤 <b>Müəllim axtarışı</b>\n\nSoyadı (və ya bir hissəsini) yazın:\n<code>/teacher İvanov</code>",
    "teacher.search_error": "❌ Axtarış xətası.",
    "teacher.not_found": "🔍 <b>{query}</b> üzrə heç nə tapılmadı.\n\nBaşqa soyad cəhd edin.",
    "teacher.found_count": "🔍 Tapılan müəllimlər: <b>{count}</b>\n\nSeçin:",
    "teacher.not_found_short": "❌ Müəllim tapılmadı.",
    "teacher.subjects_label": "\n📚 <b>Fənlər:</b>",
    "teacher.more_subjects": "  <i>…və daha {count}</i>",
    "teacher.lesson_types_label": "\n🗂 <b>Dərs növləri:</b> {types}",
    "teacher.groups_label": "\n👥 <b>Qruplar ({count}):</b> {names}",
    "teacher.more_groups": "  <i>…və daha {count}</i>",
    "teacher.lessons_in_db": "\n📊 Bazadaki dərslər: <b>{count}</b>",
    "teacher.schedule_loaded": "🕐 Cədvəl: <b>yükləndi</b>",
    "teacher.alltime_stats_label": "\n📈 <b>Bütün dövr üçün statistika:</b>",
    "teacher.total_lessons": "  Cəmi dərslər: <b>{count}</b>",
    "teacher.types_label": "  Növlər: {types}",
    "teacher.buildings_label": "  Korpuslar: {buildings}",
    "teacher.rooms_label": "  Otaqlar: {rooms}",
    "teacher.schedule_button": "📅 Cədvəl",

    # ── /me ──────────────────────────────────────────────────────────────────
    "me.profile_not_found": "👤 Profil tapılmadı.",
    "me.header": "👤 <b>Şəxsi kabinet</b>\n",
    "me.role_student": "Tələbə",
    "me.role_teacher": "Müəllim",
    "me.role_unset": "Tənzimlənməyib",
    "me.group_line": "\n📌 Qrup: <b>{group_name}</b>",
    "me.teacher_line": "\n📌 Müəllim: <b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 Sorğu limiti: <code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 Mənim cədvəlim",
    "me.miniapp_button": "📱 Cədvəl (tətbiq)",
    "me.subjects_button": "📚 Fənlər",
    "me.stats_button": "📊 Statistika",
    "me.classmates_button": "👥 Qrupdaşlar",
    "me.my_lessons_button": "📈 Mənim dərslərim",
    "me.profile_button": "⚙️ Profil",
    "me.map_button": "🗺 Xəritə",
    "me.limit_button": "💬 Sorğu limiti",
    "me.help_button": "❓ Kömək",
    "me.no_ecampus_data": "📭 eCampus məlumatı yoxdur.",
    "me.stats_choose_period": "📊 <b>Akademik göstəricilər statistikası</b>\n\nDövrü seçin:",

    # ── /grades ──────────────────────────────────────────────────────────────
    "grades.not_connected": "📚 <b>eCampus qoşulmayıb</b>\n\neCampus hesabını saytda və ya mini-tətbiqdə <b>Profil → eCampus</b> bölməsində qoşun.",
    "grades.sync_running": "⏳ eCampus ilə sinxronizasiya hələ davam edir — məlumatlar yenilənir.\nBir dəqiqədən sonra cəhd edin.",
    "grades.empty": "📭 eCampus məlumatları hələ boşdur.\nMini-tətbiqdə «Yenilə» düyməsini basın və ya avtosinxronizasiyanı gözləyin.",
    "grades.semester_label": "{n}-ci semestr",
    "grades.current_semester_label": "Cari semestr",
    "grades.no_grades": "📭 <b>Qiymət yoxdur</b> ({sem_label})\n\nQiymətlər müəllim onları qoyandan sonra görünəcək.",
    "grades.header": "📊 <b>Qiymətlər · {sem_label}</b>\n",
    "grades.total": "\n<i>Cəmi qiymətlər: {count}</i>",
    "grades.page_suffix": "\n\n({page}/{total})",

    # ── /stats ───────────────────────────────────────────────────────────────
    "stats.not_connected_short": "📚 <b>eCampus qoşulmayıb</b>\n\nHesabı saytda Profil bölməsində qoşun.",
    "stats.no_data": "📭 eCampus məlumatı yoxdur. Sinxronizasiyanı yeniləyin.",
    "stats.no_term_data": "📭 Bu semestr üzrə məlumat yoxdur.",
    "stats.all_time_suffix": " · Bütün dövr",
    "stats.term_fallback": " · sem.{id}",
    "stats.header": "📊 <b>Akademik göstəricilər statistikası{suffix}</b>\n",
    "stats.subjects_count": "📚 Fənlər:   <b>{count}</b>",
    "stats.grades_count": "✏️  Qiymətlər:      <b>{count}</b>",
    "stats.exams_count": "🎓 İmtahanlar:  <b>{count}</b>",
    "stats.credits_count": "📝 Zaçotlar:    <b>{count}</b>",
    "stats.rating": "⭐ Reytinq:    {icon} <b>{avg:.1f}</b> / {max:.1f} ({pct:.0f}%)",
    "stats.updated_at": "\n<i>Yenilənib: {dt}</i>",
    "stats.choose_period": "📊 <b>Akademik göstəricilər statistikası</b>\n\nDövrü seçin:",
    "stats.all_time_button": "📊 Bütün dövr üçün",

    # ── /subjects ────────────────────────────────────────────────────────────
    "subjects.not_connected": "📚 <b>eCampus qoşulmayıb</b>\n\nHesabı saytda Profil bölməsində qoşun.",
    "subjects.no_data": "📭 Məlumat yoxdur. Sinxronizasiyanı yeniləyin.",
    "subjects.none_for_term": "📭 Fənlər tapılmadı ({sem_label}).",
    "subjects.header": "📚 <b>Fənlər · {sem_label}</b>  ({count} ədəd)\n",
    "subjects.no_type_data": "məlumat yoxdur",
    "subjects.rating_line": "\n    {icon} Reytinq: <b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>İmtahan</i>",
    "subjects.credit_tag": " 📝<i>Zaçot</i>",

    # ── /ecampus ─────────────────────────────────────────────────────────────
    "ecampus.not_connected": (
        "📚 <b>SKFU eCampus</b>\n\n"
        "Hesab <b>qoşulmayıb</b>.\n\n"
        "Onu saytda və ya mini-tətbiqdə <b>Profil → eCampus</b> "
        "bölməsində qoşun və əldə edin:\n"
        "  • Fənlər və qiymətlərin siyahısı\n"
        "  • Akademik göstəricilər statistikası\n"
        "  • Hər kurs üzrə reytinqlər\n\n"
        "Əmrlər (qoşulduqdan sonra):\n"
        "  /grades   — qiymətlərim\n"
        "  /stats    — akademik göstəricilər statistikası\n"
        "  /subjects — fənlərin siyahısı"
    ),
    "ecampus.status_ok": "✅ Sinxronlaşdırılıb",
    "ecampus.status_running": "⏳ Sinxronizasiya...",
    "ecampus.status_error": "❌ Sinxronizasiya xətası",
    "ecampus.status_pending": "🕐 Sinxronizasiya gözlənilir",
    "ecampus.header": "📚 <b>SKFU eCampus</b>\n",
    "ecampus.status_line": "🔗 Status: {status}",
    "ecampus.subjects_count": "📦 Fənlər: <b>{count}</b>",
    "ecampus.grades_count": "✏️  Qiymətlər: <b>{count}</b>",
    "ecampus.updated_at": "🕐 Yenilənib: <b>{dt}</b>",
    "ecampus.current_term": "\n📅 Cari semestr: <b>{term}</b>",
    "ecampus.term_subjects": "   Fənlər: <b>{count}</b>",
    "ecampus.term_grades": "   Qiymətlər: <b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>Əmrlər:</b>\n"
        "  /grades   — cari semestrin qiymətlərim\n"
        "  /grades 2 — 2-ci semestrin qiymətləri\n"
        "  /stats    — tam statistika\n"
        "  /subjects — fənlərin siyahısı"
    ),

    # ── ИИ-обработчик (ошибки/заглушки) ─────────────────────────────────────
    "ai.empty_message": "Nə isə yazın 🙂",
    "ai.processing": "⏳ Emal edilir...",
    "ai.unknown_request": "❓ Naməlum sorğu.",
    "ai.parse_failed": "❌ Sorğunu tanımaq mümkün olmadı. Yenidən formalaşdırın.",
    "ai.execution_error": "❌ Sorğunu icra etmə xətası.\n<code>{eid}</code>",
    "ai.processing_error": "❌ Sorğu emalı xətası.",

    # ── /language (новая команда) ───────────────────────────────────────────
    "language.prompt": "🌐 <b>İnterfeys dilini seçin</b>\n\nBu seçim sayt və mini-tətbiqlə sinxronlaşdırılır.",
    "language.saved": "✅ Dil <b>{name}</b> olaraq dəyişdirildi.",
    "language.save_failed": "⚠️ Dili saxlamaq mümkün olmadı. Yenidən cəhd edin.",

    # ── Меню команд бота (BotCommand description) ───────────────────────────
    "cmd.start": "İşə başlamaq",
    "cmd.me": "Şəxsi kabinet 👤",
    "cmd.help": "Kömək",
    "cmd.miniapp": "Cədvəli aç (Mini App) 📅",
    "cmd.grades": "eCampus-dakı qiymətlərim",
    "cmd.stats": "Akademik göstəricilər statistikası 📊",
    "cmd.subjects": "Fənlərin siyahısı",
    "cmd.classmates": "Qrupdaşlarım 👥",
    "cmd.teacher": "Müəllim tapmaq 👤",
    "cmd.ecampus": "eCampus statusu",
    "cmd.limit": "Sorğu limiti",
    "cmd.language": "İnterfeys dili 🌐",
    "cmd.login": "Saytda giriş",
    "cmd.code": "Kodu daxil et (/code XXXXXX)",
    "cmd.support": "Dəstək",
    "cmd.suggest": "İdeya təklif et",
    "cmd.about": "Bot haqqında",
}
