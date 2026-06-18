"""Tiếng Việt — bản dịch dựa trên ru.py."""

MESSAGES: dict[str, str] = {
    # ── /start ───────────────────────────────────────────────────────────────
    "start.greeting": (
        "👋 Xin chào! Tôi là bot lịch học của SKFU.\n\n"
        "Hãy hỏi bằng ngôn ngữ tự nhiên:\n"
        "  • <i>Lịch học của nhóm ИСС-б-о-22-3 tuần này</i>\n"
        "  • <i>Tiết học của Подзолко ở đâu sau 5 phút nữa?</i>\n"
        "  • <i>Phòng trống ở tòa 11</i>\n"
        "  • <i>Nhóm АИС-б-о-25-1 bây giờ có gì?</i>\n\n"
        "📋 <b>Các lệnh:</b>\n"
        "  /me         — trang cá nhân 👤\n"
        "  /miniapp    — lịch học trong ứng dụng 📅\n"
        "  /grades     — điểm của tôi từ eCampus\n"
        "  /stats      — thống kê 📊\n"
        "  /classmates — bạn cùng lớp 👥\n"
        "  /teacher    — tìm giảng viên\n"
        "  /help       — trợ giúp đầy đủ"
    ),
    "start.login_welcome": "👋 Xin chào, {name}!\n\n🔐 <b>Cách đăng nhập mới</b>\n\n1. Mở <a href=\"{web_url}/profile\">{web_url}/profile</a>\n2. Nhấn <b>«Đăng nhập bằng Telegram»</b>\n3. Gửi cho tôi <b>mã 6 chữ số</b> được hiển thị\n4. Xác nhận — trang sẽ tự cập nhật ✨",

    # ── /help ────────────────────────────────────────────────────────────────
    "help.full": (
        "📖 <b>Trợ giúp về bot lịch học SKFU</b>\n\n"
        "Hãy nhập yêu cầu bằng ngôn ngữ tự nhiên:\n\n"
        "📅 <b>Lịch học:</b>\n"
        "  <i>Lịch của ИСС-б-о-22-3</i>\n"
        "  <i>Nhóm АИС25 ngày mai có gì?</i>\n\n"
        "👤 <b>Giảng viên:</b>\n"
        "  <i>Подзолко đang ở đâu?</i>  ·  <i>Lịch của Иванов</i>\n\n"
        "🚪 <b>Phòng học:</b>\n"
        "  <i>Phòng trống ngay bây giờ</i>\n\n"
        "📋 <b>Các lệnh:</b>\n"
        "  /me          — trang cá nhân 👤\n"
        "  /miniapp     — lịch học trong ứng dụng 📅\n"
        "  /grades      — điểm của tôi từ eCampus\n"
        "  /stats       — thống kê kết quả học tập 📊\n"
        "  /subjects    — danh sách môn học\n"
        "  /classmates  — bạn cùng lớp của tôi 👥\n"
        "  /teacher     — tìm giảng viên\n"
        "  /ecampus     — trạng thái eCampus\n"
        "  /limit       — giới hạn yêu cầu\n"
        "  /language    — ngôn ngữ giao diện 🌐\n"
        "  /support     — hỗ trợ\n"
        "  /suggest     — gửi ý tưởng\n\n"
        "💡 <i>Trong nhóm, hãy nhắc tôi bằng: @botname yêu cầu</i>"
    ),
    "help.quick": (
        "📖 <b>Trợ giúp nhanh</b>\n\n"
        "/me       — màn hình này\n"
        "/grades   — điểm eCampus\n"
        "/stats    — thống kê (chọn học kỳ)\n"
        "/subjects — danh sách môn học\n"
        "/teacher  — tìm giảng viên\n"
        "/classmates — bạn cùng lớp\n"
        "/limit    — giới hạn yêu cầu\n"
        "/miniapp  — mở ứng dụng\n"
        "/help     — trợ giúp đầy đủ"
    ),

    # ── Группа: приветствие при добавлении бота ─────────────────────────────────
    "group_welcome.text": (
        "👋 Xin chào! Rất vui được tham gia <b>{chat_title}</b>!\n\n"
        "📌 <b>Tôi có thể làm gì:</b>\n"
        "  • Lịch học của nhóm, giảng viên, phòng học\n"
        "  • Phòng trống ngay bây giờ\n"
        "  • Tìm kiếm giảng viên và nhóm\n\n"
        "💬 <b>Cách liên hệ:</b>\n"
        "  Nhắc tôi: <code>@{bot_username} lịch của ИСС-б-о-22-3</code>\n"
        "  Hoặc dùng các lệnh:\n"
        "  /help — toàn bộ chức năng\n"
        "  /miniapp — lịch học trong ứng dụng 📅\n\n"
        "🔕 <i>Tôi không theo dõi cuộc trò chuyện chung — chỉ trả lời khi được nhắc hoặc qua lệnh.</i>"
    ),
    "group_welcome.default_title": "nhóm này",
    "common.open_schedule_button": "📅 Mở lịch học",

    # ── /mykey (отключена) ───────────────────────────────────────────────────
    "mykey.disabled": "Lệnh /mykey đã bị tắt.",

    # ── /roles ───────────────────────────────────────────────────────────────
    "roles.role.admin": "Quản trị viên",
    "roles.role.moderator": "Kiểm duyệt viên",
    "roles.role.vip": "VIP",
    "roles.role.beta": "Người thử nghiệm beta",
    "roles.role.user": "Người dùng",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>Vai trò:</b>",
    "roles.privileges_label": "\n🔓 <b>Quyền lợi:</b>",
    "roles.priv_admin_panel": "⚙️ <b>Bảng quản trị</b> → <a href=\"{url}\">mở</a>",
    "roles.priv_beta": "🧪 <b>Quyền truy cập beta</b> — bộ lọc lịch học mở rộng",
    "roles.priv_floorplan_edit": "🗺 <b>Chỉnh sửa</b> sơ đồ tầng",
    "roles.priv_floorplan_view": "🗺 <b>Xem</b> sơ đồ tầng",
    "roles.priv_personal_limit": "📊 <b>Giới hạn cá nhân</b>: {limit} yêu cầu / kỳ",
    "roles.profile_link": "\n💼 <b>Trang cá nhân:</b> <a href=\"{url}\">mở</a>",

    # ── /suggest ─────────────────────────────────────────────────────────────
    "suggest.prompt": (
        "💡 <b>Đề xuất và ý tưởng</b>\n\n"
        "Bạn có ý tưởng cải thiện bot hoặc lịch học?\n"
        "Hãy viết sau lệnh:\n\n"
        "<code>/suggest Ý tưởng của bạn ở đây</code>\n\n"
        "<i>Ví dụ: /suggest Thêm thông báo trước giờ học 10 phút</i>"
    ),
    "suggest.accepted": "✅ <b>Đề xuất đã được ghi nhận!</b>\n\nCảm ơn bạn, ý tưởng của bạn sẽ giúp bot tốt hơn.\nMã số: <code>{ticket_id}</code>\n",

    # ── /about ───────────────────────────────────────────────────────────────
    "about.text": (
        "🎓 <b>Bot lịch học SKFU</b>\n\n"
        "Trợ lý thông minh cho sinh viên và giảng viên "
        "của Đại học Liên bang Bắc Kavkaz.\n\n"
        "📌 <b>Chức năng:</b>\n"
        "  • Lịch học của nhóm, giảng viên, phòng học\n"
        "  • Phòng trống theo thời gian thực\n"
        "  • Tìm kiếm theo nhóm và giảng viên\n"
        "  • Mini App với lịch học đầy đủ 📅\n\n"
        "🔗 <b>Liên kết:</b>\n"
        "  • <a href=\"{miniapp_url}\">Mini App lịch học</a>\n"
        "🛠 <b>Phiên bản:</b> 2.0\n"
        "💬 Câu hỏi và đề xuất: /support · /suggest"
    ),

    # ── /miniapp ─────────────────────────────────────────────────────────────
    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — lịch học đầy đủ trong ứng dụng\n\n"
        "• Tìm kiếm linh hoạt theo nhóm, giảng viên, phòng học\n"
        "• Phòng trống theo thời gian thực\n"
        "• Sơ đồ tầng của các tòa nhà\n"
        "• Mục yêu thích và cài đặt cá nhân\n\n"
        "Nhấn nút bên dưới 👇"
    ),

    # ── /support ─────────────────────────────────────────────────────────────
    "support.prompt": "📬 <b>Hỗ trợ</b>\n\nHãy viết câu hỏi sau lệnh:\n<code>/support Câu hỏi của bạn ở đây</code>",
    "support.accepted": "✅ <b>Yêu cầu đã được ghi nhận</b>\n\nChúng tôi sẽ trả lời bạn sớm nhất có thể.\nMã yêu cầu: <code>{ticket_id}</code>",

    # ── /limit ───────────────────────────────────────────────────────────────
    "limit.header": "📊 <b>Giới hạn {scope}</b>",
    "limit.scope_private": "yêu cầu cá nhân",
    "limit.scope_chat": "yêu cầu trong đoạn chat này",
    "limit.used": "✅ Đã dùng: <b>{used}</b>",
    "limit.remaining": "💬 Còn lại: <b>{remaining}</b>",
    "limit.max": "🏁 Tối đa: <b>{cap}</b>",
    "limit.reset_in": "🔄 Đặt lại sau: <b>{reset_str}</b>",
    "limit.reset_done": "🔄 Giới hạn đã được đặt lại — bạn có thể dùng tiếp",
    "limit.exhausted_note": "<i>Đã hết giới hạn. Hãy đợi đặt lại hoặc liên hệ quản trị viên.</i>",
    "limit.normal_note": "<i>Giới hạn tính các yêu cầu AI (lịch học, tìm kiếm). Các lệnh /start, /help và các lệnh khác không được tính.</i>",

    # ── /login, /code, подтверждение входа ──────────────────────────────────
    "login.instructions": (
        "🔐 <b>Đăng nhập vào trang web</b>\n\n"
        "1. Mở <a href=\"{web_url}/profile\">{web_url}/profile</a>\n"
        "2. Nhấn <b>«Đăng nhập bằng Telegram»</b>\n"
        "3. Bạn sẽ thấy <b>mã gồm 6 chữ</b> (chữ Latinh in hoa)\n"
        "4. Gửi mã này bằng lệnh <code>/code XXXXXX</code>\n"
        "5. Xác nhận đăng nhập — trang sẽ tự cập nhật\n\n"
        "💡 Hoặc chỉ cần gõ <code>/code</code> và mã cách nhau bằng dấu cách."
    ),
    "login.code_missing": "❓ Hãy nhập mã sau lệnh:\n<code>/code XXXXXX</code>\n\nMã được hiển thị trên trang web khi nhấn «Đăng nhập bằng Telegram».",
    "login.code_invalid_format": "❌ Mã phải gồm <b>6 chữ in hoa và số</b>.\nVí dụ: <code>/code ABCDEF</code>",
    "login.account_blocked": "❌ Tài khoản của bạn đã bị khóa.",
    "login.server_error": "⚠️ Lỗi máy chủ. Vui lòng thử lại sau.",
    "login.code_error": "❌ <b>{error}</b>\n\nKiểm tra mã trên trang web và thử lại.\nMã có hiệu lực trong <b>3 phút</b>.",
    "login.code_error_default": "Mã không đúng hoặc đã hết hạn",
    "login.code_error_server": "Lỗi máy chủ",
    "login.confirm_prompt": "🔐 <b>Xác nhận đăng nhập</b>\n\nXin chào, {name}! Có ai đó đang cố đăng nhập vào trang web bằng tài khoản của bạn.\n\nBạn xác nhận đăng nhập chứ?",
    "login.confirm_button": "✅ Xác nhận đăng nhập",
    "login.cancel_button": "❌ Hủy",
    "login.cancelled": "❌ <b>Đã hủy đăng nhập.</b>\n\nNếu không phải bạn — không sao, liên kết này đã không còn hiệu lực.",
    "login.cancelled_toast": "Đã hủy đăng nhập",
    "login.confirm_error": "⚠️ <b>Lỗi xác nhận.</b>\n\nCó thể phiên làm việc đã hết hạn. Hãy thử đăng nhập lại.",
    "login.confirm_error_toast": "Lỗi, vui lòng thử lại",
    "login.confirmed": "✅ <b>Đã xác nhận đăng nhập!</b>\n\nTrang web sẽ tự động cập nhật.",
    "login.confirmed_toast": "Đăng nhập thành công ✅",
    "login.default_name": "người dùng",

    # ── Дизамбигуация (выбор группы/аудитории) ──────────────────────────────
    "disambig.stale_data": "⏱ Dữ liệu đã cũ. Hãy gửi lại yêu cầu.",
    "disambig.stale_button": "⚠️ Nút đã cũ. Hãy gửi lại yêu cầu.",
    "disambig.expired": "⏱ Đã hết thời gian chọn. Hãy gửi lại yêu cầu.",
    "disambig.loading": "⏳ Đang tải lịch học…",
    "disambig.unknown_intent": "❓ Loại yêu cầu không xác định.",
    "disambig.error": "❌ Lỗi khi tải lịch học.\n<code>{eid}</code>",
    "disambig.format_error": "❌ Lỗi xử lý lịch học.",
    "disambig.day_of": "Ngày {idx} / {total}",
    "disambig.prev_page": "◀ Trước",
    "disambig.next_page": "Tiếp ▶",
    "disambig.group_label": "nhóm #{id}",
    "disambig.room_label": "phòng #{id}",
    "disambig.schedule_title": "Lịch học · {title}",

    # ── Фидбэк 👍👎 ───────────────────────────────────────────────────────────
    "feedback.error_toast": "⚠️ Lỗi",
    "feedback.already_rated_toast": "Đã đánh giá rồi ✓",
    "feedback.save_failed_toast": "⚠️ Không thể lưu đánh giá",
    "feedback.thanks_toast": "{icon} Đã lưu đánh giá, cảm ơn!",

    # ── /classmates ──────────────────────────────────────────────────────────
    "classmates.profile_not_found": "👤 Không tìm thấy trang cá nhân của bạn.",
    "classmates.no_group": "👥 <b>Chưa cài đặt nhóm</b>\n\nHãy cài đặt trang cá nhân trên web để xem bạn cùng lớp.",
    "classmates.query_error": "❌ Lỗi khi lấy danh sách bạn cùng lớp.",
    "classmates.header": "👥 <b>Bạn cùng lớp · {group_label}</b>\n",
    "classmates.registered_count": "<i>Đã đăng ký: {count} người.</i>\n",
    "classmates.none_registered": "👥 <b>Bạn cùng lớp · {group_label}</b>\n\nChưa có ai trong nhóm của bạn đăng ký bot.",
    "classmates.group_fallback_label": "nhóm #{id}",
    "classmates.more_suffix": "\n<i>…và nhiều hơn nữa</i>",

    # ── /teacher ──────────────────────────────────────────────────────────────
    "teacher.search_prompt": "👤 <b>Tìm giảng viên</b>\n\nHãy nhập họ (hoặc một phần):\n<code>/teacher Иванов</code>",
    "teacher.search_error": "❌ Lỗi tìm kiếm.",
    "teacher.not_found": "🔍 Không tìm thấy gì với <b>{query}</b>.\n\nHãy thử họ khác.",
    "teacher.found_count": "🔍 Tìm thấy giảng viên: <b>{count}</b>\n\nHãy chọn:",
    "teacher.not_found_short": "❌ Không tìm thấy giảng viên.",
    "teacher.subjects_label": "\n📚 <b>Môn học:</b>",
    "teacher.more_subjects": "  <i>…và {count} môn khác</i>",
    "teacher.lesson_types_label": "\n🗂 <b>Loại tiết học:</b> {types}",
    "teacher.groups_label": "\n👥 <b>Nhóm ({count}):</b> {names}",
    "teacher.more_groups": "  <i>…và {count} nhóm khác</i>",
    "teacher.lessons_in_db": "\n📊 Số tiết học trong cơ sở dữ liệu: <b>{count}</b>",
    "teacher.schedule_loaded": "🕐 Lịch học: <b>đã tải</b>",
    "teacher.alltime_stats_label": "\n📈 <b>Thống kê toàn thời gian:</b>",
    "teacher.total_lessons": "  Tổng số tiết: <b>{count}</b>",
    "teacher.types_label": "  Loại: {types}",
    "teacher.buildings_label": "  Tòa nhà: {buildings}",
    "teacher.rooms_label": "  Phòng học: {rooms}",
    "teacher.schedule_button": "📅 Lịch học",

    # ── /me ──────────────────────────────────────────────────────────────────
    "me.profile_not_found": "👤 Không tìm thấy trang cá nhân.",
    "me.header": "👤 <b>Trang cá nhân</b>\n",
    "me.role_student": "Sinh viên",
    "me.role_teacher": "Giảng viên",
    "me.role_unset": "Chưa thiết lập",
    "me.group_line": "\n📌 Nhóm: <b>{group_name}</b>",
    "me.teacher_line": "\n📌 Giảng viên: <b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 Giới hạn yêu cầu: <code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 Lịch học của tôi",
    "me.miniapp_button": "📱 Lịch học (ứng dụng)",
    "me.subjects_button": "📚 Môn học",
    "me.stats_button": "📊 Thống kê",
    "me.classmates_button": "👥 Bạn cùng lớp",
    "me.my_lessons_button": "📈 Tiết học của tôi",
    "me.profile_button": "⚙️ Trang cá nhân",
    "me.map_button": "🗺 Bản đồ",
    "me.limit_button": "💬 Giới hạn yêu cầu",
    "me.help_button": "❓ Trợ giúp",
    "me.no_ecampus_data": "📭 Không có dữ liệu eCampus.",
    "me.stats_choose_period": "📊 <b>Thống kê kết quả học tập</b>\n\nChọn khoảng thời gian:",

    # ── /grades ──────────────────────────────────────────────────────────────
    "grades.not_connected": "📚 <b>Chưa kết nối eCampus</b>\n\nHãy kết nối tài khoản eCampus trong mục <b>Trang cá nhân → eCampus</b> trên web hoặc ứng dụng mini.",
    "grades.sync_running": "⏳ Đồng bộ với eCampus vẫn đang chạy — dữ liệu đang được cập nhật.\nHãy thử lại sau một phút.",
    "grades.empty": "📭 Dữ liệu eCampus hiện đang trống.\nHãy nhấn «Cập nhật» trong ứng dụng mini hoặc chờ tự động đồng bộ.",
    "grades.semester_label": "Học kỳ {n}",
    "grades.current_semester_label": "Học kỳ hiện tại",
    "grades.no_grades": "📭 <b>Chưa có điểm</b> ({sem_label})\n\nĐiểm sẽ xuất hiện sau khi giảng viên nhập.",
    "grades.header": "📊 <b>Điểm · {sem_label}</b>\n",
    "grades.total": "\n<i>Tổng số điểm: {count}</i>",
    "grades.page_suffix": "\n\n({page}/{total})",

    # ── /stats ───────────────────────────────────────────────────────────────
    "stats.not_connected_short": "📚 <b>Chưa kết nối eCampus</b>\n\nHãy kết nối tài khoản trong mục Trang cá nhân trên web.",
    "stats.no_data": "📭 Không có dữ liệu eCampus. Hãy cập nhật đồng bộ.",
    "stats.no_term_data": "📭 Không có dữ liệu cho học kỳ này.",
    "stats.all_time_suffix": " · Toàn thời gian",
    "stats.term_fallback": " · kỳ {id}",
    "stats.header": "📊 <b>Thống kê kết quả học tập{suffix}</b>\n",
    "stats.subjects_count": "📚 Môn học:   <b>{count}</b>",
    "stats.grades_count": "✏️  Điểm:      <b>{count}</b>",
    "stats.exams_count": "🎓 Kỳ thi:  <b>{count}</b>",
    "stats.credits_count": "📝 Kiểm tra:    <b>{count}</b>",
    "stats.rating": "⭐ Xếp hạng:    {icon} <b>{avg:.1f}</b> / {max:.1f} ({pct:.0f}%)",
    "stats.updated_at": "\n<i>Đã cập nhật: {dt}</i>",
    "stats.choose_period": "📊 <b>Thống kê kết quả học tập</b>\n\nChọn khoảng thời gian:",
    "stats.all_time_button": "📊 Toàn thời gian",

    # ── /subjects ────────────────────────────────────────────────────────────
    "subjects.not_connected": "📚 <b>Chưa kết nối eCampus</b>\n\nHãy kết nối tài khoản trong mục Trang cá nhân trên web.",
    "subjects.no_data": "📭 Không có dữ liệu. Hãy cập nhật đồng bộ.",
    "subjects.none_for_term": "📭 Không tìm thấy môn học ({sem_label}).",
    "subjects.header": "📚 <b>Môn học · {sem_label}</b>  ({count} môn)\n",
    "subjects.no_type_data": "không có dữ liệu",
    "subjects.rating_line": "\n    {icon} Xếp hạng: <b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>Kỳ thi</i>",
    "subjects.credit_tag": " 📝<i>Kiểm tra</i>",

    # ── /ecampus ─────────────────────────────────────────────────────────────
    "ecampus.not_connected": (
        "📚 <b>eCampus SKFU</b>\n\n"
        "Tài khoản <b>chưa được kết nối</b>.\n\n"
        "Hãy kết nối trong mục <b>Trang cá nhân → eCampus</b> trên web "
        "hoặc ứng dụng mini để nhận:\n"
        "  • Danh sách môn học và điểm\n"
        "  • Thống kê kết quả học tập\n"
        "  • Xếp hạng theo từng môn\n\n"
        "Các lệnh (sau khi kết nối):\n"
        "  /grades   — điểm của tôi\n"
        "  /stats    — thống kê kết quả học tập\n"
        "  /subjects — danh sách môn học"
    ),
    "ecampus.status_ok": "✅ Đã đồng bộ",
    "ecampus.status_running": "⏳ Đang đồng bộ...",
    "ecampus.status_error": "❌ Lỗi đồng bộ",
    "ecampus.status_pending": "🕐 Đang chờ đồng bộ",
    "ecampus.header": "📚 <b>eCampus SKFU</b>\n",
    "ecampus.status_line": "🔗 Trạng thái: {status}",
    "ecampus.subjects_count": "📦 Môn học: <b>{count}</b>",
    "ecampus.grades_count": "✏️  Điểm: <b>{count}</b>",
    "ecampus.updated_at": "🕐 Đã cập nhật: <b>{dt}</b>",
    "ecampus.current_term": "\n📅 Học kỳ hiện tại: <b>{term}</b>",
    "ecampus.term_subjects": "   Môn học: <b>{count}</b>",
    "ecampus.term_grades": "   Điểm: <b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>Các lệnh:</b>\n"
        "  /grades   — điểm học kỳ hiện tại của tôi\n"
        "  /grades 2 — điểm học kỳ 2\n"
        "  /stats    — thống kê đầy đủ\n"
        "  /subjects — danh sách môn học"
    ),

    # ── ИИ-обработчик (ошибки/заглушки) ─────────────────────────────────────
    "ai.empty_message": "Hãy nhập gì đó 🙂",
    "ai.processing": "⏳ Đang xử lý...",
    "ai.unknown_request": "❓ Yêu cầu không xác định.",
    "ai.parse_failed": "❌ Không thể hiểu yêu cầu. Hãy thử diễn đạt lại.",
    "ai.execution_error": "❌ Lỗi khi thực hiện yêu cầu.\n<code>{eid}</code>",
    "ai.processing_error": "❌ Lỗi xử lý yêu cầu.",

    # ── /language (новая команда) ───────────────────────────────────────────
    "language.prompt": "🌐 <b>Chọn ngôn ngữ giao diện</b>\n\nLựa chọn này sẽ được đồng bộ với web và ứng dụng mini.",
    "language.saved": "✅ Đã đổi ngôn ngữ thành <b>{name}</b>.",
    "language.save_failed": "⚠️ Không thể lưu ngôn ngữ. Hãy thử lại.",

    # ── Меню команд бота (BotCommand description) ───────────────────────────
    "cmd.start": "Bắt đầu",
    "cmd.me": "Trang cá nhân 👤",
    "cmd.help": "Trợ giúp",
    "cmd.miniapp": "Mở lịch học (Mini App) 📅",
    "cmd.grades": "Điểm của tôi từ eCampus",
    "cmd.stats": "Thống kê kết quả học tập 📊",
    "cmd.subjects": "Danh sách môn học",
    "cmd.classmates": "Bạn cùng lớp của tôi 👥",
    "cmd.teacher": "Tìm giảng viên 👤",
    "cmd.ecampus": "Trạng thái eCampus",
    "cmd.limit": "Giới hạn yêu cầu",
    "cmd.language": "Ngôn ngữ giao diện 🌐",
    "cmd.login": "Đăng nhập vào trang web",
    "cmd.code": "Nhập mã (/code XXXXXX)",
    "cmd.support": "Hỗ trợ",
    "cmd.suggest": "Gửi ý tưởng",
    "cmd.about": "Về bot",
}
