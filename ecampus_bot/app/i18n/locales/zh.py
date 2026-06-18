"""中文。"""

MESSAGES: dict[str, str] = {
    "start.greeting": (
        "👋 你好！我是北高加索联邦大学课表机器人。\n\n"
        "用自然语言提问：\n"
        "  • <i>本周 ISS-b-o-22-3 的课表</i>\n"
        "  • <i>5分钟后 Podzolko 老师在哪上课？</i>\n"
        "  • <i>11号楼的空闲教室</i>\n"
        "  • <i>AIS-b-o-25-1 班现在上什么课？</i>\n\n"
        "📋 <b>命令：</b>\n"
        "  /me         — 个人中心 👤\n"
        "  /miniapp    — 应用内课表 📅\n"
        "  /grades     — 我的 eCampus 成绩\n"
        "  /stats      — 统计数据 📊\n"
        "  /classmates — 同班同学 👥\n"
        "  /teacher    — 查找教师\n"
        "  /help       — 完整帮助"
    ),
    "start.login_welcome": "👋 你好，{name}！\n\n🔐 <b>新的登录方式</b>\n\n1. 打开 <a href=\"{web_url}/profile\">{web_url}/profile</a>\n2. 点击 <b>«通过 Telegram 登录»</b>\n3. 把显示的 <b>6位数代码</b> 发给我\n4. 确认 — 页面会自动刷新 ✨",

    "help.full": (
        "📖 <b>课表机器人帮助</b>\n\n"
        "直接用自然语言提问：\n\n"
        "📅 <b>课表：</b>\n"
        "  <i>ISS-b-o-22-3 的课表</i>\n"
        "  <i>AIS25 班明天有什么课？</i>\n\n"
        "👤 <b>教师：</b>\n"
        "  <i>Podzolko 现在在哪？</i>  ·  <i>Ivanov 的课表</i>\n\n"
        "🚪 <b>教室：</b>\n"
        "  <i>现在空闲的教室</i>\n\n"
        "📋 <b>命令：</b>\n"
        "  /me          — 个人中心 👤\n"
        "  /miniapp     — 应用内课表 📅\n"
        "  /grades      — 我的 eCampus 成绩\n"
        "  /stats       — 学业统计 📊\n"
        "  /subjects    — 课程列表\n"
        "  /classmates  — 我的同班同学 👥\n"
        "  /teacher     — 查找教师\n"
        "  /ecampus     — eCampus 状态\n"
        "  /limit       — 请求限额\n"
        "  /language    — 界面语言 🌐\n"
        "  /support     — 支持\n"
        "  /suggest     — 提交建议\n\n"
        "💡 <i>在群组中请提及我：@botname 你的请求</i>"
    ),
    "help.quick": (
        "📖 <b>快速帮助</b>\n\n"
        "/me       — 此屏幕\n"
        "/grades   — eCampus 成绩\n"
        "/stats    — 统计（选择学期）\n"
        "/subjects — 课程列表\n"
        "/teacher  — 查找教师\n"
        "/classmates — 同班同学\n"
        "/limit    — 请求限额\n"
        "/miniapp  — 打开应用\n"
        "/help     — 完整帮助"
    ),

    "group_welcome.text": (
        "👋 你好！很高兴加入 <b>{chat_title}</b>！\n\n"
        "📌 <b>我能做什么：</b>\n"
        "  • 班级、教师、教室的课表\n"
        "  • 当前空闲教室\n"
        "  • 搜索教师和班级\n\n"
        "💬 <b>如何使用：</b>\n"
        "  提及我：<code>@{bot_username} 课表 ISS-b-o-22-3</code>\n"
        "  或使用命令：\n"
        "  /help — 全部功能\n"
        "  /miniapp — 应用内课表 📅\n\n"
        "🔕 <i>我不会监听整个群聊 — 只回复提及和命令。</i>"
    ),
    "group_welcome.default_title": "这个群组",
    "common.open_schedule_button": "📅 打开课表",

    "mykey.disabled": "/mykey 命令已停用。",

    "roles.role.admin": "管理员",
    "roles.role.moderator": "版主",
    "roles.role.vip": "VIP",
    "roles.role.beta": "测试用户",
    "roles.role.user": "用户",
    "roles.header": "👤 <b>{name}</b>  ·  <i>{uname}</i>\n",
    "roles.roles_label": "🎭 <b>角色：</b>",
    "roles.privileges_label": "\n🔓 <b>权限：</b>",
    "roles.priv_admin_panel": "⚙️ <b>管理面板</b> → <a href=\"{url}\">打开</a>",
    "roles.priv_beta": "🧪 <b>测试权限</b> — 扩展课表筛选",
    "roles.priv_floorplan_edit": "🗺 <b>编辑</b>楼层平面图",
    "roles.priv_floorplan_view": "🗺 <b>查看</b>楼层平面图",
    "roles.priv_personal_limit": "📊 <b>个人限额</b>：每周期 {limit} 次请求",
    "roles.profile_link": "\n💼 <b>个人中心：</b> <a href=\"{url}\">打开</a>",

    "suggest.prompt": (
        "💡 <b>建议与想法</b>\n\n"
        "有改进机器人或课表的想法吗？\n"
        "在命令后写下：\n\n"
        "<code>/suggest 你的想法</code>\n\n"
        "<i>例如：/suggest 上课前10分钟添加提醒</i>"
    ),
    "suggest.accepted": "✅ <b>建议已收到！</b>\n\n谢谢，你的想法将帮助改进机器人。\n编号：<code>{ticket_id}</code>\n",

    "about.text": (
        "🎓 <b>北高加索联邦大学课表机器人</b>\n\n"
        "为北高加索联邦大学师生打造的智能助手。\n\n"
        "📌 <b>功能：</b>\n"
        "  • 班级、教师、教室课表\n"
        "  • 实时空闲教室\n"
        "  • 搜索班级和教师\n"
        "  • 完整课表小程序 📅\n\n"
        "🔗 <b>链接：</b>\n"
        "  • <a href=\"{miniapp_url}\">课表小程序</a>\n"
        "🛠 <b>版本：</b> 2.0\n"
        "💬 问题与建议：/support · /suggest"
    ),

    "miniapp.text": (
        "🎓 <b>NCFU Schedule</b> — 应用内完整课表\n\n"
        "• 灵活搜索班级、教师、教室\n"
        "• 实时空闲教室\n"
        "• 教学楼平面图\n"
        "• 收藏与个性化设置\n\n"
        "点击下方按钮 👇"
    ),

    "support.prompt": "📬 <b>支持</b>\n\n请在命令后写下你的问题：\n<code>/support 你的问题</code>",
    "support.accepted": "✅ <b>请求已收到</b>\n\n我们会尽快回复你。\n工单编号：<code>{ticket_id}</code>",

    "limit.header": "📊 <b>{scope}限额</b>",
    "limit.scope_private": "个人请求",
    "limit.scope_chat": "本对话请求",
    "limit.used": "✅ 已使用：<b>{used}</b>",
    "limit.remaining": "💬 剩余：<b>{remaining}</b>",
    "limit.max": "🏁 最大值：<b>{cap}</b>",
    "limit.reset_in": "🔄 重置倒计时：<b>{reset_str}</b>",
    "limit.reset_done": "🔄 限额已重置 — 可以继续使用",
    "limit.exhausted_note": "<i>限额已用完。请等待重置或联系管理员。</i>",
    "limit.normal_note": "<i>此限额仅计算AI请求（课表、搜索）。/start、/help 等命令不计入。</i>",

    "login.instructions": (
        "🔐 <b>网站登录</b>\n\n"
        "1. 打开 <a href=\"{web_url}/profile\">{web_url}/profile</a>\n"
        "2. 点击 <b>«通过 Telegram 登录»</b>\n"
        "3. 你会看到一个<b>6位字母代码</b>（大写拉丁字母）\n"
        "4. 用 <code>/code XXXXXX</code> 发送代码\n"
        "5. 确认 — 页面会自动刷新\n\n"
        "💡 或直接输入 <code>/code</code> 和代码，用空格分隔。"
    ),
    "login.code_missing": "❓ 请在命令后提供代码：\n<code>/code XXXXXX</code>\n\n点击«通过 Telegram 登录»后网站会显示代码。",
    "login.code_invalid_format": "❌ 代码必须是<b>6位大写字母和数字</b>。\n例如：<code>/code ABCDEF</code>",
    "login.account_blocked": "❌ 你的账户已被封禁。",
    "login.server_error": "⚠️ 服务器错误，请稍后再试。",
    "login.code_error": "❌ <b>{error}</b>\n\n请在网站上检查代码后重试。\n代码有效期为<b>3分钟</b>。",
    "login.code_error_default": "代码无效或已过期",
    "login.code_error_server": "服务器错误",
    "login.confirm_prompt": "🔐 <b>确认登录</b>\n\n你好，{name}！有人正在用你的账户登录网站。\n\n确认登录吗？",
    "login.confirm_button": "✅ 确认登录",
    "login.cancel_button": "❌ 取消",
    "login.cancelled": "❌ <b>登录已取消。</b>\n\n如果不是你操作的，没关系 — 该链接已失效。",
    "login.cancelled_toast": "登录已取消",
    "login.confirm_error": "⚠️ <b>确认出错。</b>\n\n会话可能已过期，请重新登录。",
    "login.confirm_error_toast": "出错了，请重试",
    "login.confirmed": "✅ <b>登录已确认！</b>\n\n网站页面会自动刷新。",
    "login.confirmed_toast": "登录成功 ✅",
    "login.default_name": "用户",

    "disambig.stale_data": "⏱ 数据已过期，请重新请求。",
    "disambig.stale_button": "⚠️ 按钮已过期，请重新请求。",
    "disambig.expired": "⏱ 选择时间已过期，请重新请求。",
    "disambig.loading": "⏳ 正在加载课表…",
    "disambig.unknown_intent": "❓ 未知的请求类型。",
    "disambig.error": "❌ 加载课表出错。\n<code>{eid}</code>",
    "disambig.format_error": "❌ 处理课表出错。",
    "disambig.day_of": "第 {idx} 天，共 {total} 天",
    "disambig.prev_page": "◀ 上一页",
    "disambig.next_page": "下一页 ▶",
    "disambig.group_label": "班级 #{id}",
    "disambig.room_label": "教室 #{id}",
    "disambig.schedule_title": "课表 · {title}",

    "feedback.error_toast": "⚠️ 出错了",
    "feedback.already_rated_toast": "已评价 ✓",
    "feedback.save_failed_toast": "⚠️ 评价保存失败",
    "feedback.thanks_toast": "{icon} 评价已保存，谢谢！",

    "classmates.profile_not_found": "👤 未找到你的资料。",
    "classmates.no_group": "👥 <b>未设置班级</b>\n\n请在网站上设置你的资料以查看同班同学。",
    "classmates.query_error": "❌ 获取同班同学列表出错。",
    "classmates.header": "👥 <b>同班同学 · {group_label}</b>\n",
    "classmates.registered_count": "<i>已注册：{count} 人</i>\n",
    "classmates.none_registered": "👥 <b>同班同学 · {group_label}</b>\n\n目前还没有同班同学注册机器人。",
    "classmates.group_fallback_label": "班级 #{id}",
    "classmates.more_suffix": "\n<i>…还有更多</i>",

    "teacher.search_prompt": "👤 <b>查找教师</b>\n\n输入姓氏（或部分）：\n<code>/teacher Ivanov</code>",
    "teacher.search_error": "❌ 搜索出错。",
    "teacher.not_found": "🔍 未找到 <b>{query}</b> 的结果。\n\n请尝试其他姓氏。",
    "teacher.found_count": "🔍 找到教师：<b>{count}</b> 位\n\n请选择：",
    "teacher.not_found_short": "❌ 未找到该教师。",
    "teacher.subjects_label": "\n📚 <b>课程：</b>",
    "teacher.more_subjects": "  <i>…还有 {count} 个</i>",
    "teacher.lesson_types_label": "\n🗂 <b>课程类型：</b> {types}",
    "teacher.groups_label": "\n👥 <b>班级（{count}）：</b> {names}",
    "teacher.more_groups": "  <i>…还有 {count} 个</i>",
    "teacher.lessons_in_db": "\n📊 数据库中的课程数：<b>{count}</b>",
    "teacher.schedule_loaded": "🕐 课表：<b>已加载</b>",
    "teacher.alltime_stats_label": "\n📈 <b>历史统计：</b>",
    "teacher.total_lessons": "  总课次：<b>{count}</b>",
    "teacher.types_label": "  类型：{types}",
    "teacher.buildings_label": "  楼栋：{buildings}",
    "teacher.rooms_label": "  教室：{rooms}",
    "teacher.schedule_button": "📅 课表",

    "me.profile_not_found": "👤 未找到资料。",
    "me.header": "👤 <b>个人中心</b>\n",
    "me.role_student": "学生",
    "me.role_teacher": "教师",
    "me.role_unset": "未设置",
    "me.group_line": "\n📌 班级：<b>{group_name}</b>",
    "me.teacher_line": "\n📌 教师：<b>{teacher_name}</b>",
    "me.quota_line": "\n\n💬 请求限额：<code>{bar}</code> {used}/{cap}",
    "me.my_schedule_button": "📅 我的课表",
    "me.miniapp_button": "📱 课表（应用）",
    "me.subjects_button": "📚 课程",
    "me.stats_button": "📊 统计",
    "me.classmates_button": "👥 同班同学",
    "me.my_lessons_button": "📈 我的课程",
    "me.profile_button": "⚙️ 资料",
    "me.map_button": "🗺 地图",
    "me.limit_button": "💬 请求限额",
    "me.help_button": "❓ 帮助",
    "me.no_ecampus_data": "📭 没有 eCampus 数据。",
    "me.stats_choose_period": "📊 <b>学业统计</b>\n\n请选择时段：",

    "grades.not_connected": "📚 <b>未连接 eCampus</b>\n\n请在网站或小程序的<b>个人资料 → eCampus</b>中连接你的 eCampus 账户。",
    "grades.sync_running": "⏳ eCampus 同步仍在进行 — 数据正在更新。\n请稍后再试。",
    "grades.empty": "📭 eCampus 数据暂时为空。\n请在小程序中点击«刷新»或等待自动同步。",
    "grades.semester_label": "第 {n} 学期",
    "grades.current_semester_label": "当前学期",
    "grades.no_grades": "📭 <b>暂无成绩</b>（{sem_label}）\n\n教师录入成绩后会显示在此处。",
    "grades.header": "📊 <b>成绩 · {sem_label}</b>\n",
    "grades.total": "\n<i>成绩总数：{count}</i>",
    "grades.page_suffix": "\n\n（{page}/{total}）",

    "stats.not_connected_short": "📚 <b>未连接 eCampus</b>\n\n请在网站的个人资料中连接账户。",
    "stats.no_data": "📭 没有 eCampus 数据，请刷新同步。",
    "stats.no_term_data": "📭 该学期没有数据。",
    "stats.all_time_suffix": " · 全部时间",
    "stats.term_fallback": " · 学期{id}",
    "stats.header": "📊 <b>学业统计{suffix}</b>\n",
    "stats.subjects_count": "📚 课程数：   <b>{count}</b>",
    "stats.grades_count": "✏️  成绩数：   <b>{count}</b>",
    "stats.exams_count": "🎓 考试数： <b>{count}</b>",
    "stats.credits_count": "📝 考查数： <b>{count}</b>",
    "stats.rating": "⭐ 评分：    {icon} <b>{avg:.1f}</b> / {max:.1f}（{pct:.0f}%）",
    "stats.updated_at": "\n<i>更新时间：{dt}</i>",
    "stats.choose_period": "📊 <b>学业统计</b>\n\n请选择时段：",
    "stats.all_time_button": "📊 全部时间",

    "subjects.not_connected": "📚 <b>未连接 eCampus</b>\n\n请在网站的个人资料中连接账户。",
    "subjects.no_data": "📭 没有数据，请刷新同步。",
    "subjects.none_for_term": "📭 未找到课程（{sem_label}）。",
    "subjects.header": "📚 <b>课程 · {sem_label}</b>（共 {count} 个）\n",
    "subjects.no_type_data": "暂无数据",
    "subjects.rating_line": "\n    {icon} 评分：<b>{cur:.1f}</b>/{max}",
    "subjects.exam_tag": " 🎓<i>考试</i>",
    "subjects.credit_tag": " 📝<i>考查</i>",

    "ecampus.not_connected": (
        "📚 <b>NCFU eCampus</b>\n\n"
        "账户<b>未连接</b>。\n\n"
        "在网站或小程序的<b>个人资料 → eCampus</b>中连接，即可获得：\n"
        "  • 课程与成绩列表\n"
        "  • 学业统计\n"
        "  • 各课程评分\n\n"
        "连接后可用命令：\n"
        "  /grades   — 我的成绩\n"
        "  /stats    — 学业统计\n"
        "  /subjects — 课程列表"
    ),
    "ecampus.status_ok": "✅ 已同步",
    "ecampus.status_running": "⏳ 同步中...",
    "ecampus.status_error": "❌ 同步出错",
    "ecampus.status_pending": "🕐 等待同步",
    "ecampus.header": "📚 <b>NCFU eCampus</b>\n",
    "ecampus.status_line": "🔗 状态：{status}",
    "ecampus.subjects_count": "📦 课程数：<b>{count}</b>",
    "ecampus.grades_count": "✏️  成绩数：<b>{count}</b>",
    "ecampus.updated_at": "🕐 更新时间：<b>{dt}</b>",
    "ecampus.current_term": "\n📅 当前学期：<b>{term}</b>",
    "ecampus.term_subjects": "   课程数：<b>{count}</b>",
    "ecampus.term_grades": "   成绩数：<b>{count}</b>",
    "ecampus.commands_footer": (
        "\n📋 <b>命令：</b>\n"
        "  /grades   — 当前学期成绩\n"
        "  /grades 2 — 第2学期成绩\n"
        "  /stats    — 完整统计\n"
        "  /subjects — 课程列表"
    ),

    "ai.empty_message": "请输入一些内容 🙂",
    "ai.processing": "⏳ 处理中...",
    "ai.unknown_request": "❓ 未知请求。",
    "ai.parse_failed": "❌ 无法理解该请求，请换个说法。",
    "ai.execution_error": "❌ 执行请求时出错。\n<code>{eid}</code>",
    "ai.processing_error": "❌ 处理请求出错。",

    "language.prompt": "🌐 <b>选择界面语言</b>\n\n该选择会与网站和小程序同步。",
    "language.saved": "✅ 语言已更改为<b>{name}</b>。",
    "language.save_failed": "⚠️ 保存语言失败，请重试。",

    "cmd.start": "开始使用",
    "cmd.me": "个人中心 👤",
    "cmd.help": "帮助",
    "cmd.miniapp": "打开课表（小程序）📅",
    "cmd.grades": "我的 eCampus 成绩",
    "cmd.stats": "学业统计 📊",
    "cmd.subjects": "课程列表",
    "cmd.classmates": "我的同班同学 👥",
    "cmd.teacher": "查找教师 👤",
    "cmd.ecampus": "eCampus 状态",
    "cmd.limit": "请求限额",
    "cmd.language": "界面语言 🌐",
    "cmd.login": "登录网站",
    "cmd.code": "输入代码（/code XXXXXX）",
    "cmd.support": "支持",
    "cmd.suggest": "提交建议",
    "cmd.about": "关于机器人",
}
