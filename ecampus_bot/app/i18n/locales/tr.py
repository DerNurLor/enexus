"""Türkçe."""

MESSAGES: dict[str, str] = {
    "start.greeting": (
        "👋 Merhaba! Ben NCFU ders programı botuyum.\n\n"
        "Bana doğal dilde sorabilirsin:\n"
        "  • <i>Bu hafta ISS-b-o-22-3 ders programı</i>\n"
        "  • <i>Podzolko'nun dersi 5 dakika sonra nerede?</i>\n"
        "  • <i>11. binada boş dersликler</i>\n"
        "  • <i>AIS-b-o-25-1 grubu şu an ne yapıyor?</i>\n\n"
        "📋 <b>Komutlar:</b>\n"
        "  /me         — kişisel panel 👤\n"
        "  /miniapp    — uygulamada ders programı 📅\n"
        "  /grades     — eCampus notlarım\n"
        "  /stats      — istatistikler 📊\n"
        "  /classmates — sınıf arkadaşları 👥\n"
        "  /teacher    — öğretmen bul\n"
        "  /help       — tam yardım"
    ),
    "start.login_welcome": "👋 Merhaba {name}!\n\n🔐 <b>Yeni giriş yöntemi</b>\n\n1. <a href=\"{web_url}/profile\">{web_url}/profile</a> adresini açın\n2. <b>«Telegram ile giriş yap»</b>a tıklayın\n3. Gösterilen <b>6 haneli kodu</b> bana gönderin\n4. Onaylayın — sayfa otomatik olarak yenilenecek ✨",

    "help.full": (
        "📖 <b>NCFU ders programı botu yardımı</b>\n\n"
        "Sadece doğal dilde sor:\n\n"
        "📅 <b>Ders programı:</b>\n"
        "  <i>ISS-b-o-22-3 ders programı</i>\n"
        "  <i>AIS25 grubunun yarın dersi ne?</i>\n\n"
        "👤 <b>Öğretmen:</b>\n"
        "  <i>Podzolko şu an nerede?</i>  ·  <i>Ivanov'un ders programı</i>\n\n"
        "🚪 <b>Derslikler:</b>\n"
        "  <i>Şu anda boş derslikler</i>\n\n"
        "📋 <b>Komutlar:</b>\n"
        "  /me          — kişisel panel 👤\n"
        "  /miniapp     — uygulamada ders programı 📅\n"
        "  /grades      — eCampus notlarım\n"
        "  /stats       — akademik istatistikler 📊\n"
        "  /subjects    — ders listesi\n"
        "  /classmates  — sınıf arkadaşlarım 👥\n"
        "  /teacher     — öğretmen bul\n"
        "  /ecampus     — eCampus durumu\n"
        "  /limit       — istek limiti\n"
        "  /language    — arayüz dili 🌐\n"
        "  /support     — destek\n"
        "  /suggest     — fikir öner\n\n"
        "💡 <i>Gruplarda benden bahsedin: @botname isteğiniz</i>"
    ),
    "help.quick": (
        "📖 <b>Hızlı yardım</b>\n\n"
        "/me       — bu ekran\n"
        "/grades   — eCampus notları\n"
        "/stats    — istatistikler (dönem seçimi)\n"
        "/subjects — ders listesi\n"
        "/teacher  — öğretmen bul\n"
        "/classmates — sınıf arkadaşları\n"
        "/limit    — istek limiti\n"
        "/miniapp  — uygulamayı aç\n"
        "/help     — tam yardım"
    ),

    "group_welcome.text": (
        "👋 Merhaba! <b>{chat_title}</b>'a katılmaktan mutluluk duyarım!\n\n"
        "📌 <b>Yapabildiklerim:</b>\n"
        "  • Grup, öğretmen veya derslik ders programı\n"
        "  • Şu anda boş derslikler\n"
        "  • Öğretmen ve grup arama\n\n"
        "💬 <b>Benimle nasıl konuşulur:</b>\n"
        "  Bahsedin: <code>@{bot_username} ders programı ISS-b-o-22-3</code>\n"
        "  Veya komutları kullanın:\n"
        "  /help — yapabildiğim her şey\n"
        "  /miniapp — uygulamada ders programı 📅\n\n"
        "🔕 <i>Tüm sohbeti takip etmiyorum — yalnızca bahsedilme ve komutlara cevap veririm.</i>"
    ),
    "group_welcome.default_title": "bu grup",
    "common.open_schedule_button": "📅 Ders programını aç",

    "mykey.disabled": "/mykey komutu devre dışı.",

    "roles.role.admin": "Yönetici",
    "roles.role.moderator": "Moderatör",
    "roles.role.vip": "VIP",
    "roles.role.beta": "Beta test eden",
    "roles.role.user": "Kullanıcı",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>Roller:</b>",
    "roles.privileges_label": "\n🔓 <b>Ayrıcalıklar:</b>",
    "roles.priv_admin_panel": "⚙️ <b>Yönetim paneli</b> → <a href=\"{url}\">aç</a>",
    "roles.priv_beta": "🧪 <b>Beta erişimi</b> — genişletilmiş ders programı filtreleri",
    "roles.priv_floorplan_edit": "🗺 Kat planlarını <b>düzenleme</b>",
    "roles.priv_floorplan_view": "🗺 Kat planlarını <b>görüntüleme</b>",
    "roles.priv_personal_limit": "📊 <b>Kişisel limit</b>: dönem başına {limit} istek",
    "roles.profile_link": "\n💼 <b>Kişisel panel:</b> <a href=\"{url}\">aç</a>",

    "suggest.prompt": (
        "💡 <b>Öneriler ve fikirler</b>\n\n"
        "Botu veya ders programını geliştirmek için bir fikriniz mi var?\n"
        "Komuttan sonra yazın:\n\n"
        "<code>/suggest Fikriniz buraya</code>\n\n"
        "<i>Örnek: /suggest Dersten 10 dakika önce hatırlatma ekle</i>"
    ),
    "suggest.accepted": "✅ <b>Öneri alındı!</b>\n\nTeşekkürler, fikriniz botu daha iyi hale getirmeye yardımcı olacak.\nNumara: <code>{ticket_id}</code>\n",

    "about.text": (
        "🎓 <b>NCFU ders programı botu</b>\n\n"
        "Kuzey Kafkasya Federal Üniversitesi öğrenci ve öğretim üyeleri için akıllı asistan.\n\n"
        "📌 <b>Özellikler:</b>\n"
        "  • Grup, öğretmen, derslik ders programları\n"
        "  • Gerçek zamanlı boş derslikler\n"
        "  • Grup ve öğretmen arama\n"
        "  • Tam ders programı ile Mini App 📅\n\n"
        "🔗 <b>Bağlantılar:</b>\n"
        "  • <a href=\"{miniapp_url}\">Ders programı Mini App</a>\n"
        "🛠 <b>Sürüm:</b> 2.0\n"
        "💬 Sorular ve öneriler: /support · /suggest"
    ),

    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — uygulamada tam ders programı\n\n"
        "• Grup, öğretmen, derslik ile esnek arama\n"
        "• Gerçek zamanlı boş derslikler\n"
        "• Bina kat planları\n"
        "• Favoriler ve kişisel ayarlar\n\n"
        "Aşağıdaki düğmeye dokunun 👇"
    ),

    "support.prompt": "📬 <b>Destek</b>\n\nSorunuzu komuttan sonra yazın:\n<code>/support Sorunuz buraya</code>",
    "support.accepted": "✅ <b>Talep alındı</b>\n\nEn kısa sürede size geri döneceğiz.\nTalep numarası: <code>{ticket_id}</code>",

    "limit.header": "📊 <b>{scope} limiti</b>",
    "limit.scope_private": "kişisel istek",
    "limit.scope_chat": "bu sohbetteki istek",
    "limit.used": "✅ Kullanılan: <b>{used}</b>",
    "limit.remaining": "💬 Kalan: <b>{remaining}</b>",
    "limit.max": "🏁 Maksimum: <b>{cap}</b>",
    "limit.reset_in": "🔄 Sıfırlanma: <b>{reset_str}</b>",
    "limit.reset_done": "🔄 Limit zaten sıfırlandı — tekrar kullanabilirsiniz",
    "limit.exhausted_note": "<i>Limit doldu. Sıfırlanmasını bekleyin veya bir yöneticiyle iletişime geçin.</i>",
    "limit.normal_note": "<i>Bu limit yalnızca AI isteklerini (ders programı, arama) sayar. /start, /help ve diğer komutlar sayılmaz.</i>",

    "login.instructions": (
        "🔐 <b>Siteye giriş</b>\n\n"
        "1. <a href=\"{web_url}/profile\">{web_url}/profile</a> adresini açın\n"
        "2. <b>«Telegram ile giriş yap»</b>a tıklayın\n"
        "3. <b>6 harfli bir kod</b> (büyük Latin harfleri) göreceksiniz\n"
        "4. Bunu <code>/code XXXXXX</code> ile gönderin\n"
        "5. Onaylayın — sayfa otomatik olarak yenilenecek\n\n"
        "💡 Ya da sadece <code>/code</code> ve kodu boşlukla ayırarak yazın."
    ),
    "login.code_missing": "❓ Komuttan sonra kodu belirtin:\n<code>/code XXXXXX</code>\n\nKod, sitede «Telegram ile giriş yap»a tıklandığında görünür.",
    "login.code_invalid_format": "❌ Kod <b>6 büyük harf ve sayıdan</b> oluşmalıdır.\nÖrnek: <code>/code ABCDEF</code>",
    "login.account_blocked": "❌ Hesabınız engellendi.",
    "login.server_error": "⚠️ Sunucu hatası. Daha sonra tekrar deneyin.",
    "login.code_error": "❌ <b>{error}</b>\n\nSitedeki kodu kontrol edip tekrar deneyin.\nKod <b>3 dakika</b> geçerlidir.",
    "login.code_error_default": "Geçersiz veya süresi dolmuş kod",
    "login.code_error_server": "Sunucu hatası",
    "login.confirm_prompt": "🔐 <b>Girişi onayla</b>\n\nMerhaba {name}! Birisi hesabınızla siteye giriş yapıyor.\n\nGirişi onaylıyor musunuz?",
    "login.confirm_button": "✅ Girişi onayla",
    "login.cancel_button": "❌ İptal",
    "login.cancelled": "❌ <b>Giriş iptal edildi.</b>\n\nBu siz değilseniz sorun yok — bağlantı zaten geçersiz.",
    "login.cancelled_toast": "Giriş iptal edildi",
    "login.confirm_error": "⚠️ <b>Onay hatası.</b>\n\nOturumun süresi dolmuş olabilir. Tekrar giriş yapmayı deneyin.",
    "login.confirm_error_toast": "Hata, tekrar deneyin",
    "login.confirmed": "✅ <b>Giriş onaylandı!</b>\n\nSite sayfası otomatik olarak yenilenecek.",
    "login.confirmed_toast": "Giriş yapıldı ✅",
    "login.default_name": "kullanıcı",

    "disambig.stale_data": "⏱ Veriler eski. Lütfen tekrar deneyin.",
    "disambig.stale_button": "⚠️ Eski düğme. Lütfen tekrar deneyin.",
    "disambig.expired": "⏱ Seçim süresi doldu. Lütfen tekrar deneyin.",
    "disambig.loading": "⏳ Ders programı yükleniyor…",
    "disambig.unknown_intent": "❓ Bilinmeyen istek türü.",
    "disambig.error": "❌ Ders programı yüklenirken hata oluştu.\n<code>{eid}</code>",
    "disambig.format_error": "❌ Ders programı işlenirken hata oluştu.",
    "disambig.day_of": "{total} günden {idx}. gün",
    "disambig.prev_page": "◀ Önceki",
    "disambig.next_page": "Sonraki ▶",
    "disambig.group_label": "grup #{id}",
    "disambig.room_label": "derslik #{id}",
    "disambig.schedule_title": "Ders programı · {title}",

    "feedback.error_toast": "⚠️ Hata",
    "feedback.already_rated_toast": "Zaten değerlendirildi ✓",
    "feedback.save_failed_toast": "⚠️ Değerlendirme kaydedilemedi",
    "feedback.thanks_toast": "{icon} Değerlendirme kaydedildi, teşekkürler!",

    "classmates.profile_not_found": "👤 Profiliniz bulunamadı.",
    "classmates.no_group": "👥 <b>Grup ayarlanmadı</b>\n\nSınıf arkadaşlarını görmek için sitede profilinizi ayarlayın.",
    "classmates.query_error": "❌ Sınıf arkadaşları listesi alınırken hata oluştu.",
    "classmates.header": "👥 <b>Sınıf arkadaşları · {group_label}</b>\n",
    "classmates.registered_count": "<i>Kayıtlı: {count} kişi</i>\n",
    "classmates.none_registered": "👥 <b>Sınıf arkadaşları · {group_label}</b>\n\nGrubunuzdan henüz kimse bota kayıt olmadı.",
    "classmates.group_fallback_label": "grup #{id}",
    "classmates.more_suffix": "\n<i>…ve daha fazlası</i>",

    "teacher.search_prompt": "👤 <b>Öğretmen ara</b>\n\nSoyadını (veya bir kısmını) yazın:\n<code>/teacher Ivanov</code>",
    "teacher.search_error": "❌ Arama hatası.",
    "teacher.not_found": "🔍 <b>{query}</b> için sonuç bulunamadı.\n\nBaşka bir soyadı deneyin.",
    "teacher.found_count": "🔍 Bulunan öğretmen sayısı: <b>{count}</b>\n\nSeçin:",
    "teacher.not_found_short": "❌ Öğretmen bulunamadı.",
    "teacher.subjects_label": "\n📚 <b>Dersler:</b>",
    "teacher.more_subjects": "  <i>…ve {count} daha</i>",
    "teacher.lesson_types_label": "\n🗂 <b>Ders türleri:</b> {types}",
    "teacher.groups_label": "\n👥 <b>Gruplar ({count}):</b> {names}",
    "teacher.more_groups": "  <i>…ve {count} daha</i>",
    "teacher.lessons_in_db": "\n📊 Veritabanındaki ders sayısı: <b>{count}</b>",
    "teacher.schedule_loaded": "🕐 Ders programı: <b>yüklendi</b>",
    "teacher.alltime_stats_label": "\n📈 <b>Tüm zamanlar istatistikleri:</b>",
    "teacher.total_lessons": "  Toplam ders: <b>{count}</b>",
    "teacher.types_label": "  Türler: {types}",
    "teacher.buildings_label": "  Binalar: {buildings}",
    "teacher.rooms_label": "  Derslikler: {rooms}",
    "teacher.schedule_button": "📅 Ders programı",

    "me.profile_not_found": "👤 Profil bulunamadı.",
    "me.header": "👤 <b>Kişisel panel</b>\n",
    "me.role_student": "Öğrenci",
    "me.role_teacher": "Öğretmen",
    "me.role_unset": "Ayarlanmadı",
    "me.group_line": "\n📌 Grup: <b>{group_name}</b>",
    "me.teacher_line": "\n📌 Öğretmen: <b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 İstek limiti: <code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 Ders programım",
    "me.miniapp_button": "📱 Ders programı (uygulama)",
    "me.subjects_button": "📚 Dersler",
    "me.stats_button": "📊 İstatistikler",
    "me.classmates_button": "👥 Sınıf arkadaşları",
    "me.my_lessons_button": "📈 Derslerim",
    "me.profile_button": "⚙️ Profil",
    "me.map_button": "🗺 Harita",
    "me.limit_button": "💬 İstek limiti",
    "me.help_button": "❓ Yardım",
    "me.no_ecampus_data": "📭 eCampus verisi yok.",
    "me.stats_choose_period": "📊 <b>Akademik istatistikler</b>\n\nBir dönem seçin:",

    "grades.not_connected": "📚 <b>eCampus bağlı değil</b>\n\nSitedeki ya da mini uygulamadaki <b>Profil → eCampus</b> bölümünden eCampus hesabınızı bağlayın.",
    "grades.sync_running": "⏳ eCampus ile senkronizasyon hâlâ sürüyor — veriler güncelleniyor.\nBir dakika sonra tekrar deneyin.",
    "grades.empty": "📭 eCampus verileri henüz boş.\nMini uygulamada «Yenile»ye dokunun veya otomatik senkronizasyonu bekleyin.",
    "grades.semester_label": "{n}. Dönem",
    "grades.current_semester_label": "Mevcut dönem",
    "grades.no_grades": "📭 <b>Not yok</b> ({sem_label})\n\nNotlar öğretmen tarafından girildikten sonra görünecek.",
    "grades.header": "📊 <b>Notlar · {sem_label}</b>\n",
    "grades.total": "\n<i>Toplam not: {count}</i>",
    "grades.page_suffix": "\n\n({page}/{total})",

    "stats.not_connected_short": "📚 <b>eCampus bağlı değil</b>\n\nSitedeki Profil bölümünden hesabınızı bağlayın.",
    "stats.no_data": "📭 eCampus verisi yok. Senkronizasyonu yenileyin.",
    "stats.no_term_data": "📭 Bu dönem için veri yok.",
    "stats.all_time_suffix": " · Tüm zamanlar",
    "stats.term_fallback": " · dönem {id}",
    "stats.header": "📊 <b>Akademik istatistikler{suffix}</b>\n",
    "stats.subjects_count": "📚 Dersler:     <b>{count}</b>",
    "stats.grades_count": "✏️  Notlar:       <b>{count}</b>",
    "stats.exams_count": "🎓 Sınavlar:    <b>{count}</b>",
    "stats.credits_count": "📝 Geçme/Kalma: <b>{count}</b>",
    "stats.rating": "⭐ Puan:        {icon} <b>{avg:.1f}</b> / {max:.1f} (%{pct:.0f})",
    "stats.updated_at": "\n<i>Güncellendi: {dt}</i>",
    "stats.choose_period": "📊 <b>Akademik istatistikler</b>\n\nBir dönem seçin:",
    "stats.all_time_button": "📊 Tüm zamanlar",

    "subjects.not_connected": "📚 <b>eCampus bağlı değil</b>\n\nSitedeki Profil bölümünden hesabınızı bağlayın.",
    "subjects.no_data": "📭 Veri yok. Senkronizasyonu yenileyin.",
    "subjects.none_for_term": "📭 Ders bulunamadı ({sem_label}).",
    "subjects.header": "📚 <b>Dersler · {sem_label}</b>  ({count} adet)\n",
    "subjects.no_type_data": "veri yok",
    "subjects.rating_line": "\n    {icon} Puan: <b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>Sınav</i>",
    "subjects.credit_tag": " 📝<i>Geçme/Kalma</i>",

    "ecampus.not_connected": (
        "📚 <b>NCFU eCampus</b>\n\n"
        "Hesap <b>bağlı değil</b>.\n\n"
        "Şunları almak için sitedeki ya da mini uygulamadaki "
        "<b>Profil → eCampus</b> bölümünden bağlayın:\n"
        "  • Ders ve not listesi\n"
        "  • Akademik istatistikler\n"
        "  • Her ders için puanlar\n\n"
        "Komutlar (bağlandıktan sonra):\n"
        "  /grades   — notlarım\n"
        "  /stats    — akademik istatistikler\n"
        "  /subjects — ders listesi"
    ),
    "ecampus.status_ok": "✅ Senkronize edildi",
    "ecampus.status_running": "⏳ Senkronize ediliyor...",
    "ecampus.status_error": "❌ Senkronizasyon hatası",
    "ecampus.status_pending": "🕐 Senkronizasyon bekleniyor",
    "ecampus.header": "📚 <b>NCFU eCampus</b>\n",
    "ecampus.status_line": "🔗 Durum: {status}",
    "ecampus.subjects_count": "📦 Dersler: <b>{count}</b>",
    "ecampus.grades_count": "✏️  Notlar: <b>{count}</b>",
    "ecampus.updated_at": "🕐 Güncellendi: <b>{dt}</b>",
    "ecampus.current_term": "\n📅 Mevcut dönem: <b>{term}</b>",
    "ecampus.term_subjects": "   Dersler: <b>{count}</b>",
    "ecampus.term_grades": "   Notlar: <b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>Komutlar:</b>\n"
        "  /grades   — mevcut dönem notlarım\n"
        "  /grades 2 — 2. dönem notları\n"
        "  /stats    — tam istatistikler\n"
        "  /subjects — ders listesi"
    ),

    "ai.empty_message": "Bir şey yazın 🙂",
    "ai.processing": "⏳ İşleniyor...",
    "ai.unknown_request": "❓ Bilinmeyen istek.",
    "ai.parse_failed": "❌ İstek anlaşılamadı. Yeniden ifade etmeyi deneyin.",
    "ai.execution_error": "❌ İstek çalıştırılırken hata oluştu.\n<code>{eid}</code>",
    "ai.processing_error": "❌ İstek işlenirken hata oluştu.",

    "language.prompt": "🌐 <b>Arayüz dilini seçin</b>\n\nBu seçim web sitesi ve mini uygulama ile senkronize edilir.",
    "language.saved": "✅ Dil <b>{name}</b> olarak değiştirildi.",
    "language.save_failed": "⚠️ Dil kaydedilemedi. Tekrar deneyin.",

    "cmd.start": "Başlayın",
    "cmd.me": "Kişisel panel 👤",
    "cmd.help": "Yardım",
    "cmd.miniapp": "Ders programını aç (Mini App) 📅",
    "cmd.grades": "eCampus notlarım",
    "cmd.stats": "Akademik istatistikler 📊",
    "cmd.subjects": "Ders listesi",
    "cmd.classmates": "Sınıf arkadaşlarım 👥",
    "cmd.teacher": "Öğretmen bul 👤",
    "cmd.ecampus": "eCampus durumu",
    "cmd.limit": "İstek limiti",
    "cmd.language": "Arayüz dili 🌐",
    "cmd.login": "Siteye giriş yap",
    "cmd.code": "Kod girin (/code XXXXXX)",
    "cmd.support": "Destek",
    "cmd.suggest": "Fikir öner",
    "cmd.about": "Bot hakkında",
}
